#!/usr/bin/env python3
"""Verification helpers for the PDF pipeline. Truncation, bleed, numbering drift
and - most insidiously - dropped formulas are invisible when inspecting outputs
one by one, so all four checks are mandatory before a translated PDF ships.

Usage:
  pdf_audit.py sheet FIGDIR OUTPREFIX [--cols 3] [--cell 470x360]
      Tiles every figureN.png/tableN.png into contact sheets for one-glance
      visual audit (truncation / bleed / leftover English captions).

  pdf_audit.py numbers COMPILED_PDF TEXT_FILE
      Compares the caption sequence rendered in the compiled Chinese PDF
      (图 N: / 表 N:) with the Figure N: / Table N: captions in the extracted
      source text. Non-zero exit on missing, duplicated or out-of-order numbers.

  pdf_audit.py coverage MAIN_ZH_TEX INVENTORY_JSON
      Guards against the classic PDF-translation failure: formulas, algorithms
      and theorem-like blocks silently dropped because the extracted text
      renders them as glyph soup. Checks, against an inventory produced by
      pdf_inventory.py:
        * \\begin{equation}/align/gather count == numbered equations in source
        * every Algorithm n has a 算法 n block in the tex
        * every Theorem/Lemma/Definition/Corollary/Proposition has its Chinese
          marker (定理/引理/定义/推论/命题) with the same number
        * \\begin{figure} / \\begin{table} counts match the source counts and
          every figureN.png is actually \\includegraphics-ed
      Prints a MISSING list and exits non-zero if anything is uncovered.
"""
import json
import os
import re
import sys

import pymupdf
from PIL import Image, ImageDraw

import doc_class

TH_ZH = {"Theorem": "定理", "Lemma": "引理", "Definition": "定义",
         "Corollary": "推论", "Proposition": "命题"}

