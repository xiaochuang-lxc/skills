#!/usr/bin/env python3
r"""
ChineseXiv 第二步：拉取 arXiv 源码并准备翻译副本。

工作流程：
  1. 从 arxiv.org 下载论文 e-print（tar.gz / gz / 单 .tex 都兼容）；
  2. 解压到 work_dir，递归找出所有 .tex 文件；
  3. 通过 `\documentclass` 标志定位主文件；
  4. 通过 arXiv API（失败则回落 abs 网页）抓论文英文标题，用作 PDF 备用文件名；
  5. 把主文件以及它通过 `\input{}` / `\include{}` 引用的子 .tex 复制为 `_zh.tex` 副本，
     并改写中文主文件里的 input 引用指向 `_zh` 版本——
     这样英文原文文件原样不动，模型只会在 `_zh` 副本上做翻译；
  6. 直接下载 arXiv 官方已编译的英文 PDF，按英文标题命名后落在 source/ 的父目录
     （即 $OUTPUT_DIR）里，和稍后生成的中文译稿 PDF 并排存放——保证「英文原文 + 中文
     译文」始终同时在论文文件夹里。拿不到官方 PDF 时返回空，由上层回落到用 compile.py
     编译英文 MAIN_TEX。

用法：
  python download.py <paper_id> <work_dir>      # work_dir 约定为 $OUTPUT_DIR/source

向 stdout 输出六行 shell 变量赋值（供调用方 eval 或解析）：
  WORK_DIR=<源码目录绝对路径>
  MAIN_TEX=<英文主文件相对路径，只读>
  MAIN_TEX_ZH=<中文翻译主文件相对路径>
  PDF_NAME=<论文英文标题，仅供生成 PDF 备用名>
  PDF_NAME_EN=<英文原文 PDF 的跨平台安全文件名（冒号等已替换）>
  PDF_EN=<已下载的英文 PDF 绝对路径；下载失败则为空字符串>
"""
import gzip
import html
import os
import re
import shutil
import sys
import tarfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


def extract_tar_archive(tf, work_dir):
    """解压 tar 归档；Python 3.12+ 启用更安全的 data filter，避免目录穿越。"""
    if sys.version_info >= (3, 12):
        tf.extractall(work_dir, filter="data")
    else:
        tf.extractall(work_dir)


def download_and_extract(paper_id, work_dir):
    """下载 e-print 到 work_dir，并按 tar / gzip / 裸文件三种情况解压。

    返回所有 .tex 文件的相对路径列表（相对 work_dir）。
    若未找到任何 .tex，说明论文可能只有 PDF 没有源码，直接退出。
    """
    os.makedirs(work_dir, exist_ok=True)
    source_path = os.path.join(work_dir, "source.bin")

    url = f"https://arxiv.org/e-print/{paper_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(source_path, "wb") as f:
                shutil.copyfileobj(resp, f)
    except Exception as e:
        print(f"错误：下载失败 {url}\n{e}", file=sys.stderr)
        sys.exit(1)

    # 依次尝试 tar / gzip / 裸文件三种情况——arXiv e-print 三种都见过
    extracted = False
    try:
        if tarfile.is_tarfile(source_path):
            with tarfile.open(source_path) as tf:
                extract_tar_archive(tf, work_dir)
            extracted = True
    except Exception:
        pass
    if not extracted:
        try:
            with gzip.open(source_path, "rb") as gz, open(os.path.join(work_dir, "paper.tex"), "wb") as out:
                shutil.copyfileobj(gz, out)
            extracted = True
        except Exception:
            pass
    if not extracted:
        # 兜底：当作单个未压缩的 .tex 处理
        shutil.copy(source_path, os.path.join(work_dir, "paper.tex"))
    os.remove(source_path)

    tex_files = []
    for root, _, files in os.walk(work_dir):
        for f in files:
            if f.endswith(".tex"):
                tex_files.append(os.path.relpath(os.path.join(root, f), work_dir))
    if not tex_files:
        print("错误：未找到任何 .tex 文件，该论文可能只有 PDF 没有源码。", file=sys.stderr)
        sys.exit(1)
    return tex_files


# 正则常量：识别主文件、解析 input/include、抓 arXiv 标题
_RE_DOCCLASS = re.compile(r"\\documentclass")
_RE_INPUT = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
_RE_CITATION_TITLE = re.compile(
    r'<meta\s+name=["\']citation_title["\']\s+content=["\'](.*?)["\']',
    re.IGNORECASE,
)
_RE_HTML_TITLE = re.compile(r"<title>\s*(?:\[[^\]]+\]\s*)?(.*?)\s*</title>", re.IGNORECASE | re.DOTALL)


