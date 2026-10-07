#!/usr/bin/env python3
"""
ChineseXiv 第四步收尾：清理本地编译产物，保留译稿源码。

会删除：
  - 任意层级下名为 `build/` 的子目录（约定为本地 xelatex 的输出目录）；
  - `build/` 内的散落编译中间产物（`.aux`/`.log`/`.bbl`/…）；
  - 旧版残留的 `.tmp_arxiv/` 目录（向后兼容）；
  - 旧版 inspect 临时报告（`inspect_*.txt`）。

会保留：
  - 所有 `.tex` / `.bib` / `.cls` / `.sty` / `figs/` 资源——方便用户对照英文原文
    与 `_zh.tex` 译稿，必要时手动重编；
  - 与源码并列、由原 arXiv 源码自带的 `.bbl` 文件（许多 arXiv 论文不发 `.bib`
    而是直接附带预生成的 `.bbl`，这种 `.bbl` 是 \\textit{源码}而不是中间产物，
    一旦删了 main_zh.tex 引用就解析不出来）。本脚本只清理 `build/` 子目录里
    的中间产物，不动 source 根目录的文件。

用法：
  python cleanup.py <base_dir>
"""
import os
import re
import shutil
import sys


# 旧版 inspect 报告文件名匹配
INSPECT_OUTPUT_RE = re.compile(r"^inspect_.*\.txt$")

# 公认的编译中间产物扩展名，整套删——仅在 `build/` 内生效
INTERMEDIATE_EXTS = {
    ".aux", ".log", ".out", ".toc", ".bbl", ".blg",
    ".fls", ".fdb_latexmk", ".synctex.gz", ".nav", ".snm", ".vrb",
    ".lof", ".lot", ".idx", ".ilg", ".ind", ".run.xml", ".bcf",
    ".xdv", ".dvi", ".ps",
}


def _has_intermediate_ext(filename):
    """文件名是否以编译中间产物扩展名结尾。"""
    lower = filename.lower()
    for ext in INTERMEDIATE_EXTS:
        if lower.endswith(ext):
            return True
    return False


def remove_build_dirs(root):
    """递归找并删所有 `build/` 子目录。注意删完要从 dirnames 摘掉避免重复 walk。"""
    removed = []
    for dirpath, dirnames, _filenames in os.walk(root):
        if "build" in dirnames:
            target = os.path.join(dirpath, "build")
            try:
                shutil.rmtree(target)
                removed.append(target)
                dirnames.remove("build")
            except OSError:
                pass
    return removed


def remove_legacy_tmp(root):
    """删旧版本（基于上游 Leey21）留下的 `.tmp_arxiv/` 工作目录。"""
    legacy = os.path.join(root, ".tmp_arxiv")
    if os.path.isdir(legacy):
        try:
            shutil.rmtree(legacy)
            return [legacy]
        except OSError:
            pass
    return []


def remove_inspect_outputs(base_dir):
    """删 inspect_tex.py 旧版本可能写出的临时报告文件。"""
    removed = []
    for entry in os.listdir(base_dir):
        path = os.path.join(base_dir, entry)
        if not os.path.isfile(path):
            continue
        if not INSPECT_OUTPUT_RE.fullmatch(entry):
            continue
        os.remove(path)
        removed.append(path)
    return removed


def cleanup(base_dir):
    """清理入口：依次跑各步并打印日志。

    设计原则：宁可漏删，绝不误删。源码目录里若残留 `.aux` 这种小文件
    用户可以手动清掉；但 `.bbl` 一旦被错删，下次重编就会出现一堆 `??`。
    """
    base_dir = os.path.abspath(base_dir)
    total = 0

    for path in remove_build_dirs(base_dir):
        print(f"✅ 已删除 build 目录：{path}")
        total += 1
    for path in remove_legacy_tmp(base_dir):
        print(f"✅ 已删除旧版 .tmp_arxiv：{path}")
        total += 1
    for path in remove_inspect_outputs(base_dir):
        print(f"✅ 已删除 inspect 临时报告：{path}")
        total += 1

    if total == 0:
        print(f"无需清理：{base_dir}")
    print(f"📂 译稿源码已保留：{base_dir}/source/")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法：python cleanup.py <base_dir>", file=sys.stderr)
        sys.exit(2)
    cleanup(sys.argv[1])