def sheet(figdir, prefix, cols, cw, ch):
    files = sorted((f for f in os.listdir(figdir) if f.endswith(".png")),
                   key=lambda f: (f.startswith("table"),
                                  int(re.search(r"(\d+)", f).group(1))))
    rows, per = 3, cols * 3
    made = []
    for si in range(0, len(files), per):
        chunk = files[si:si + per]
        sh = Image.new("RGB", (cols * cw, rows * ch), (240, 240, 240))
        d = ImageDraw.Draw(sh)
        for i, f in enumerate(chunk):
            im = Image.open(os.path.join(figdir, f)).convert("RGB")
            aw, ah, pad, lbl = cw - 20, ch - 42, 10, 22
            sc = min(aw / im.width, ah / im.height)
            im2 = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))))
            cx, cy = (i % cols) * cw, (i // cols) * ch
            sh.paste(im2, (cx + pad + int((aw - im2.width) / 2), cy + pad + lbl))
            d.text((cx + 6, cy + 5), f"{f} {im.width}x{im.height}", fill=(200, 0, 0))
            d.rectangle([cx + pad, cy + pad + lbl, cx + cw - pad, cy + ch - pad],
                        outline=(255, 0, 0))
        p = f"{prefix}_{si // per + 1}.png"
        sh.save(p)
        made.append(p)
    print("sheets:", made)


def numbers(pdf, txt):
    src = open(txt, encoding="utf-8").read()
    # 抽取文本的题注行可能带超链接残留符（PCI-SIG 的 § 既出现在行首也出现在
    # "Figure§ 1-2" 中间），先整行剔除再别行首杂符，否则 ^ 锚定与类别判定都失效。
    norm = "\n".join(re.sub(r"^[^A-Za-z\d]{0,3}", "", l.replace("§", ""))
                     for l in src.splitlines())
    # 类别从抽取文本判定（这里的 pdf 是译后 PDF，不能用来探测源版式）。
    spec = any(doc_class.PREFIX_CAP_RE.match(l.strip()) for l in norm.splitlines())
    want_f = sorted({int(x) for x in re.findall(r"^Figure\s+(\d+):", norm, re.M)})
    want_t = sorted({int(x) for x in re.findall(r"^Table\s+(\d+):", norm, re.M)})
    if spec:   # 协议/标准类：编号带章节前缀且无冒号
        want_f = sorted(set(want_f) | {int(x.split("-")[1]) for x in
                            re.findall(r"^Figure\s+(\d+-\d+)\s+[A-Z0-9(]", norm, re.M)})
        want_t = sorted(set(want_t) | {int(x.split("-")[1]) for x in
                            re.findall(r"^Table\s+(\d+-\d+)\s+[A-Z0-9(]", norm, re.M)})
    # IEEE/类 IEEE 题注（Fig. N. 独立行 / 单行式 / TABLE 罗马）：集合语义并入。
    # 正文交叉引用只会引用已存在的图号，不会污染集合；ACM 文档这些模式不命中。
    _lines = norm.splitlines()
    ieee_f = {int(m.group(1)) for m in
              (doc_class.IEEE_FIG_LABEL_RE.fullmatch(l) for l in _lines) if m}
    ieee_f |= {int(m.group(1)) for m in
               (doc_class.IEEE_FIG_ONELINE_RE.match(l) for l in _lines) if m}
    ieee_t = {doc_class.roman2int(m.group(1)) for m in
              (doc_class.IEEE_TAB_RE.fullmatch(l) for l in _lines) if m}
    want_f = sorted(set(want_f) | ieee_f)
    want_t = sorted(set(want_t) | {n for n in ieee_t if n})
    doc = pymupdf.open(pdf)
    got_f, got_t = [], []
    # 渲染侧只认题注行：行首 + 编号后要么到行尾、要么跟一个宽间隔（labelsep）。
    # 仅锁定行首不够：以「表 2-5 定义了…」开头的句子会被当成第二个题注。
    rf = r"^图\s*(\d+):" if not spec else r"^图\s*(\d+(?:-\d+)?)(?:\s{2,}|\s*$)"
    rt = r"^表\s*(\d+):" if not spec else r"^表\s*(\d+(?:-\d+)?)(?:\s{2,}|\s*$)"
    for i in range(doc.page_count):
        s = doc[i].get_text()
        got_f += [int(x.split("-")[-1]) for x in re.findall(rf, s, re.M)]
        got_t += [int(x.split("-")[-1]) for x in re.findall(rt, s, re.M)]
    ok = True
    for name, want, got in (("figures", want_f, got_f), ("tables", want_t, got_t)):
        if not want:
            # 空对空不是通过：以前这里会打印 "OK figures: 1..0" 造成假绿。
            print(f"WARN {name}: no captions of this kind in source text; "
                  f"numbers gate vacuous for {name}")
            continue
        seq = [g for g in got if g in want]
        if seq != want:
            ok = False
            print(f"MISMATCH {name}: source {want} rendered {seq}")
        else:
            print(f"OK {name}: 1..{want[-1]} contiguous and in order")
    sys.exit(0 if ok else 1)


def coverage(tex_path, inv_path):
    tex = open(tex_path, encoding="utf-8").read()
    inv = json.load(open(inv_path, encoding="utf-8"))
    missing = []

    n_eq_src = len(inv["equations"])
    n_eq_tex = len(re.findall(r"\\begin\{(equation|align|gather|multline)\*?\}", tex))
    if n_eq_tex < n_eq_src:
        missing.append(f"displayed equations: source {n_eq_src}, tex {n_eq_tex}")

    for a in inv["algorithms"]:
        if not (f"算法 {a['n']}" in tex or f"算法~{a['n']}" in tex
                or f"Algorithm {a['n']}" in tex):
            missing.append(f"Algorithm {a['n']} ({a['title'][:40]})")

    for t in inv["theorems"]:
        zh = TH_ZH[t["kind"]]
        if not re.search(rf"{zh}\s*~?\s*{re.escape(t['n'])}", tex):
            missing.append(f"{t['kind']} {t['n']}")

    nf_src, nt_src = len(inv["figures"]), len(inv["tables"])
    # 跳页的大图/大表不能放在 [H] 浮动体里（会因 Overfull \vbox too high 被静默截断），
    # 常见写法是非浮动上下文 + \captionof{figure|table}，它同样递增计数器。
    # 因此两种写法都计为一个资产环境。
    nf_tex = len(re.findall(r"\\begin\{figure\}", tex)) + len(re.findall(r"\\captionof\{figure\}", tex))
    nt_tex = len(re.findall(r"\\begin\{table\*?\}", tex)) + len(re.findall(r"\\captionof\{table\}", tex))
    if nf_tex != nf_src:
        missing.append(f"figure environments: source {nf_src}, tex {nf_tex}")
    if nt_tex != nt_src:
        missing.append(f"table environments: source {nt_src}, tex {nt_tex}")
    # A source figure is covered either as a clipped image (figureN.png) or as a
    # rebuilt figure environment (e.g. a cost table re-typeset inside \begin
    # {figure}, which is common when the original 'Figure N' is really a table).
    # Requiring the png for every figure was a false positive; instead trust the
    # environment-count equality above and check clipped + rebuilt account for all.
    clipped_f = [f for f in inv["figures"] if f"{{figure{f['n']}.png}}" in tex]
    need_rf = nf_src - len(clipped_f)
    have_rf = nf_tex - len(clipped_f)
    if have_rf < need_rf:
        missing.append(f"{need_rf - have_rf} non-clipped figure(s) have no "
                       f"matching \\begin{{figure}} (source {nf_src}, "
                       f"clipped {len(clipped_f)}, tex figure-env {nf_tex})")
    # A source table is covered either as a clipped image (tableN.png) or as a
    # rebuilt LaTeX table. Do NOT require a numeric tab:N label - rebuilt tables
    # almost always carry a descriptive \label{tab:fpgalat}, so that check was a
    # false positive. Instead, trust the environment-count equality above and
    # verify clipped + rebuilt together account for every source table.
    clipped = [t for t in inv["tables"] if f"{{table{t['n']}.png}}" in tex]
    need_rebuilt = nt_src - len(clipped)
    have_rebuilt = nt_tex - len(clipped)
    if have_rebuilt < need_rebuilt:
        missing.append(f"{need_rebuilt - have_rebuilt} non-clipped table(s) have "
                       f"no matching \\begin{{table}} (source {nt_src}, "
                       f"clipped {len(clipped)}, tex table-env {nt_tex})")

    if missing:
        print("COVERAGE MISSING:")
        for m in missing:
            print("  -", m)
        sys.exit(1)
    print(f"COVERAGE OK: {n_eq_src} equations, {len(inv['algorithms'])} algorithms, "
          f"{len(inv['theorems'])} theorem-like, {nf_src} figures, {nt_src} tables")



def _clip_rects(tex_path):
    """读 pdf_clip 落下的裁切清单：{page: [Rect]}。
    表格/图内部的列表项已由位图承载，不应再计入「待译散文单」，否则
    跨页大表（如 PCIe Table 2-5）会让 structure 假 FAIL、fidelity 假 SUSPECT。"""
    mf = os.path.join(os.path.dirname(os.path.abspath(tex_path)), "fig",
                      "_clip_manifest.json")
    out = {}
    if not os.path.exists(mf):
        return out
    try:
        for e in json.load(open(mf, encoding="utf-8")):
            r = e["rect"]
            out.setdefault(e["page"], []).append(
                pymupdf.Rect(r[0], r[1], r[2], r[3]))
    except Exception:
        return {}
    return out


def _in_clip(rects, r):
    # 不用 Rect.area/get_area（不同 PyMuPDF 版本 API 不一致），直接手算交集。
    area = max(0.0, r.x1 - r.x0) * max(0.0, r.y1 - r.y0)
    if not area:
        return False
    for b in rects:
        ix = min(b.x1, r.x1) - max(b.x0, r.x0)
        iy = min(b.y1, r.y1) - max(b.y0, r.y0)
        if ix > 0 and iy > 0 and (ix * iy) / area > 0.6:
            return True
    return False


BULLET_CHARS = "•◦▪■○‣⁃"


def _spec_src_units(doc, start, end, tex_path=None):
    """spec 类源侧内容单元：列表项（不论长短）+ 散文块。
    论文口径只数 len>=60 的块，会把短列表项漏掉；spec 文档主体就是列表。
    图带内的块（多行图例、图内说明文字）一律不计：它们在位图里，译稿没有
    对应项，计入会造成假 FAIL。"""
    units = 0
    clip = _clip_rects(tex_path) if tex_path else {}
    for pno in range(start, end + 1):
        page = doc[pno - 1]
        pw, ph = page.rect.width, page.rect.height
        rects = clip.get(pno, [])
        blocks = []
        for b in page.get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            ls = ["".join(sp["text"] for sp in ln["spans"]).strip() for ln in b["lines"]]
            txt = "\n".join(t for t in ls if t).strip()
            if txt:
                blocks.append((pymupdf.Rect(b["bbox"]), ls, txt))
        prose = [r for r, _, t in blocks
                 if len(t) >= 60 and r.width >= 0.30 * pw]
        # § 是超链接残留符，既可能在行首也可能在编号前，匹配前整行剔除
        caps = [r for r, ls, _ in blocks
                if re.match(r"^(Figure|Table)\s+\d+", ls[0].replace("§", "").strip())]
        draws = [pymupdf.Rect(d["rect"]) for d in page.get_drawings()
                 if d["rect"].width > 2 and d["rect"].height > 2]
        bands = []
        for cr in caps:
            # 上界优先用「本图自己」的矢量框顶边：图例文字本身也是「散文」，
            # 若用「上方最近散文」当上界会被图例自己顶到图例下方，漏排除。
            # 矢量框必须限制在上一张题注之后，否则上一张图的框会把本图上界
            # 拉到上一张图那里，误删两图之间的正文。
            prev = max([c.y1 for c in caps if c.y1 < cr.y0 - 1] + [40.0])
            fig = [r.y0 for r in draws if prev < r.y0 and r.y1 <= cr.y0 + 2]
            above = [r.y1 for r in prose if r.y1 < cr.y0 - 4]
            top = min(fig) if fig else (max(above) if above else 40.0)
            top = max(top, max([r.y1 for r in prose if r.y1 < top] or [40.0]))
            bands.append((top, cr.y0))
        for r, ls, txt in blocks:
            l0 = ls[0].replace("§", "").strip()
            if r.y0 < 72 or r.y0 > ph - 45:
                continue
            if _in_clip(rects, r):
                continue                      # 已由裁切位图承载（表体/图内）
            if re.match(r"^(Figure|Table)\s+\d+", l0):
                continue
            # 本类文档的 bullet 符号常是独立文本块（"•" 一块、正文一块），
            # 若也计数会把每个列表项算两次，源侧单元数虚高。
            if len(l0) <= 2 and l0[:1] in BULLET_CHARS:
                continue
            if any(top <= r.y0 and r.y1 <= bot + 2 for top, bot in bands):
                continue                      # 图带内：图例/图内文字
            if re.match(r"^\d+(?:\.\d+)*\.?\s+[A-Z]", l0) and r.width < 0.5 * pw:
                continue                      # 章节标题
            if re.match(r"^\d+\.\s", l0):
                continue                      # 脚注定义
            if l0[:1] in BULLET_CHARS or len(txt) >= 40:
                units += 1
    return units


def _spec_tex_units(tex_path):
    """spec 类译稿侧内容单元：\\item 数 + 非列表的逻辑段数。
    论文口径按「单行 CJK>40」计段，译稿硬换行到 ~60 字符时会严重低估。"""
    skip = ("\\includegraphics", "\\caption", "\\label", "\\begin", "\\end")
    env_skip = ("figure", "table", "equation", "center", "tabular",
                "thebibliography", "abstract")
    items = paras = 0
    buf, stack, in_item = [], [], False

    def cjk(t):
        return len(re.findall(r"[\u4e00-\u9fff]", t))

    def flush():
        nonlocal buf, paras, in_item
        t = " ".join(buf)
        buf = []
        if not in_item and cjk(t) >= 20:
            paras += 1
        in_item = False

    for ln in open(tex_path, encoding="utf-8"):
        s = ln.strip()
        m = re.match(r"\\begin\{(\w+\*?)\}", s)
        if m:
            flush()
            stack.append(m.group(1).rstrip("*"))
            continue
        if s.startswith("\\end{"):
            flush()
            if stack:
                stack.pop()
            continue
        if stack and stack[-1] in env_skip:
            continue
        if re.match(r"\\item\b", s):
            flush()
            items += 1
            in_item = True
            buf = [s[5:]]
            continue
        if not s:
            flush()
            continue
        if s.startswith(skip) or s.startswith("\\"):
            continue
        buf.append(s)
    flush()
    return items + paras, items, paras


def structure(pdf, start, end, tex_path):
    """Paragraph-fidelity guard: a translation that silently merges or drops
    source paragraphs reads fluently but loses content - exactly the failure a
    coverage check on formulas/figures cannot see. Count prose blocks per
    section in the source PDF and CJK paragraphs per section in the tex."""
    doc = pymupdf.open(pdf)
    src, cur, done = {}, "1", False
    for pno in range(start, end + 1):
        if done:
            break
        page = doc[pno - 1]
        pw, ph = page.rect.width, page.rect.height
        for b in page.get_text("dict")["blocks"]:
            if done or b.get("type") != 0:
                continue
            ls = ["".join(sp["text"] for sp in ln["spans"]).strip() for ln in b["lines"]]
            txt = "\n".join(t for t in ls if t).strip()
            if not txt:
                continue
            r = pymupdf.Rect(b["bbox"])
            if r.y0 < 72 or r.y0 > ph - 45:
                continue
            if re.match(r"^(Figure|Table)\s+\d+:", txt):
                continue
            if len(re.findall(r"\([\d,.]+%\)", txt)) >= 2:
                continue                       # table row, not prose
            if ls[0] in ("References", "REFERENCES"):
                done = True
            if (len(ls) >= 2 and re.fullmatch(r"\d+(?:\.\d+)*", ls[0])
                    and re.match(r"^[A-Z][A-Za-z \-]{3,}$", ls[1]) and r.width < 0.5 * pw):
                cur = ls[0]
                src.setdefault(cur, 0)
                continue
            nl = txt.count("\n") + 1
            if len(txt) >= 60 and r.width >= 0.30 * pw and len(txt) / nl >= 40:
                src[cur] = src.get(cur, 0) + 1

    skip = ("\\includegraphics", "\\caption", "\\label", "\\begin", "\\end")
    texsec, cur, stack = {}, "front", []
    for ln in open(tex_path, encoding="utf-8"):
        s2 = ln.strip()
        m = re.match(r"\\begin\{(\w+\*?)\}", s2)
        if m:
            stack.append(m.group(1).rstrip("*"))
            continue
        if s2.startswith("\\end{"):
            if stack:
                stack.pop()
            continue
        m = re.match(r"\\(section|subsection|subsubsection)\*?\{(.+?)\}", s2)
        if m:
            cur = m.group(2)
            texsec.setdefault(cur, 0)
            rest = s2[m.end():]          # heading lines may carry body text
            if len(re.findall(r"[\u4e00-\u9fff]", rest)) > 40:
                texsec[cur] += 1
            continue
        if stack and stack[-1] in ("figure", "table", "equation", "center", "tabular",
                                   "thebibliography", "abstract"):
            continue
        cjk = len(re.findall(r"[\u4e00-\u9fff]", s2))
        if cjk > 40 and not s2.startswith(skip):
            texsec[cur] = texsec.get(cur, 0) + 1

    if doc_class.detect(pdf, start, end) == "spec":
        # spec 口径：列表项 + 逻辑段；论文口径（上面的逐行计数）保持不变。
        s_units = _spec_src_units(doc, start, end, tex_path)
        t_units, n_items, n_paras = _spec_tex_units(tex_path)
        print(f"[spec metric] source units {s_units}; tex units {t_units} "
              f"(\\item {n_items} + paragraphs {n_paras})")
        return _structure_report({"spec": s_units}, tex_path, {"spec": t_units})
    return _structure_report(src, tex_path, texsec)


def _structure_report(src, tex_path, texsec=None):
    if texsec is None:
        texsec = {}
    ts, tt = sum(src.values()), sum(texsec.values())
    print(f"source prose blocks: {ts}   tex paragraphs: {tt}")
    print("  src per section:", json.dumps(src, ensure_ascii=False))
    print("  tex per section:", json.dumps(texsec, ensure_ascii=False))
    if tt < 0.9 * ts:
        print(f"STRUCTURE FAIL: tex paragraphs {tt} < 90% of source prose blocks {ts}; "
              "sections were collapsed - re-translate them paragraph-by-paragraph")
        sys.exit(1)
    print("STRUCTURE OK (tex paragraph count within 90% of source prose blocks)")


def fidelity(pdf, start, end, tex_path, min_tok=2, ratio=0.7):
    """Content-fidelity guard. Paragraph counts can match while content is
    merged or dropped, so fingerprint every source prose block by its numeric
    tokens (percentages, factors, latencies, sizes...) and require most of them
    to reappear in the translation. Citation brackets ([22]) and 4-digit years
    are excluded: they become \\cite{rN} or vanish by design."""
    tex = open(tex_path, encoding="utf-8").read()
    tex_nums = set(re.findall(r"\d+(?:\.\d+)?", tex.replace("\\%", "%")))
    doc = pymupdf.open(pdf)
    clip = _clip_rects(tex_path)
    suspects = []
    checked = 0
    for pno in range(start, end + 1):
        page = doc[pno - 1]
        pw, ph = page.rect.width, page.rect.height
        # clipped tables leak their cell text as ordinary blocks; those numbers
        # live in the image, not the tex, so excluding table regions prevents
        # spec-heavy tables (e.g. DPU-vs-CPU comparisons with DDR/PCIe/× tokens)
        # from being mistaken for dropped prose. find_tables is best-effort.
        try:
            tboxes = [t.bbox for t in page.find_tables().tables]
        except Exception:
            tboxes = []
        # ACM convention: a figure's body sits ABOVE its caption, a table's body
        # BELOW its caption. find_tables misses borderless (booktabs) tables and
        # never covers figure-internal text, so also collect caption rects and
        # drop blocks in that band - their numbers live in the clipped image.
        caps = []
        for b in page.get_text("dict")["blocks"]:
            if b.get("type") != 0 or not b["lines"]:
                continue
            first = "".join(sp["text"] for sp in b["lines"][0]["spans"]).strip()
            cm = re.match(r"^(Figure|Table)\s+\d+:", first)
            if cm:
                caps.append((cm.group(1), pymupdf.Rect(b["bbox"])))
            else:
                # IEEE/类 IEEE 题注：同样排除图/表带内的数字（它们在位图里）。
                nl = len(b["lines"])
                if (doc_class.IEEE_FIG_LABEL_RE.fullmatch(first)
                        or (nl == 1 and doc_class.IEEE_FIG_ONELINE_RE.match(first))):
                    caps.append(("Figure", pymupdf.Rect(b["bbox"])))
                elif doc_class.IEEE_TAB_RE.fullmatch(first):
                    caps.append(("Table", pymupdf.Rect(b["bbox"])))

        def in_asset_band(cx, cy):
            for kind, cr in caps:
                if not (cr.x0 - 10 <= cx <= cr.x1 + 10):
                    continue
                if kind == "Figure" and cr.y0 - 200 <= cy <= cr.y0:
                    return True
                if kind == "Table" and cr.y1 <= cy <= cr.y1 + 200:
                    return True
            return False
        for b in page.get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            ls = ["".join(sp["text"] for sp in ln["spans"]).strip() for ln in b["lines"]]
            txt = " ".join(t for t in ls if t).strip()
            if not txt:
                continue
            r = pymupdf.Rect(b["bbox"])
            if r.y0 < 72 or r.y0 > ph - 45:
                continue
            if _in_clip(clip.get(pno, []), r):
                continue                       # 已由裁切位图承载（跨页大表等）
            cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
            if any(x0 <= cx <= x1 and y0 <= cy <= y1 for x0, y0, x1, y1 in tboxes):
                continue                       # inside a clipped table body
            if in_asset_band(cx, cy):
                continue                       # inside a clipped figure/table body
            if ls[0] in ("References", "REFERENCES"):
                return _fidelity_report(suspects, checked)
            if re.match(r"^(Figure|Table)\s+\d+:", txt):
                continue
            if txt.startswith(("This work is licensed", "ACM Reference Format",
                               "Permission to make", "©")):
                continue                       # front matter, never translated
            if "ACM, New York" in txt or re.match(r"^\d{4}, (Denver|New York)", txt):
                continue                       # reference-format continuation block
            if len(re.findall(r"\([\d,.]+%\)", txt)) >= 2:
                continue                       # table row, not prose
            # A clipped table leaks its cell text as a narrow, percentage-dense
            # block (e.g. Table 7's root-cause breakdown): those numbers live in
            # the image, not the tex, so skip such table bodies. A full-column
            # results paragraph (wide, low pct density) is still fingerprinted.
            _pct = len(re.findall(r"\d+(?:\.\d+)?%", txt))
            if _pct >= 3 and _pct >= 0.10 * max(1, len(txt.split())) \
                    and r.width < 0.55 * pw:
                continue                       # table body, not prose
            nl = txt.count("\n") + 1
            if not (len(txt) >= 60 and r.width >= 0.30 * pw and len(txt) / nl >= 40):
                continue
            clean = re.sub(r"^\d+(?:\.\d+)*\.?\s*", " ", txt)  # drop section numbers
            clean = re.sub(r"[§]\s*\d+(?:\.\d+)*", " ", clean)   # drop §-cross-refs
            clean = re.sub(r"\[\d+(?:[,\-\u2013 ]+\d+)*\]", " ", clean)  # drop citation nums
            toks = [t for t in re.findall(r"\d+(?:\.\d+)?", clean)
                    if not re.fullmatch(r"(19|20)\d\d", t)]
            if len(toks) < min_tok:
                continue
            checked += 1
            hit = [t for t in toks if t in tex_nums]
            if len(hit) / len(toks) < ratio:
                miss = [t for t in toks if t not in tex_nums]
                suspects.append((pno, txt[:70], miss[:8]))
    return _fidelity_report(suspects, checked)


def _fidelity_report(suspects, checked):
    print(f"fidelity: checked {checked} numeric-bearing prose blocks")
    if suspects:
        print("SUSPECT blocks (numeric fingerprints missing in translation):")
        for pno, head, miss in suspects:
            print(f"  p{pno} missing={miss} :: {head}")
        sys.exit(1)
    print("FIDELITY OK: every numeric-bearing source paragraph is represented")


# ---------------------------------------------------------------- spec 门禁
# 以下三个门禁只对 spec 类有意义（交叉引用/连续脚注/字面编号标题都是规范文档
# 的约定）；paper 类调用时直接 skip，保证两类互不影响。

XREF_RE = re.compile(r"\b(Section|Chapter|Figure|Table)\s+\d+(?:\.\d+)*\b")


def xrefs(tex_path, cls="spec"):
    """译稿残留交叉引用门禁：§ 符号与英文 Section/Chapter/Figure N 都说明
    该处没译成「第 N 节 / 图 N」。\caption 行与注释行除外。"""
    if cls != "spec":
        print("xrefs gate is spec-only; skipped for paper class")
        return
    bad = []
    for i, ln in enumerate(open(tex_path, encoding="utf-8"), 1):
        s = ln.strip()
        if not s or s.startswith("%") or "\\caption" in s or "\\includegraphics" in s:
            continue
        if "§" in s or XREF_RE.search(s):
            bad.append((i, s[:80]))
    if bad:
        print("XREFS SUSPECT (untranslated cross-references):")
        for i, s in bad:
            print(f"  L{i}: {s}")
        sys.exit(1)
    print("XREFS OK: no leftover § / English Section|Chapter|Figure|Table refs")


def footnotes(pdf, start, end, tex_path):
    """脚注门禁：源页脚注定义行数 == 译稿 \\footnote 数，且 \\setcounter 钉回的
    编号必须落在源脚注编号集合内（规范脚注全文连续，不按章重置）。"""
    if doc_class.detect(pdf, start, end) != "spec":
        print("footnotes gate is spec-only; skipped for paper class")
        return
    doc = pymupdf.open(pdf)
    src_nums = []
    for pno in range(start, end + 1):
        # 逐行扫描而不是只看块首行：多条脚注常合并在同一文本块里，
        # 只看首行会漏掉第二条及以后的脚注。
        for _, t in doc_class.block_lines(doc[pno - 1]):
            t = t.replace("§", "").strip()
            m = re.match(r"^(\d+)\.\s+[A-Z(]", t)
            if m and len(t) >= 40:
                src_nums.append(int(m.group(1)))
    src_nums = sorted(set(src_nums))
    tex = open(tex_path, encoding="utf-8").read()
    # 两种写法都算一个脚注：正文里的 \footnote{...}，以及表格内不能用
    # \footnote 时改用 \footnotemark[n] + 表后 \footnotetext[n]{...}。
    n_auto = len(re.findall(r"\\footnote\{", tex))
    ext = [int(x) for x in re.findall(r"\\footnotetext\[(\d+)\]\{", tex)]
    n_tex = n_auto + len(ext)
    counters = [int(x) + 1 for x in re.findall(r"\\setcounter\{footnote\}\{(\d+)\}", tex)] + ext
    ok = True
    if n_tex != len(src_nums):
        ok = False
        print(f"MISMATCH footnotes: source defs {src_nums}, tex \\footnote {n_tex}")
    stray = [c for c in counters if c not in src_nums]
    if stray:
        ok = False
        print(f"MISMATCH footnote numbering: \\setcounter pins {stray} not in source {src_nums}")
    if not ok:
        sys.exit(1)
    print(f"FOOTNOTES OK: {len(src_nums)} defs, numbers {src_nums}")


def sections(pdf, start, end, tex_path):
    """节级门禁：源标题树编号集合必须全部出现在译稿标题宏里，防整节漏译。
    译稿多出源没有的编号只报 WARN（可能是译者加的前言/附录标题）。"""
    if doc_class.detect(pdf, start, end) != "spec":
        print("sections gate is spec-only; skipped for paper class")
        return
    import pdf_outline
    src = {it["num"] for it in pdf_outline.outline(pdf, start, end)}
    tex = open(tex_path, encoding="utf-8").read()
    # 只扫正文：导言区的 \newcommand{\hdD}[1]{\paragraph{...#1}} 会被误读成编号 1
    tex = tex.split("\\begin{document}")[-1]
    got = set(re.findall(
        r"\\(?:hd[A-E]|(?:sub)*section\*?|paragraph|subparagraph)\s*"
        r"(?:\[[^\]]*\])?\s*\{[^{}0-9]*(\d+(?:\.\d+)*)", tex))
    missing = sorted(src - got, key=lambda s: [int(x) for x in s.split(".")])
    extra = sorted(got - src, key=lambda s: [int(x) for x in s.split(".")])
    if missing:
        print(f"SECTIONS MISSING ({len(missing)}): {missing}")
        sys.exit(1)
    if extra:
        print(f"WARN sections extra in tex (not in source outline): {extra}")
    print(f"SECTIONS OK: all {len(src)} source headings present in tex")

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "sheet":
        cw, chh = 470, 360
        if "--cell" in sys.argv:
            cw, chh = (int(v) for v in sys.argv[sys.argv.index("--cell") + 1].split("x"))
        cols = 3
        if "--cols" in sys.argv:
            cols = int(sys.argv[sys.argv.index("--cols") + 1])
        sheet(sys.argv[2], sys.argv[3], cols, cw, chh)
    elif cmd == "numbers":
        numbers(sys.argv[2], sys.argv[3])
    elif cmd == "coverage":
        coverage(sys.argv[2], sys.argv[3])
    elif cmd == "structure":
        structure(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
    elif cmd == "fidelity":
        fidelity(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
    elif cmd == "xrefs":
        xrefs(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "spec")
    elif cmd == "footnotes":
        footnotes(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
    elif cmd == "sections":
        sections(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
    else:
        print(__doc__)
        sys.exit(2)
