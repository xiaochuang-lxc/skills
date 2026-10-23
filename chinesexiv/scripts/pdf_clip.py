#!/usr/bin/env python3
"""Structure-aware figure/table clipper for two-column proceedings PDFs.

Usage:
  pdf_clip.py PDF START END OUTDIR [--zoom 3]

For every "Figure N:" / "Table N:" caption in pages START..END (1-based,
inclusive) it renders the figure body to OUTDIR/figureN.png / tableN.png.

Why it is built this way (each rule fixes an observed failure; see
references/pdf-pipeline.md for the full failure table):
  * captions are matched per LINE, not per block - subfigure captions arrive as
    "(a) ...\\n(b) ...\\nFigure N: ..." inside one text block;
  * the regex requires the colon, otherwise body cross-references such as
    "Figure 10 illustrates ..." are mistaken for captions;
  * running heads (y<72) and folios (y>page_h-45, digits-only blocks) are page
    furniture and are excluded from every candidate set;
  * a figure's vertical band ends at the nearest prose block / caption / table
    body ABOVE it, while an ACM table's band runs BELOW its caption and stops at
    the first >10pt gap or the first solid (drawing/image) box;
  * side-by-side captions (shared baseline) split the page at the widest REAL
    gap of the merged occupied intervals between them, not at their midpoint;
  * membership is by box centre, and boxes wider than 0.70 of the page width
    belong to full-width windows only - otherwise a neighbour's frame or a
    full-width rule bleeds into the crop;
  * plot frames are zero-height/zero-width paths; PyMuPDF treats such rects as
    EMPTY and silently drops them from `|` unions, so they are inflated by
    0.6pt before unioning (but kept out of gap detection);
  * tick labels and rotated axis titles are TEXT, so non-paragraph text blocks
    join the union or the y-axis is clipped away.

Lines starting with "!!" on stdout mark captions that could not be clipped and
need a manual rect (see references/pdf-pipeline.md, "Manual overrides").
"""
import argparse
import os
import re

import pymupdf

import doc_class

# 论文类（ACM/USENIX）题注："Figure 12: Title"。历史正则，论文路径保持不变。
CAP_RE = re.compile(r"^(Figure|Table)\s+(\d+):")
# 协议/标准类题注："Figure 7-132  Title"（无冒号、编号带章节前缀）。
# 仅在 doc_class 判定为 spec 时启用，且要求编号后接大写/数字/括号开头的
# 标题，以排除正文交叉引用（"Figure 1-2 shows ..." 是小写动词开头）。
CAP_PREFIX_RE = re.compile(r"^(Figure|Table)\s+(\d+-\d+)\s+(?=[A-Z0-9(])")
MIN_PARA_CHARS = 60        # axis labels are short; paragraphs are long
MIN_PARA_WIDTH_RATIO = 0.30  # two-column prose is ~0.41*page width
MIN_PARA_LINE_CHARS = 40   # sub-label rows like "(a) X  (b) Y" are wide but ragged
PAGE_PAD = 6


CLIPPED = []          # (page, key, rect) —— 供 pdf_audit 扣除位图已承载的内容


class _IEEEMatch:
    """Shim match for IEEE captions: group(1) in {Figure,Table}, group(2)=num."""
    def __init__(self, kind, num):
        self._k, self._n = kind, str(num)

    def group(self, i):
        return self._k if i == 1 else self._n


def _ieee_match(tt, i, nlines):
    """IEEE 题注识别（仅 ieee 风格启用）。两行式标签独立成行用 fullmatch；
    单行式仅当整块只有一行；表题为全大写罗马数字。正文交叉引用因同行带
    小写动词或多行而不命中。"""
    m = doc_class.IEEE_FIG_LABEL_RE.fullmatch(tt)
    if m:
        return _IEEEMatch("Figure", m.group(1))
    if i == 0 and nlines == 1:
        m = doc_class.IEEE_FIG_ONELINE_RE.match(tt)
        if m:
            return _IEEEMatch("Figure", m.group(1))
    m = doc_class.IEEE_TAB_RE.fullmatch(tt)
    if m:
        n = doc_class.roman2int(m.group(1))
        if n:
            return _IEEEMatch("Table", n)
    return None


