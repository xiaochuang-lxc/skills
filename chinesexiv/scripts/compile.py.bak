#!/usr/bin/env python3
"""
ChineseXiv 编译入口：支持本地 xelatex 与在线 latex-on-http 双引擎。
Usage:
  python compile.py <work_dir> <main_tex> <output_pdf_path> [--engine auto|local|online]

参数说明：
  main_tex:        相对 work_dir 的路径（如 ms.tex），或主文件绝对路径。
  output_pdf_path: 输出 PDF 完整路径；若传入一个已存在的目录，则在该目录下写 <main_basename>.pdf。
  --engine auto:   默认。本地装了 xelatex 走本地编译，否则回落在线。
  --engine local:  强制本地 xelatex；未装则报错退出。
  --engine online: 强制走 latex.ytotech.com。
"""
import argparse
import base64
import os
import re
import shutil
import subprocess
import sys

import requests


_BIBLATEX_RE = re.compile(r"\\(?:usepackage(?:\[[^\]]*\])?\{biblatex\}|addbibresource\{)")
_BIBTEX_CMD_RE = re.compile(r"\\bibliography\{")
_THEBIB_RE = re.compile(r"\\begin\{thebibliography\}")
_BBL_INPUT_RE = re.compile(r"\\(?:input|include)\s*\{[^}]+\.bbl\}")
_CMD_ALREADY_DEFINED_RE = re.compile(r"LaTeX Error: Command \\([A-Za-z@]+) already defined")
_CMD_ALREADY_DEFINED_WITH_PATH_RE = re.compile(
    r"^\./(?P<path>[^:\n]+):(?P<lineno>\d+):\s+LaTeX Error: Command \\(?P<cmd>[A-Za-z@]+) already defined",
    re.MULTILINE,
)
_BEGIN_DOCUMENT_RE = re.compile(r"\\begin\{document\}")
_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_UNRESOLVED_CITE_MARKERS = ("[?", "?]")
_UNRESOLVED_REF_MARKERS = ("??",)
_SOURCE_TEXT_EXTS = {
    ".tex",
    ".sty",
    ".cls",
    ".bst",
    ".bib",
    ".bbx",
    ".cbx",
    ".cfg",
}
_BUILD_ARTIFACT_EXTS = (
    ".aux",
    ".log",
    ".out",
    ".toc",
    ".lof",
    ".lot",
    ".nav",
    ".snm",
    ".vrb",
    ".fls",
    ".fdb_latexmk",
    ".synctex.gz",
    ".run.xml",
    ".bcf",
    ".blg",
    ".idx",
    ".ilg",
    ".ind",
    ".xdv",
    ".dvi",
    ".ps",
)
_SKIP_FILENAMES = {"download.env"}
_AUTO_CJK_PREAMBLE = "\n".join(
    (
        r"\usepackage{fontspec}",
        r"\usepackage{xeCJK}",
        r"\setCJKmainfont{Noto Serif CJK SC}",
        r"% --- 中文排版舒适度（行距 + 中英文间距）---",
        r"\xeCJKsetup{CJKecglue={\hskip 0.15em plus 0.05em minus 0.04em}}",
        r"\linespread{1.25}\selectfont",
        "",
    )
)


def encode(path):
    """读取文件并以 base64 编码返回——在线引擎上传源码时要打成 base64。"""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _read_text(path):
    """以 UTF-8 读文本文件，遇到编码错误就忽略而不是炸——arXiv 源码风格混乱常见。"""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _norm_relpath(path, root):
    """把绝对路径转成相对于 root 的规范化路径；Windows 上把反斜杠换成正斜杠。"""
    rel = os.path.relpath(path, root)
    rel = os.path.normpath(rel)
    if os.name == "nt":
        rel = rel.replace("\\", "/")
    return rel


# 遍历项目时跳过的目录（构建产物、版本控制、IDE）
_SKIP_DIRNAMES = {"build", "_build", "__pycache__", ".git", ".idea", ".vscode"}


def _iter_project_files(work_dir):
    """遍历 work_dir 下所有文件，自动跳过 _SKIP_DIRNAMES 里的目录。"""
    for root, dirs, files in os.walk(work_dir):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRNAMES]
        for fname in files:
            abs_path = os.path.join(root, fname)
            yield abs_path, _norm_relpath(abs_path, work_dir)