def find_main_tex(work_dir, tex_files):
    r"""在所有 .tex 里找主文件。

    判据：包含 `\documentclass` 的文件即候选；若有多个候选，挑 `\input/\include`
    引用最多的那个（通常是真正的入口），相对更稳。
    """
    candidates = []
    for tf in tex_files:
        try:
            content = open(os.path.join(work_dir, tf), "r", encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if _RE_DOCCLASS.search(content):
            candidates.append((tf, content))
    if not candidates:
        print("错误：所有 .tex 里都没找到 \\documentclass，无法判断主文件。", file=sys.stderr)
        sys.exit(1)
    if len(candidates) == 1:
        return candidates[0]
    return max(candidates, key=lambda c: len(_RE_INPUT.findall(c[1])))


def fetch_arxiv_title(paper_id):
    """优先走 arXiv API 取标题，失败再回落到 abs 页面 meta 信息。"""
    title = fetch_arxiv_title_from_api(paper_id)
    if title:
        return title
    return fetch_arxiv_title_from_abs_page(paper_id)


def fetch_arxiv_title_from_api(paper_id):
    """通过 arXiv 官方 API（Atom feed）取论文标题，最稳的一条路径。"""
    query = urllib.parse.urlencode({"id_list": paper_id})
    url = f"https://arxiv.org/api/query?{query}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "chinesexiv/1.0 (+https://arxiv.org/help/api/user-manual)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception:
        return None
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    entry = root.find("atom:entry", _ATOM_NS)
    if entry is None:
        return None
    title_el = entry.find("atom:title", _ATOM_NS)
    if title_el is None:
        return None
    # 标题里常有换行、连续空格，先做归一化
    title = " ".join(title_el.itertext()).strip()
    return re.sub(r"\s+", " ", title) or None


def fetch_arxiv_title_from_abs_page(paper_id):
    """回落方案：抓 https://arxiv.org/abs/<id> 网页里的 meta 标题。"""
    url = f"https://arxiv.org/abs/{paper_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            page = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None
    for pattern in (_RE_CITATION_TITLE, _RE_HTML_TITLE):
        match = pattern.search(page)
        if not match:
            continue
        title = html.unescape(match.group(1)).strip()
        title = re.sub(r"\s+", " ", title)
        if title:
            return title
    return None


def pdf_name_from_title(title, fallback, max_len=240):
    """根据论文标题生成 PDF 备用文件名：保留原文本，仅剔除文件系统非法字符。

    若标题为空则用 fallback（通常是主文件 stem）。
    """
    if not title or not str(title).strip():
        return fallback
    s = " ".join(str(title).split())
    s = s.replace("\x00", "")
    s = s.replace("/", "-").replace("\\", "-")
    if os.name == "nt":
        # Windows 额外不允许的字符
        for ch in '<>:"|?*':
            s = s.replace(ch, "_")
    s = s.strip().rstrip(".")
    if not s:
        return fallback
    if max_len and len(s) > max_len:
        s = s[:max_len].rstrip()
    return s


def pdf_name_en_from_title(title, fallback, max_len=240):
    r"""英文原文 PDF 的文件名：在 pdf_name_from_title 基础上做跨平台加固 + 去空格。

    命名规则（与中文目录/PDF 命名同构，且在 Windows、网盘、Git、URL 下都安全）：
      - 半角/全角冒号 `:`/`：`（连同周围空格）→ `_`：视作「方法名 ↔ 副标题」的分隔，
        与中文把 `：` 换成 `_` 一致，例如 `GeoGround: A Unified...` → `GeoGround_A_Unified_...`；
      - 空格 → `_`：文件名不保留空格，免去 shell / URL / Git 里反复转义的麻烦；
      - 标题里**原有**的连字符 `-` 原样保留（如 `Vision-Language`）——它与代表空格的 `_`
        区分开，因此英文 PDF 名大体可还原出原标题；
      - 其余 Windows/网盘不接受的字符 `<>"|?*` → `_`（`/`、`\` 已在 pdf_name_from_title 里转 `-`）。
    最终形如 `GeoGround_A_Unified_Large_Vision-Language_Model_for_Remote_Sensing_Visual_Grounding`。
    """
    name = pdf_name_from_title(title, fallback, max_len=max_len)
    name = re.sub(r"\s*[:：]\s*", "_", name)  # 冒号（含周围空格）压成单个 _
    for ch in '<>"|?*':
        name = name.replace(ch, "_")
    name = re.sub(r"\s+", "_", name)          # 其余空白 → _
    name = re.sub(r"_+", "_", name).strip("_").rstrip(".")  # 合并连续 _，去首尾 _ 和句点
    return name or fallback


def download_pdf(paper_id, dest_path, timeout=45):
    r"""下载 arXiv 官方已编译的英文 PDF 到 dest_path，与中文译稿 PDF 并列保存。

    为什么直接下 arXiv 的 PDF：它是作者最终排版、官方编译的版本，比本地重新编译英文
    源码更稳、更快、也更忠于原貌。只有这里拿不到 PDF 时，上层才回落到用 compile.py
    编译英文 MAIN_TEX。

    URL 顺序：**export.arxiv.org 镜像优先**——arXiv 主站 (arxiv.org) 对最新提交的论文
    偶发连接超时（实测出现 http=000 的长时间挂起），export 镜像稳定得多；主站随后作为
    后备。单个 URL 用较短 timeout（默认 45s）快速失败、尽早切到下一个，避免在挂起的连接
    上空等几分钟。只有响应确实以 %PDF 魔数开头才落盘（避免把限流页、HTML 错误页误存成
    .pdf）。成功返回 dest_path，全部失败返回 None。
    """
    urls = (
        f"https://export.arxiv.org/pdf/{paper_id}",
        f"https://arxiv.org/pdf/{paper_id}",
        f"https://arxiv.org/pdf/{paper_id}.pdf",
    )
    for url in urls:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
        except Exception:
            continue
        if data[:4] != b"%PDF":
            continue
        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(data)
        return dest_path
    return None


def _sh_var_assign(name, value):
    """把 (name, value) 输出成可被 sh `eval` 安全消费的 `NAME='value'` 形式。"""
    esc = str(value).replace("'", "'\\''")
    return f"{name}='{esc}'"


def _zh_sibling(rel_path):
    """给一个 .tex 相对路径，返回它对应的 `_zh.tex` 副本路径。"""
    rel_path = rel_path.replace("\\", "/")
    base, ext = os.path.splitext(rel_path)
    return f"{base}_zh{ext or '.tex'}"


def _copy_main_companion(work_dir, main_rel, ext):
    """复制与主文件同名、扩展名为 `ext` 的伴随文件到 `_zh` 副本旁。

    场景：很多 arXiv 论文不发 .bib，而是直接附带一份预生成的 `main.bbl`。当我们把
    `main.tex` 复制为 `main_zh.tex` 后，jobname 变成 `main_zh`，LaTeX 在
    `\\bibliography{...}` 处会寻找 `<jobname>.bbl`，即 `main_zh.bbl`——根目录没有这个
    文件名，引用就全是 `??`。把 `main.bbl` 一并复制为 `main_zh.bbl`，无论用哪个工具
    编译（chinesexiv 自己的 compile.py、LaTeX Workshop recipe、命令行 xelatex
    都能跑通）。

    返回新建副本的相对路径；若源文件不存在或与目标同路径则返回 None。
    """
    src_rel = os.path.splitext(main_rel)[0] + ext
    src_path = os.path.join(work_dir, src_rel)
    if not os.path.isfile(src_path):
        return None
    zh_main_rel = _zh_sibling(main_rel)
    dst_rel = os.path.splitext(zh_main_rel)[0] + ext
    dst_path = os.path.join(work_dir, dst_rel)
    if os.path.realpath(src_path) == os.path.realpath(dst_path):
        return None
    os.makedirs(os.path.dirname(dst_path) or work_dir, exist_ok=True)
    shutil.copy2(src_path, dst_path)
    return dst_rel


def prepare_translation_copy(work_dir, main_rel):
    r"""为翻译准备 `_zh.tex` 副本，并改写中文主文件里的 input/include 引用。

    具体动作：
      - 把主 .tex 复制为 `<name>_zh.tex`；
      - 解析主文件里的 `\input{x}` / `\include{x}`，逐个把 `x.tex` 也复制为 `x_zh.tex`，
        并在中文主文件里把 `{x}` 改写为 `{x_zh}`（不带 .tex 后缀，与 LaTeX 习惯一致）；
      - 把与主文件同名的 `.bbl`（arXiv 论文常见的预生成参考文献）也复制成 `_zh.bbl`，
        使中文版 jobname 对应的辅助文件能被 LaTeX 找到；
      - 这样英文原文整套保持只读，翻译只动 `_zh` 系列。

    返回值：中文主文件相对 work_dir 的路径。
    """
    main_rel = main_rel.replace("\\", "/")
    main_path = os.path.join(work_dir, main_rel)
    try:
        with open(main_path, "r", encoding="utf-8", errors="replace") as f:
            main_text = f.read()
    except OSError as exc:
        print(f"错误：无法读取主文件 {main_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    rewritten = main_text
    for match in _RE_INPUT.finditer(main_text):
        target = match.group(1).strip()
        # LaTeX 允许省略 .tex，因此两种都试一下
        candidates = [target, f"{target}.tex"] if not target.endswith(".tex") else [target]
        src_rel = None
        for cand in candidates:
            cand_path = os.path.join(work_dir, cand)
            if os.path.isfile(cand_path):
                src_rel = cand
                break
        if not src_rel:
            continue
        dst_rel = _zh_sibling(src_rel)
        dst_path = os.path.join(work_dir, dst_rel)
        os.makedirs(os.path.dirname(dst_path) or work_dir, exist_ok=True)
        shutil.copy2(os.path.join(work_dir, src_rel), dst_path)
        # 改写引用——保持与原文相同的「写不写 .tex 后缀」风格
        replacement = dst_rel[:-4] if (not target.endswith(".tex") and dst_rel.endswith(".tex")) else dst_rel
        rewritten = rewritten.replace("{" + target + "}", "{" + replacement + "}")

    main_zh_rel = _zh_sibling(main_rel)
    main_zh_path = os.path.join(work_dir, main_zh_rel)
    with open(main_zh_path, "w", encoding="utf-8") as f:
        f.write(rewritten)

    # 与主文件同名的辅助产物（最常见的是 .bbl，少数项目也带 .ind/.glo 等）一并复制副本，
    # 避免 jobname 改变导致 LaTeX 找不到这些文件。
    for ext in (".bbl",):
        _copy_main_companion(work_dir, main_rel, ext)

    return main_zh_rel


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法：python download.py <paper_id> <work_dir>", file=sys.stderr)
        sys.exit(2)
    paper_id, work_dir = sys.argv[1], sys.argv[2]
    tex_files = download_and_extract(paper_id, work_dir)
    rel_path, _ = find_main_tex(work_dir, tex_files)
    rel_path = rel_path.replace("\\", "/")
    fallback = os.path.splitext(os.path.basename(rel_path))[0]
    title = fetch_arxiv_title(paper_id)
    pdf_name = pdf_name_from_title(title, fallback)
    pdf_name_en = pdf_name_en_from_title(title, fallback)
    main_zh_rel = prepare_translation_copy(work_dir, rel_path)

    # 英文原文 PDF：与 source/ 同级（即 $OUTPUT_DIR 下），和中文译稿 PDF 并排。
    # work_dir 约定为 $OUTPUT_DIR/source，故其父目录就是 $OUTPUT_DIR。下载阶段目录名还是
    # 占位的 $PARENT/$PAPER_ID，稍后整体 mv 成最终名时，这份英文 PDF 会跟着一起搬过去。
    output_dir = os.path.dirname(os.path.abspath(work_dir))
    pdf_en_path = os.path.join(output_dir, pdf_name_en + ".pdf")
    pdf_en = download_pdf(paper_id, pdf_en_path)
    if not pdf_en:
        print(
            f"提示：未能直接下载英文 PDF（{paper_id}）；"
            f"请回落到 compile.py 编译英文 MAIN_TEX 到 $OUTPUT_DIR/$PDF_NAME_EN.pdf。",
            file=sys.stderr,
        )

    # stdout 是契约：调用方按 KEY='value' 格式解析
    print(_sh_var_assign("WORK_DIR", os.path.abspath(work_dir)))
    print(_sh_var_assign("MAIN_TEX", rel_path))
    print(_sh_var_assign("MAIN_TEX_ZH", main_zh_rel))
    print(_sh_var_assign("PDF_NAME", pdf_name))
    print(_sh_var_assign("PDF_NAME_EN", pdf_name_en))
    print(_sh_var_assign("PDF_EN", pdf_en or ""))
