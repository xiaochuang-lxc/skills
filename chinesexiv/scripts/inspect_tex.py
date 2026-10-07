#!/usr/bin/env python3
r"""
ChineseXiv 翻译后自检：扫描 .tex 中疑似未翻译的英文片段。

思路（启发式，不是严格判断）：
  - 逐行剥离 LaTeX 命令、注释、数学环境、cite/ref/label/include/url 等"不应翻译"的成分；
  - 剥离后若仍出现长串字母（≥6 连续 [A-Za-z]）且整行含中文字符为零，
    就判定为可疑——可能是漏译的英文句子；
  - 表格里的格式说明行（如 `l|cccc`）、纯数字行会被排除。

扫描范围（scope）：
  - body：仅 `\begin{document}` 到 `\end{document}` 之间；遇到 `\appendix` 提前停下。
  - full：扫整文件，包括前言和附录。

用法：
  python inspect_tex.py scan <work_dir> <main_tex> <scope>

输出：
  SUSPECT_COUNT=<n>
  SUSPECT=<file>:<lineno>:<片段>
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from typing import Iterable


# ---- 关键正则 ----
INPUT_RE = re.compile(r"\\(input|include|subfile)\{([^}]+)\}")
BEGIN_DOC_RE = re.compile(r"\\begin\{document\}")
END_DOC_RE = re.compile(r"\\end\{document\}")
APPENDIX_RE = re.compile(r"\\appendix\b")
BEGIN_BIB_RE = re.compile(r"\\begin\{thebibliography\}|\\bibliographystyle\{|\\bibliography\{")
BEGIN_TABULAR_RE = re.compile(r"\\begin\{tabular\}")
END_TABULAR_RE = re.compile(r"\\end\{tabular\}")

# 去掉行内未转义的 % 注释
COMMENT_RE = re.compile(r"(?<!\\)%.*$")

# 这些 LaTeX 构造不参与"是否英文"判定，按顺序剥离
STRIP_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\\(input|include|subfile)\{[^}]*\}"),
    re.compile(r"\\includegraphics(\[[^\]]*\])?\{[^}]*\}"),
    re.compile(r"\\texttt\{[^}]*\}"),
    re.compile(r"\\textit\{[^}]*\}"),
    re.compile(r"\\cite\w*\{[^}]*\}"),
    re.compile(r"\\ref\{[^}]*\}"),
    re.compile(r"\\label\{[^}]*\}"),
    re.compile(r"\\url\{[^}]*\}"),
    re.compile(r"\\href\{[^}]*\}\{[^}]*\}"),
    re.compile(r"\\(begin|end)\{[^}]*\}"),
    re.compile(r"\$[^$]*\$"),
    re.compile(r"\\\([^)]*\\\)"),
    re.compile(r"\\\[[^\]]*\\\]"),
    re.compile(r"\\[A-Za-z@]+\*?"),  # 任何命令名
    re.compile(r"[{}\\[\\]]"),
]

ALPHA_RUN_RE = re.compile(r"[A-Za-z]{6,}")
CJK_RE = re.compile(r"[一-鿿]")
TABULAR_SPEC_RE = re.compile(r"^[lcrpmb\|@*!0-9.\s]+$")


@dataclass(frozen=True)
class Suspect:
    """一条可疑漏译记录：文件、行号、剥离后的片段。"""
    path: str
    lineno: int
    snippet: str


def _norm_tex_path(work_dir: str, raw: str) -> str | None:
    r"""规范化 `\input/\include` 的参数为可访问的绝对路径。

    TeX 允许省略 .tex 扩展名，所以两种都要试。
    """
    raw = raw.strip()
    if not raw:
        return None
    candidates = [raw]
    if not raw.lower().endswith(".tex"):
        candidates.append(raw + ".tex")
    for c in candidates:
        p = os.path.normpath(os.path.join(work_dir, c))
        if os.path.exists(p) and os.path.isfile(p):
            return p
    return None


def _walk_includes(work_dir: str, main_tex: str) -> list[str]:
    r"""从主文件开始 BFS 展开 `\input/\include`，得到所有要扫描的 .tex 文件。

    限制在 work_dir 之内，避免 \input 跳出去引发安全/路径问题。
    """
    work_dir = os.path.abspath(work_dir)
    main_abs = main_tex if os.path.isabs(main_tex) else os.path.join(work_dir, main_tex)
    main_abs = os.path.abspath(main_abs)
    if not main_abs.startswith(work_dir + os.sep) and main_abs != work_dir:
        raise SystemExit(f"主文件必须在 work_dir 之内：{main_abs}")

    queue = [main_abs]
    seen: set[str] = set()
    ordered: list[str] = []

    while queue:
        cur = os.path.abspath(queue.pop(0))
        if cur in seen or not os.path.exists(cur):
            continue
        seen.add(cur)
        ordered.append(cur)
        try:
            with open(cur, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        # 逐行剥掉 % 注释后再找 \input：被注释掉的 \input 不参与编译，
        # 若照样跟进，会把无关文件拉进扫描队列并虚报大量 SUSPECT。
        for line in text.splitlines():
            for m in INPUT_RE.finditer(COMMENT_RE.sub("", line)):
                inc = _norm_tex_path(os.path.dirname(cur), m.group(2))
                if inc and inc.startswith(work_dir + os.sep):
                    queue.append(inc)
    return ordered


def _iter_relevant_lines(lines: list[str], scope: str) -> Iterable[tuple[int, str]]:
    r"""按 scope 过滤出要扫描的行。

    body 模式做了几个剪枝：
      - `\begin{document}` 之前都跳过（前言区不该有英文叙述）；
      - 遇到 `\appendix` / `\end{document}` / `\bibliography*` 立即停；
      - tabular 内部跳过（格式控制 + 数据行，常被误判）。
    """
    if scope == "full":
        for i, line in enumerate(lines, start=1):
            yield i, line
        return

    in_doc = False
    in_tabular = False
    for i, line in enumerate(lines, start=1):
        if not in_doc and BEGIN_DOC_RE.search(line):
            in_doc = True
        if not in_doc:
            continue
        if APPENDIX_RE.search(line):
            break
        if BEGIN_BIB_RE.search(line):
            break
        if END_DOC_RE.search(line):
            break
        if BEGIN_TABULAR_RE.search(line):
            in_tabular = True
        if in_tabular:
            if END_TABULAR_RE.search(line):
                in_tabular = False
            continue
        yield i, line


def _strip_for_detection(s: str) -> str:
    """剥离所有不应被翻译的 LaTeX 成分，剩下的字符串才参与"是否英文"判定。"""
    s = COMMENT_RE.sub("", s)
    for pat in STRIP_PATTERNS:
        s = pat.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_suspect_line(s: str) -> bool:
    """判断剥离后的字符串是否「疑似英文」。

    规则：
      - 含中文则直接放行（即便残留英文也大概率是术语 / 缩写）；
      - 字母总数太少（<12）说明信息量低，跳过；
      - 有 ≥6 连续字母（长单词，几乎不可能是术语缩写）→ 怀疑；
      - 字母密度 > 35% → 怀疑。
    """
    if not s:
        return False
    if TABULAR_SPEC_RE.match(s):
        return False
    if CJK_RE.search(s):
        return False
    alpha = sum(1 for ch in s if ch.isalpha())
    if alpha < 12:
        return False
    if ALPHA_RUN_RE.search(s):
        return True
    return alpha / max(len(s), 1) > 0.35


def scan(work_dir: str, main_tex: str, scope: str) -> list[Suspect]:
    """主扫描入口：返回所有可疑行。"""
    suspects: list[Suspect] = []
    for path in _walk_includes(work_dir, main_tex):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except OSError:
            continue

        for lineno, raw in _iter_relevant_lines(lines, scope):
            stripped = _strip_for_detection(raw)
            if _is_suspect_line(stripped):
                snippet = stripped[:160]
                suspects.append(Suspect(path=path, lineno=lineno, snippet=snippet))

    return suspects


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="ChineseXiv 漏译扫描器")
    sub = parser.add_subparsers(dest="cmd", required=True)

    scan_p = sub.add_parser("scan", help="扫描可疑漏译")
    scan_p.add_argument("work_dir", help="源码目录")
    scan_p.add_argument("main_tex", help="主 .tex 文件（相对 work_dir 或绝对路径）")
    scan_p.add_argument("scope", choices=["body", "full"], help="扫描范围：body / full")

    args = parser.parse_args(argv)
    if args.cmd == "scan":
        sus = scan(args.work_dir, args.main_tex, args.scope)
        # 输出格式是契约：先一行总数，再每条一行
        print(f"SUSPECT_COUNT={len(sus)}")
        for s in sus[:5000]:
            rel = os.path.relpath(s.path, os.path.abspath(args.work_dir))
            print(f"SUSPECT={rel}:{s.lineno}:{s.snippet}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