def text_blocks(page, allow_prefix=False, ieee=False):
    """Return (blocks, captions); see module docstring for the per-line rule.

    allow_prefix 只在 spec 类文档打开：论文类保持仅冒号匹配的历史行为。
    ieee 只在 caption_style=='ieee' 打开：识别 Fig. N. / TABLE 罗马 题注。"""
    blocks, captions = [], []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        lines = b["lines"]
        texts = ["".join(s["text"] for s in ln["spans"]).strip() for ln in lines]
        hit = None
        for i, t in enumerate(texts):
            tt = t.replace("§", "").strip()   # 超链接残留符；剥掉后可能留前导空格
            m = CAP_RE.match(tt)
            if not m and allow_prefix:
                m = CAP_PREFIX_RE.match(tt)
            if not m and ieee:
                m = _ieee_match(tt, i, len(texts))
            if m:
                hit = (i, m)
                break
        if hit:
            i, m = hit
            bb = pymupdf.Rect(lines[i]["bbox"])
            for ln in lines[i + 1:]:
                bb |= pymupdf.Rect(ln["bbox"])
            captions.append((bb, m))
            continue
        joined = "\n".join(t for t in texts if t)
        if joined:
            blocks.append((pymupdf.Rect(b["bbox"]), joined))
    return blocks, captions


def visual_boxes(page):
    """Return (solid, thin); thin = inflated frame lines (see docstring)."""
    solid, thin = [], []
    for d in page.get_drawings():
        r = pymupdf.Rect(d["rect"])
        if r.width > 3 and r.height > 3:
            solid.append(r)
        elif r.width > 3 or r.height > 3:
            thin.append(pymupdf.Rect(r.x0 - 0.6, r.y0 - 0.6, r.x1 + 0.6, r.y1 + 0.6))
    for im in page.get_image_info():
        solid.append(pymupdf.Rect(im["bbox"]))
    return solid, thin