def _collect_source_texts(work_dir):
    """把所有可识别的源码文件（.tex/.sty/.cls/.bib/...）一次性读进内存，方便正则联查。"""
    texts = {}
    for abs_path, rel in _iter_project_files(work_dir):
        if os.path.splitext(rel)[1].lower() not in _SOURCE_TEXT_EXTS:
            continue
        try:
            texts[rel] = _read_text(abs_path)
        except OSError:
            continue
    return texts


def _main_tex_relative(work_dir, main_tex):
    """把 main_tex 统一成相对 work_dir 的路径，并校验它必须落在 work_dir 内。"""
    work_dir = os.path.abspath(work_dir)
    if os.path.isabs(main_tex):
        main_abs = os.path.abspath(main_tex)
    else:
        main_abs = os.path.abspath(os.path.join(work_dir, main_tex))
    try:
        rel = os.path.relpath(main_abs, work_dir)
    except ValueError:
        rel = main_tex
    if rel.startswith("..") or os.path.isabs(rel):
        print(
            "错误：主文件必须在 work_dir 之内。\n"
            f"  work_dir={work_dir}\n"
            f"  main_tex={main_tex} -> {main_abs}",
            file=sys.stderr,
        )
        sys.exit(1)
    rel = os.path.normpath(rel)
    if os.name == "nt":
        rel = rel.replace("\\", "/")
    return work_dir, rel


def _resolve_output_pdf(output_path, main_tex_rel):
    """解析输出 PDF 路径：若 output_path 是已存在目录，则写入 `<main_stem>.pdf`。"""
    output_path = os.path.expanduser(output_path)
    if output_path.endswith(os.sep) or (os.path.exists(output_path) and os.path.isdir(output_path)):
        base = os.path.splitext(os.path.basename(main_tex_rel))[0] + ".pdf"
        return os.path.join(output_path.rstrip(os.sep), base)
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    return output_path


def _find_prebuilt_bbl(work_dir, main_rel):
    """找项目里已编译好的 .bbl 文件（论文经常预先打包了 .bbl 但不带 .bib）。"""
    main_stem = os.path.splitext(os.path.basename(main_rel))[0].lower()
    bbl_files = []
    for _, rel in _iter_project_files(work_dir):
        if rel.lower().endswith(".bbl"):
            bbl_files.append(rel)
    if not bbl_files:
        return None
    # 优先匹配与主文件同名的 .bbl
    for rel in bbl_files:
        if os.path.splitext(os.path.basename(rel))[0].lower() == main_stem:
            return rel
    if len(bbl_files) == 1:
        return bbl_files[0]
    return None


def _detect_bibliography_setup(work_dir, main_rel):
    """检测论文用了哪套参考文献方案。返回 (bib_command, prebuilt_bbl)。

    判定优先级：
      1. 用了 biblatex / addbibresource：走 biber；
      2. 直接写了 thebibliography 环境 / \\input 了 .bbl：不需要再跑 bib 工具；
      3. 用了 \\bibliography{...} 命令：
         - 项目内带预编译 .bbl 且无 .bib：复用 .bbl；
         - 否则走 bibtex；
      4. 项目里只是有 .bib 没显式 \\bibliography：尝试 bibtex。
    """
    tex_blob = "\n".join(
        text for rel, text in _collect_source_texts(work_dir).items() if rel.lower().endswith(".tex")
    )
    has_bib_files = any(rel.lower().endswith(".bib") for _, rel in _iter_project_files(work_dir))
    prebuilt_bbl = _find_prebuilt_bbl(work_dir, main_rel)

    if _BIBLATEX_RE.search(tex_blob):
        return "biber", None

    # 已有显式的 thebibliography 环境或 \\input{xxx.bbl}：不需要任何 bib 工具。
    # 这种情况下硬跑 bibtex 容易因找不到 .bib 而失败，反倒留下未解析的引用（"?"）。
    if _THEBIB_RE.search(tex_blob) or _BBL_INPUT_RE.search(tex_blob):
        return None, None

    # 用了 \\bibliography{...}：若已带预编译 .bbl 且没有 .bib，直接复用 .bbl，免去再跑一遍 bibtex。
    # 在线服务会把主文件改名为 __main_document__.tex，所以上传时要把 .bbl 也按这个名字提交。
    if _BIBTEX_CMD_RE.search(tex_blob):
        if prebuilt_bbl and not has_bib_files:
            return None, prebuilt_bbl
        return "bibtex", None

    if has_bib_files:
        return "bibtex", None

    return None, None


def _detect_compiler(work_dir, main_rel):
    """根据主文件里的 CJK 栈选择编译器。"""
    main_text = _read_text(os.path.join(work_dir, main_rel))

    # 让编译器与 CJK 栈匹配——可以避免一些细微的不兼容和宏冲突。
    if "\\usepackage{xeCJK}" in main_text or "\\setCJKmainfont" in main_text:
        return "xelatex"
    if "\\usepackage{luatexja}" in main_text or "\\usepackage{luatexja-fontspec}" in main_text or "\\setmainjfont" in main_text:
        return "lualatex"

    # 本 skill 默认走 xelatex（与 fontspec/xeCJK + 大多数 arXiv 源码兼容性最好）。
    return "xelatex"


def _map_server_path_to_local(server_path, main_rel):
    """在线服务会把主文件改名为 __main_document__.tex，解析日志时要还原回本地路径。"""
    base = os.path.basename(server_path)
    if base == "__main_document__.tex":
        return main_rel
    return server_path.lstrip("./")


def _patch_file_replace(path, pattern, repl, count=1):
    """通用的「按正则替换文件内容」工具函数。"""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError:
        return False
    new_text, n = re.subn(pattern, repl, text, count=count, flags=re.MULTILINE)
    if n <= 0:
        return False
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
    except OSError:
        return False
    return True


def _project_contains_cjk(work_dir):
    """检测项目里的 .tex 文件是否真的包含 CJK 字符——决定是否要注入 CJK 支持。"""
    for rel, text in _collect_source_texts(work_dir).items():
        if rel.lower().endswith(".tex") and _CJK_RE.search(text):
            return True
    return False


_COMMENT_RE = re.compile(r"(?<!\\)%.*$", re.M)


def _strip_latex_comments(text):
    """剥掉 LaTeX 注释（未转义的 % 到行尾），供「是否已自带某宏包」类检测使用。

    必须剥离后再匹配：论文源码里常残留被注释掉的 \\usepackage{xeCJK} /
    \\setCJKmainfont{...}（模板遗留或作者试验残留）。若不剥离，就会误判为
    「作者已配好 CJK 栈」而跳过注入，最终编译 exit 0 但中文全部渲染为空白
    字形，只有日志里留下大量 Missing character 警告——属于静默失败。
    """
    return _COMMENT_RE.sub("", text)


def _ensure_cjk_support(work_dir, main_rel):
    """若项目含中文且主文件还没装好 CJK 栈，就在 \\begin{document} 前注入 xeCJK 配置。"""
    path = os.path.join(work_dir, main_rel)
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError:
        return False

    if not _project_contains_cjk(work_dir):
        return False

    # 检测基于「剥掉注释后」的文本：被注释掉的 xeCJK 不应算作已配置
    probe = _strip_latex_comments(text)

    # 论文若已经自带 CJK/Unicode 栈，就尊重原作者的配置，不强行注入。
    if any(
        tok in probe
        for tok in (
            "\\usepackage{luatexja}",
            "\\usepackage{luatexja-fontspec}",
            "\\usepackage{xeCJK}",
            "\\usepackage{ctex}",
            "\\setmainjfont{",
            "\\setCJKmainfont{",
        )
    ):
        return False

    if not _BEGIN_DOCUMENT_RE.search(text):
        return False

    preamble = _AUTO_CJK_PREAMBLE
    # 论文自己已经 \\usepackage{fontspec} 了就不重复加，否则 xelatex 会报已加载警告
    if "\\usepackage{fontspec}" in probe:
        preamble = preamble.replace("\\usepackage{fontspec}\n", "", 1)

    new_text, n = _BEGIN_DOCUMENT_RE.subn(lambda _: preamble + r"\begin{document}", text, count=1)
    if n <= 0:
        return False

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
    except OSError:
        return False

    return True