def clip_page(page, pno, out, zoom, allow_prefix=False, ieee=False):
    pw, ph = page.rect.width, page.rect.height
    # 页眉/页脚带宽度：ACM 论文页眉在 72pt 以上；而规范/标准类文档页眉只占 y<40，
    # 且表格/图常常顶到页顶（如 PCIe Table 2-9 题注在 y=55），用 72 会把它当页眉误杀。
    top_y = 40.0 if allow_prefix else 72.0
    blocks, captions = text_blocks(page, allow_prefix, ieee)
    boxes, thin = visual_boxes(page)
    # ieee：图体矢量框可能顶到 y<72（页顶图例/标签），文字块仍按 top_y 过滤页眉。
    vtop = 40.0 if ieee else top_y
    blocks = [(r, t) for r, t in blocks if top_y <= r.y0 <= ph - 45]
    boxes = [r for r in boxes if vtop <= r.y0 <= ph - 45]
    thin = [r for r in thin if vtop <= r.y0 <= ph - 45]
    captions = [(r, m) for r, m in captions if top_y <= r.y0 <= ph - 45]

    def is_prose(r, t):
        nl = t.count("\n") + 1
        return (len(t) >= MIN_PARA_CHARS
                and r.width >= MIN_PARA_WIDTH_RATIO * pw
                and len(t) / nl >= MIN_PARA_LINE_CHARS)

    paragraphs = [(r, t) for r, t in blocks if is_prose(r, t)]
    caption_rects = [r for r, _ in captions]
    para_rects = {id(r) for r, _ in paragraphs}

    def is_heading(t, size):
        # section/subsection headings ("4.1\nTraffic Measurement Module") are
        # neither prose nor captions; if left in the union a figure sitting
        # directly under a heading captures the heading text. Font size is the
        # discriminator: headings ~11pt, figure-internal numeric labels <=6pt,
        # folios ~9pt - a bare "first line is a number" test alone would eat
        # tree-node / axis labels and shred the figure.
        ls = [l.strip() for l in t.split("\n") if l.strip()]
        return (bool(ls) and re.fullmatch(r"\d+(?:\.\d+)*\.?", ls[0])
                and len(t) < 120 and size >= 10.0)

    _bsize = {}
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        szs = [sp["size"] for ln in b["lines"] for sp in ln["spans"] if sp["text"].strip()]
        _bsize[(round(b["bbox"][0], 1), round(b["bbox"][1], 1))] = max(szs) if szs else 0.0
    headings = [r for r, t in blocks
                if is_heading(t, _bsize.get((round(r.x0, 1), round(r.y0, 1)), 0.0))]
    head_rects = {id(r) for r in headings}
    label_rects = [r for r, t in blocks
                   if id(r) not in para_rects and id(r) not in head_rects
                   and not re.fullmatch(r"[\d\s]+", t)]
    region = boxes + thin + label_rects      # union: frames included
    region_cut = boxes + label_rects         # gap detection: frames excluded

    def rows_of(rects):
        left, rows = list(rects), []
        while left:
            anchor = min(left, key=lambda r: (r.y0, r.x0))
            row = [r for r in left
                   if abs(r.y0 - anchor.y0) < 12 and abs(r.y1 - anchor.y1) < 24]
            for r in row:
                left.remove(r)
            rows.append(sorted(row, key=lambda r: r.x0))
        return rows

    def merged_intervals(items):
        out = []
        for a, b in sorted([[r.x0, r.x1] for r in items]):
            if out and a <= out[-1][1] + 1:
                out[-1][1] = max(out[-1][1], b)
            else:
                out.append([a, b])
        return out

    def cut_between(a, b, items):
        ivs = merged_intervals(items)
        lo, hi = a.x1 - 10, b.x0 + 10
        best = None
        for i in range(len(ivs) - 1):
            gap = ivs[i + 1][0] - ivs[i][1]
            cut = (ivs[i][1] + ivs[i + 1][0]) / 2
            if gap > 2 and lo <= cut <= hi and (best is None or gap > best[0]):
                best = (gap, cut)
        return best[1] if best else (a.x1 + b.x0) / 2

    # ---- pass 1: horizontal window per caption -------------------------
    windows = {}
    for row in rows_of(caption_rects):
        above = [r.y1 for r in caption_rects if r.y1 < row[0].y0 - 1]
        floor = max(above) if above else 0.0
        bounds = None
        if len(row) > 1:
            scope = [r for r in region_cut if r.y0 >= floor and r.y1 <= row[0].y0 + 4]
            bounds = [0.0]
            for a, b in zip(row, row[1:]):
                bounds.append(cut_between(a, b, scope))
            bounds.append(pw)
        for idx, cr in enumerate(row):
            ccx = (cr.x0 + cr.x1) / 2
            if bounds:
                windows[id(cr)] = (bounds[idx], bounds[idx + 1])
            elif allow_prefix and len(row) == 1:
                # spec 单栏：一行只有一个题注时窗口就是整页宽；窄题注
                # 不能按中心 x 分半页，否则宽图会被「宽框只属整宽窗口」排除
                windows[id(cr)] = (0.0, pw)
            elif cr.width > 0.62 * pw or 0.4 * pw <= ccx <= 0.6 * pw:
                windows[id(cr)] = (0.0, pw)
            elif ccx < pw / 2:
                windows[id(cr)] = (0.0, pw / 2)
            else:
                windows[id(cr)] = (pw / 2, pw)
            # ieee：跨栏图（figure*）的题注文本窄且左对齐，按题注中心分栏会
            # 把图裁成单栏丢右半。若本带内矢量框同时落在左右两栏，则整页宽。
            if ieee and len(row) == 1 and not bounds:
                band = [v for v in boxes if v.y0 >= floor and v.y1 <= cr.y0 + 4]
                # 另一栏若在本带内有表题注，则该栏题注以下的框属于那张表
                # （另一资产），不能作为本图跨栏的证据（否则把邻栏表裁进本图）。
                tabcaps = [r for r, m in captions if m.group(1) == "Table"]
                ltab = [tc for tc in tabcaps
                        if (tc.x0 + tc.x1) / 2 < pw / 2 and tc.y1 >= floor - 2]
                rtab = [tc for tc in tabcaps
                        if (tc.x0 + tc.x1) / 2 >= pw / 2 and tc.y1 >= floor - 2]
                lf = [v for v in band if (v.x0 + v.x1) / 2 < pw / 2
                      and not any(tc.y0 <= v.y0 + 2 for tc in ltab)]
                rt = [v for v in band if (v.x0 + v.x1) / 2 > pw / 2
                      and not any(tc.y0 <= v.y0 + 2 for tc in rtab)]
                # 带内若还有别的图题注，同理不判跨栏。
                other = [r for r in caption_rects
                         if r is not cr and floor <= r.y0 <= cr.y0 + 4]
                if lf and rt and not other:
                    windows[id(cr)] = (0.0, pw)

    def table_stop(cand, cr, bottom):
        """表体下界。ACM：遇第一个 >10pt 空隙或第一个实心框即止；
        同时检测 prose 块（宽度≥0.30×页宽、平均行长≥40），防止表格
        与正文间无 solid box 且间隙<10pt 时 prose 被误纳入表体。
        spec：改为下一个正文段落顶边（脚注定义行属正文），否则打勾矩阵
        行间的空隙会把表提前切断。论文路径保持历史逻辑。"""
        if allow_prefix:
            # spec：从题注向下按「间隙连续性」聚簇定表体下界。用「下一个正文/题注」
            # 当硬边界不可靠：表下方紧跟图时，图框会与表体重叠，把图（及其题注）
            # 包进表体，还会抰高下一张图的带上界使其 degenerate。
            ys = sorted(((v.y0, v.y1) for v in cand if v.y0 >= cr.y1 - 2))
            if not ys:
                return bottom
            cur = ys[0][1]
            for y0, y1 in ys[1:]:
                if y0 - cur > 12:
                    break
                cur = max(cur, y1)
            return cur
        solids = {id(v) for v in boxes}
        ys = sorted(((v.y0, v.y1, id(v) in solids) for v in cand))
        stop = ys[0][1]
        _seen_table_content = False
        for a, b, is_solid in ys[1:]:
            # prose 检测：宽度≥0.30×页宽 且 平均行长≥40 → 正文段落
            # 若已积累一定表内容后遇到 prose，说明表已结束
            if _seen_table_content and a - stop <= 10:
                blk_w = None
                for v in cand:
                    if abs(v.y0 - a) < 2:
                        blk_w = v.width
                        break
                if blk_w is not None and blk_w >= 0.30 * pw:
                    # 进一步确认是 prose：检查该块是否为段落
                    for r, t in paragraphs:
                        if abs(r.y0 - a) < 2 and len(t) / max(1, t.count("\n") + 1) >= 40:
                            break  # 确认为 prose，停止扩展
                    else:
                        # 不是 prose，继续扩展
                        if is_solid or a - stop > 10:
                            break
                        stop = max(stop, b)
                        continue
                    break  # prose 确认，停止
            if is_solid or a - stop > 10:
                break
            stop = max(stop, b)
            _seen_table_content = True
        return stop

    # ---- pass 2: table bodies (ACM puts the caption above the body) ----
    table_bodies = []
    for cr, mt in captions:
        if mt.group(1) != "Table":
            continue
        hx0, hx1 = windows[id(cr)]
        cand = [v for v in region + label_rects + [r for r, _ in paragraphs] + [cr]
                if v.y0 >= cr.y0 - 2 and hx0 <= (v.x0 + v.x1) / 2 <= hx1]
        if not cand:
            continue
        stop = table_stop(cand, cr, ph - 45.0)
        u = pymupdf.Rect(cand[0])
        for v in cand:
            if v.y1 <= stop + 2:
                u |= v
        # 表体矩形包含题注：用 cr.y0 而非 cr.y1，确保下游 figure 定位
        # 时不会与表题注重叠。
        table_bodies.append(pymupdf.Rect(u.x0, cr.y0, u.x1, stop))

    # ---- pass 3: crop ---------------------------------------------------
    clipped_bodies = []
    for row in rows_of(caption_rects):
        for cr in row:
            mt = next(m for r, m in captions if r is cr)
            kind, num = mt.group(1), mt.group(2)
            hx0, hx1 = windows[id(cr)]

            if kind == "Table":
                # ieee：表格交给手工位图/重建（见 references），自动裁切仅用于
                # 给下方图提供带上界，不产出 tableN.png，避免不可靠的表位图。
                if ieee:
                    continue
                # spec 类：表以位图交付且无独立 \caption，裁切必须包含题注
                # （top 用 cr.y0、cr 入候选集），否则题注被裁切框底边切断。
                # paper 类：表题由 LaTeX \caption（中文）提供，图片内再带英文
                # 题注会重复，故排除题注（top 用 cr.y1、cr 不入候选集）。
                if allow_prefix:
                    top, bottom = cr.y0, ph - 45.0
                    extra = [cr]
                else:
                    top, bottom = cr.y1, ph - 45.0
                    extra = []
                cand = [v for v in region + label_rects + [r for r, _ in paragraphs] + extra
                        if v.y0 >= top - 2 and v.y1 <= bottom + 2
                        and hx0 <= (v.x0 + v.x1) / 2 <= hx1]
                if cand:
                    stop = table_stop(cand, cr, bottom)
                    cand = [v for v in cand if v.y1 <= stop + 2]
                # paper 类二次防护：扫描候选块中是否有 caption-like 文本
                # （匹配 CAP_RE），若有则以其 y0 作为实际 crop 下界。
                # 场景：caption block bbox 因 PDF 解析原因延伸至表数据区下方，
                # 或 caption 实际位于表下方（非 ACM 惯例），导致 cr.y1 不可靠。
                if not allow_prefix:
                    for r, t in blocks:
                        tt = t.split("\n")[0].replace("§", "").strip()
                        if (CAP_RE.match(tt)
                                and r is not cr
                                and hx0 <= (r.x0 + r.x1) / 2 <= hx1
                                and r.y0 > cr.y1 - 2):
                            # 发现另一个 caption-like 块在候选区域内
                            bottom = min(bottom, r.y0 - 2)
                            # 同时收紧候选集
                            cand = [v for v in cand if v.y1 <= bottom + 2]
                            break
                if not cand:
                    print(f"!! {kind.lower()}{num} p{pno}: no box below caption "
                          f"[{top:.0f},{bottom:.0f}] x[{hx0:.0f},{hx1:.0f}]", flush=True)
                    continue
                u = pymupdf.Rect(cand[0])
                for v in cand[1:]:
                    u |= v
                crop = pymupdf.Rect(max(u.x0 - PAGE_PAD, 0), max(u.y0 - PAGE_PAD, top - PAGE_PAD),
                                    min(u.x1 + PAGE_PAD, pw), min(u.y1 + PAGE_PAD, bottom))
                if crop.width < 40 or crop.height < 12:
                    print(f"!! {kind.lower()}{num} p{pno}: degenerate {crop}", flush=True)
                    continue
            else:
                top = 0.0
                for r, _ in paragraphs:
                    if r.y1 <= cr.y0 + 1 and not (r.x1 < hx0 or r.x0 > hx1):
                        top = max(top, r.y1)
                for hr in headings:
                    if hr.y1 <= cr.y0 + 1 and not (hr.x1 < hx0 or hr.x0 > hx1):
                        top = max(top, hr.y1)
                for r, _ in captions:
                    if r is not cr and r.y1 <= cr.y0 + 1 and not (r.x1 < hx0 or r.x0 > hx1):
                        top = max(top, r.y1)
                for tb in table_bodies:
                    if tb.y1 <= cr.y0 + 1 and not (tb.x1 < hx0 or tb.x0 > hx1):
                        top = max(top, tb.y1)
                # ieee：同一栏/页上已裁的图体作为本图带上界，防止上一张图
                # 的残留渗进本图（带顶落到页顶时的串图）。
                if ieee:
                    for fb in clipped_bodies:
                        if fb.y1 <= cr.y0 + 1 and not (fb.x1 < hx0 or fb.x0 > hx1):
                            top = max(top, fb.y1)
                if allow_prefix:
                    # spec：图带上界用本图自己的矢量框顶边。不能直接取
                    # 「题注上方所有框的最小 y0」：标题下的装饰横线也在其中，
                    # 会把上界顶到横线处、把上一节标题与正文 bullet 一起带进来。
                    # 改为从紧贴题注的框向上聚簇，只并入间隙 <=12pt 的框。
                    prev = max([r.y1 for r, _ in captions if r.y1 < cr.y0 - 1] +
                               [tb.y1 for tb in table_bodies if tb.y1 < cr.y0 - 1] + [0.0])

                    def xok(v):
                        return not (v.x1 < hx0 or v.x0 > hx1)

                    above = [v for v in boxes + thin
                             if prev < v.y0 and v.y1 <= cr.y0 + 2 and xok(v)]
                    seed = [v for v in above if v.y1 >= cr.y0 - 45]
                    if seed:
                        cur = min(v.y0 for v in seed)
                        grown = True
                        while grown:
                            grown = False
                            for v in above:
                                if v.y0 < cur and v.y1 >= cur - 12:
                                    cur = v.y0
                                    grown = True
                        top = max(top, cur)

                def in_window(v):
                    if not (v.y0 >= top - 2 and v.y1 <= cr.y0 + 4):
                        return False
                    if v.width > 0.70 * pw:
                        return hx0 == 0.0 and hx1 == pw
                    return hx0 <= (v.x0 + v.x1) / 2 <= hx1

                cand = [v for v in region if in_window(v)]
                if not cand:
                    cand = [v for v in label_rects if in_window(v)]
                if not cand:
                    print(f"!! {kind.lower()}{num} p{pno}: no visual box in band "
                          f"[{top:.0f},{cr.y0:.0f}] x[{hx0:.0f},{hx1:.0f}]", flush=True)
                    continue
                u = pymupdf.Rect(cand[0])
                for v in cand[1:]:
                    u |= v
                if allow_prefix:
                    # 跨在图带上界的文字行（如位编号行 7 6 5 4 3 2 1 0）必须整行纳入，
                    # 否则顶边会把它切掉半截。
                    strad = [v for v in label_rects
                             if u.y0 - 15 <= v.y0 < u.y0 and v.y1 > u.y0 - 1
                             and hx0 <= (v.x0 + v.x1) / 2 <= hx1]
                    if strad:
                        u.y0 = min([v.y0 for v in strad] + [u.y0])
                crop = pymupdf.Rect(max(u.x0 - PAGE_PAD, 0),
                                    max(u.y0 - PAGE_PAD, top - (15 if allow_prefix else 0)),
                                    min(u.x1 + PAGE_PAD, pw), cr.y0 - 1.5)
                if crop.width < 40 or crop.height < 28:
                    print(f"!! {kind.lower()}{num} p{pno}: degenerate {crop}", flush=True)
                    continue
                clipped_bodies.append(pymupdf.Rect(crop))

            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=crop)
            key = f"{kind.lower()}{num}"
            pix.save(os.path.join(out, key + ".png"))
            CLIPPED.append({"page": pno, "key": key,
                            "rect": [round(crop.x0, 1), round(crop.y0, 1),
                                     round(crop.x1, 1), round(crop.y1, 1)]})
            # 打印实际裁切框（以前打的是水平窗口，spec 单栏下窗口=整页宽，
            # 会让人误以为裁切过松）
            print(f"{key} p{pno} {round(crop.width)}x{round(crop.height)} "
                  f"clip=({crop.x0:.0f},{crop.y0:.0f},{crop.x1:.0f},{crop.y1:.0f})",
                  flush=True)
    return len(captions)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pdf")
    ap.add_argument("start", type=int)
    ap.add_argument("end", type=int)
    ap.add_argument("outdir")
    ap.add_argument("--zoom", type=float, default=3.0)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    doc = pymupdf.open(a.pdf)
    allow_prefix = doc_class.detect(a.pdf, a.start, a.end) == "spec"
    ieee = (not allow_prefix) and \
        doc_class.caption_style(a.pdf, a.start, a.end) == "ieee"
    total = 0
    for pno in range(a.start, a.end + 1):
        total += clip_page(doc[pno - 1], pno, a.outdir, a.zoom, allow_prefix, ieee)
    if total == 0:
        # 静默空产出比报错更危险：fig/ 为空但管线会继续走到翻译。
        print(f"!! NO CAPTION MATCHED in pages {a.start}..{a.end}: fig/ is empty. "
              f"检查题注格式（无冒号？编号带章节前缀？题注在图下方还是上方？）",
              flush=True)
        raise SystemExit(2)
    print(f"done ({total} captions, class={'spec' if allow_prefix else 'paper'}, "
          f"style={'spec' if allow_prefix else ('ieee' if ieee else 'acm')})")
    # 落一份裁切清单：下游 structure/fidelity 需要知道哪些页区已由位图承载，
    # 否则表格/图内部的列表项会被当成「漏译的散文块」误报。
    import json
    mf = os.path.join(a.outdir, "_clip_manifest.json")
    old = []
    if os.path.exists(mf):
        try:
            old = json.load(open(mf, encoding="utf-8"))
        except Exception:
            old = []
    keys = {c["key"] for c in CLIPPED}
    json.dump(old + [c for c in CLIPPED], open(mf, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"manifest -> {mf} ({len(CLIPPED)} entries, {len(keys)} keys)")


if __name__ == "__main__":
    main()