def _preflight_comment_inputenc_fontenc(work_dir, main_rel):
    """注释掉与 Unicode 栈冲突的 inputenc/fontenc。

    XeLaTeX / LuaLaTeX 这套 Unicode 编译栈（fontspec + xeCJK 或 luatexja）天生支持 UTF-8，
    遇到 \\usepackage[utf8]{inputenc} 或 \\usepackage[T1]{fontenc} 反而会报错。
    """
    path = os.path.join(work_dir, main_rel)
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError:
        return False

    uses_unicode_stack = any(
        tok in text
        for tok in (
            "\\usepackage{fontspec}",
            "\\usepackage{xeCJK}",
            "\\usepackage{luatexja}",
            "\\usepackage{ctex}",
        )
    )
    if not uses_unicode_stack:
        return False

    changed = False

    # 已经被注释掉的行不再重复注释
    def _comment_line(m):
        indent = m.group("indent") or ""
        line = m.group(0)
        # 保留缩进，仅在缩进后插 "% "
        return indent + "% " + line[len(indent) :]

    for pat in (
        r"^(?P<indent>\s*)\\usepackage\[[^\]]*\]\{inputenc\}.*$",
        r"^(?P<indent>\s*)\\usepackage\[[^\]]*\]\{fontenc\}.*$",
    ):
        if re.search(pat, text, flags=re.MULTILINE):
            text = re.sub(pat, _comment_line, text, count=1, flags=re.MULTILINE)
            changed = True

    if changed:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError:
            return False
    return changed


def _fix_command_already_defined(work_dir, rel_path, cmd):
    """自动修「LaTeX Error: Command \\xxx already defined」。

    策略：把第一处 `\\newcommand\\xxx` 改成 `\\renewcommand`——
    保留论文作者期望的宏定义语义，比 `\\providecommand` 更安全（不会丢失论文里的数学宏）。
    """
    abs_path = os.path.join(work_dir, rel_path)
    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except OSError:
        return False

    cmd_esc = re.escape(cmd)
    pat1 = re.compile(rf"^\s*\\newcommand\*?\s*\\{cmd_esc}\b")
    pat2 = re.compile(rf"^\s*\\newcommand\*?\s*\{{\\{cmd_esc}\}}\b")

    changed = False
    for i, line in enumerate(lines):
        if pat1.search(line) or pat2.search(line):
            # 只替换 \\newcommand 这个引子，参数/宏体保留原样
            lines[i] = re.sub(r"\\newcommand\*?", r"\\renewcommand", line, count=1)
            changed = True
            break

    if not changed:
        return False

    try:
        with open(abs_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except OSError:
        return False

    return True


def _extract_pdf_text(pdf_path):
    """尽量从 PDF 提取文本——失败也无所谓，仅用于检测未解析引用。"""
    try:
        import pypdf  # type: ignore
    except Exception:
        return None

    try:
        reader = pypdf.PdfReader(pdf_path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return None


def _has_unresolved_markers(pdf_path):
    """检查 PDF 里是否还有 ?? 或 [?]——这是 LaTeX 引用 / 交叉引用未解析的标志。"""
    text = _extract_pdf_text(pdf_path)
    if not text:
        return False
    return any(m in text for m in _UNRESOLVED_CITE_MARKERS) or any(m in text for m in _UNRESOLVED_REF_MARKERS)


def _try_fix_from_logs(work_dir, main_rel, logs_text):
    """从编译日志里识别常见错误并尝试自动修复。返回 True 表示真的改动了源码。"""
    applied = False

    # 最常见的：宏重复定义（luatexja 等包定义的 \\mc 与论文宏冲突）
    m = _CMD_ALREADY_DEFINED_WITH_PATH_RE.search(logs_text)
    if m:
        rel = _map_server_path_to_local(m.group("path"), main_rel)
        cmd = m.group("cmd")
        if _fix_command_already_defined(work_dir, rel, cmd):
            applied = True

    # 兜底：日志里没给出明确路径时，尝试只取命令名，去主文件里改
    if not applied:
        m2 = _CMD_ALREADY_DEFINED_RE.search(logs_text)
        if m2:
            cmd = m2.group(1)
            if _fix_command_already_defined(work_dir, main_rel, cmd):
                applied = True

    return applied


def _pdf_is_referenced(rel_path, source_texts):
    rel_path = rel_path.replace("\\", "/")
    stem_path = os.path.splitext(rel_path)[0]
    base = os.path.basename(rel_path)
    base_stem = os.path.splitext(base)[0]
    keys = tuple(dict.fromkeys((rel_path, stem_path, base, base_stem)))

    for text in source_texts.values():
        if any(key and key in text for key in keys):
            return True
    return False


def _should_skip_resource(rel_path, source_texts):
    rel_lower = rel_path.lower()
    base_lower = os.path.basename(rel_lower)

    if rel_lower.startswith("__macosx/"):
        return True
    if base_lower in _SKIP_FILENAMES:
        return True
    if rel_lower.endswith(_BUILD_ARTIFACT_EXTS):
        return True
    if rel_lower.endswith(".pdf") and not _pdf_is_referenced(rel_path, source_texts):
        return True
    return False


def compile_online(work_dir, main_tex, output_path):
    """在线编译入口：把整个项目打包成 base64 资源 POST 给 latex.ytotech.com。"""
    work_dir, main_rel = _main_tex_relative(work_dir, main_tex)
    output_path = _resolve_output_pdf(output_path, main_rel)
    bibliography_command, prebuilt_bbl = _detect_bibliography_setup(work_dir, main_rel)
    compiler = _detect_compiler(work_dir, main_rel)

    def _build_resources():
        # 每次重试都重新构建 payload——这样自愈修改过的源码会被一并带上
        source_texts = _collect_source_texts(work_dir)
        resources = []
        main_marked = False
        for fpath, rel_cmp in _iter_project_files(work_dir):
            if _should_skip_resource(rel_cmp, source_texts):
                continue
            item = {"path": rel_cmp, "file": encode(fpath)}
            if rel_cmp == main_rel:
                item["main"] = True
                main_marked = True
            resources.append(item)
        if not main_marked:
            print(
                "错误：在 work_dir 内未找到主文件，无法标记 main。\n"
                f"  期望相对路径: {main_rel!r}\n"
                f"  work_dir: {work_dir}",
                file=sys.stderr,
            )
            sys.exit(1)
        if prebuilt_bbl and prebuilt_bbl != "__main_document__.bbl":
            resources.append(
                {
                    "path": "__main_document__.bbl",
                    "file": encode(os.path.join(work_dir, prebuilt_bbl)),
                }
            )
        return resources

    max_attempts = 3  # 首次 + 最多 2 次自愈重试
    last_error = None

    for attempt in range(1, max_attempts + 1):
        _ensure_cjk_support(work_dir, main_rel)
        # Unicode 编译栈下几乎肯定要做的源码预处理
        _preflight_comment_inputenc_fontenc(work_dir, main_rel)
        resources = _build_resources()

        payload = {
            "compiler": compiler,
            "resources": resources,
            "options": {
                "compiler": {"halt_on_error": True},
                "response": {"log_files_on_failure": True},
            },
        }
        if bibliography_command is None:
            payload["options"]["compiler"]["bibliography"] = False

        resp = requests.post(
            "https://latex.ytotech.com/builds/sync",
            json=payload,
            timeout=300,
        )

        if 200 <= resp.status_code < 300 and resp.content.startswith(b"%PDF"):
            with open(output_path, "wb") as f:
                f.write(resp.content)

            # 额外校验：编译"成功"但 PDF 里仍含 ?? / [?]（多趟编译没跑够、或前面有静默错误）
            if _has_unresolved_markers(output_path):
                last_error = "PDF 含未解析的引用标记（'??' 或 '[?]'）。"
                if attempt < max_attempts:
                    continue
                print(f"编译失败：{last_error}", file=sys.stderr)
                sys.exit(1)

            print(f"✅ 已写出 PDF（在线 {compiler}）：{os.path.abspath(output_path)}")
            return True

        # 失败：尝试解析返回的日志（JSON 错误体）并做有针对性的自愈
        logs_text = ""
        try:
            if resp.headers.get("Content-Type", "").startswith("application/json"):
                data = resp.json()
                if isinstance(data, dict):
                    log_files = data.get("log_files") or {}
                    if isinstance(log_files, dict):
                        logs_text = log_files.get("__main_document__.log") or data.get("logs") or ""
        except Exception:
            logs_text = ""

        snippet = resp.content[:4000]
        try:
            msg = snippet.decode("utf-8", errors="replace")
        except Exception:
            msg = repr(snippet[:500])

        last_error = f"HTTP {resp.status_code}: {msg if msg.strip() else '(非文本响应，已截断)'}"
        if logs_text:
            if attempt < max_attempts and _try_fix_from_logs(work_dir, main_rel, logs_text):
                # 自愈成功，立刻重跑
                continue

        # 没有可修复点或已用尽重试次数
        print("在线编译失败（attempt %d/%d）。" % (attempt, max_attempts), file=sys.stderr)
        print(last_error, file=sys.stderr)
        if logs_text:
            print("\n--- 编译日志（截断）---", file=sys.stderr)
            print(logs_text[-8000:], file=sys.stderr)
        sys.exit(1)

    print("在线编译失败。", file=sys.stderr)
    if last_error:
        print(last_error, file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 本地 xelatex 编译路径
# ---------------------------------------------------------------------------

_LOCAL_BUILD_DIRNAME = "build"
_LOCAL_MAX_ATTEMPTS = 3


def _xelatex_available():
    return shutil.which("xelatex") is not None


def _run(cmd, cwd, env=None):
    """运行子进程，返回 (returncode, stdout, stderr)，合并 stdout/stderr 给日志解析用。"""
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except FileNotFoundError as exc:
        return 127, "", f"{exc}"


def _local_one_pass(work_dir, main_rel, build_dir, bibliography_command, prebuilt_bbl):
    """跑一轮完整的 xelatex 序列。返回 (ok, log_text)。
    成功 ok=True；失败 ok=False，log_text 给上层尝试自愈用。
    """
    main_stem = os.path.splitext(os.path.basename(main_rel))[0]
    os.makedirs(build_dir, exist_ok=True)

    # 若存在预编译好的 .bbl，先放进 build/ 让 xelatex 读
    if prebuilt_bbl:
        src_bbl = os.path.join(work_dir, prebuilt_bbl)
        dst_bbl = os.path.join(build_dir, f"{main_stem}.bbl")
        try:
            shutil.copy2(src_bbl, dst_bbl)
        except OSError:
            pass

    common_xelatex = [
        "xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-output-directory={_LOCAL_BUILD_DIRNAME}",
        main_rel,
    ]

    # 第一遍 xelatex
    rc, out, err = _run(common_xelatex, cwd=work_dir)
    log_text = out + "\n" + err
    if rc != 0:
        log_text += _read_local_log(build_dir, main_stem)
        return False, log_text

    # 处理参考文献
    if bibliography_command == "bibtex":
        env = os.environ.copy()
        # 让 bibtex 同时能从源码目录找到 .bib
        env["BIBINPUTS"] = f".:{env.get('BIBINPUTS', '')}"
        env["BSTINPUTS"] = f".:{env.get('BSTINPUTS', '')}"
        rc, out, err = _run(
            ["bibtex", os.path.join(_LOCAL_BUILD_DIRNAME, main_stem)],
            cwd=work_dir,
            env=env,
        )
        # bibtex 出错不直接退出（很多论文 bib 有警告，但仍可继续），但要记下来
        log_text += "\n" + out + "\n" + err
    elif bibliography_command == "biber":
        rc, out, err = _run(
            ["biber", f"--output-directory={_LOCAL_BUILD_DIRNAME}", main_stem],
            cwd=work_dir,
        )
        log_text += "\n" + out + "\n" + err

    # 第二、三遍 xelatex 解析交叉引用
    for _ in range(2):
        rc, out, err = _run(common_xelatex, cwd=work_dir)
        log_text += "\n" + out + "\n" + err
        if rc != 0:
            log_text += _read_local_log(build_dir, main_stem)
            return False, log_text

    return True, log_text


def _read_local_log(build_dir, main_stem):
    log_path = os.path.join(build_dir, f"{main_stem}.log")
    if not os.path.isfile(log_path):
        return ""
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            return "\n--- 本地 xelatex 日志 ---\n" + f.read()
    except OSError:
        return ""


def compile_local(work_dir, main_tex, output_path):
    """本地 xelatex 编译。失败时尝试有限次自愈（macro 重定义等）。"""
    if not _xelatex_available():
        print(
            "错误：本地未检测到 xelatex（PATH 里找不到）。请安装 TeX Live，或改用 --engine online。",
            file=sys.stderr,
        )
        sys.exit(1)

    work_dir, main_rel = _main_tex_relative(work_dir, main_tex)
    output_path = _resolve_output_pdf(output_path, main_rel)
    bibliography_command, prebuilt_bbl = _detect_bibliography_setup(work_dir, main_rel)
    build_dir = os.path.join(work_dir, _LOCAL_BUILD_DIRNAME)
    main_stem = os.path.splitext(os.path.basename(main_rel))[0]
    last_log = ""

    for attempt in range(1, _LOCAL_MAX_ATTEMPTS + 1):
        _ensure_cjk_support(work_dir, main_rel)
        _preflight_comment_inputenc_fontenc(work_dir, main_rel)

        ok, log_text = _local_one_pass(
            work_dir, main_rel, build_dir, bibliography_command, prebuilt_bbl
        )
        last_log = log_text

        if ok:
            built_pdf = os.path.join(build_dir, f"{main_stem}.pdf")
            if not os.path.isfile(built_pdf):
                print(
                    f"错误：本地编译返回成功但 PDF 未生成：{built_pdf}",
                    file=sys.stderr,
                )
                sys.exit(1)

            # 额外校验：避免引用/交叉引用未解析的 PDF
            if _has_unresolved_markers(built_pdf):
                if attempt < _LOCAL_MAX_ATTEMPTS:
                    print(
                        f"⚠️  本地编译 PDF 含未解析引用（'??' 或 '[?]'），将再试一轮 ({attempt}/{_LOCAL_MAX_ATTEMPTS})",
                        file=sys.stderr,
                    )
                    continue
                print(
                    "编译失败：本地 PDF 仍含未解析引用（'??' 或 '[?]'）。",
                    file=sys.stderr,
                )
                sys.exit(1)

            shutil.copy2(built_pdf, output_path)
            print(f"✅ 已写出 PDF（本地 xelatex）：{os.path.abspath(output_path)}")
            return True

        # 失败：尝试从日志做有限自愈，然后再来一轮
        if attempt < _LOCAL_MAX_ATTEMPTS and _try_fix_from_logs(work_dir, main_rel, log_text):
            print(
                f"🔧 已尝试自动修复，重新编译 ({attempt + 1}/{_LOCAL_MAX_ATTEMPTS})",
                file=sys.stderr,
            )
            continue

        # 无可修复或重试已用完
        print(
            f"本地编译失败（attempt {attempt}/{_LOCAL_MAX_ATTEMPTS}）。",
            file=sys.stderr,
        )
        print("\n--- 本地编译日志（截断）---", file=sys.stderr)
        print(last_log[-8000:], file=sys.stderr)
        sys.exit(1)

    print("本地编译失败。", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 引擎调度
# ---------------------------------------------------------------------------


def compile_dispatch(work_dir, main_tex, output_path, engine):
    """根据 --engine 选项分发到本地或在线编译。"""
    if engine == "local":
        return compile_local(work_dir, main_tex, output_path)

    if engine == "online":
        return compile_online(work_dir, main_tex, output_path)

    # engine == auto：装了 xelatex 就用本地，否则走在线
    if _xelatex_available():
        print("ℹ️  --engine auto：检测到本地 xelatex，使用本地编译。", file=sys.stderr)
        return compile_local(work_dir, main_tex, output_path)
    print(
        "ℹ️  --engine auto：未检测到本地 xelatex，回落到在线编译（latex.ytotech.com）。",
        file=sys.stderr,
    )
    return compile_online(work_dir, main_tex, output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ChineseXiv 编译：本地 xelatex 或在线 latex-on-http 双引擎。",
    )
    parser.add_argument("work_dir", help="源码目录")
    parser.add_argument("main_tex", help="主 .tex 文件（相对 work_dir 或绝对路径）")
    parser.add_argument("output_pdf_path", help="输出 PDF 路径")
    parser.add_argument(
        "--engine",
        choices=("auto", "local", "online"),
        default="auto",
        help="编译引擎：auto（默认）/ local / online",
    )
    args = parser.parse_args()
    compile_dispatch(args.work_dir, args.main_tex, args.output_pdf_path, args.engine)
