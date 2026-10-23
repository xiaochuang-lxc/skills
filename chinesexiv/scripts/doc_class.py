#!/usr/bin/env python3
"""文档类别探测：paper（ACM/USENIX 双栏论文）vs spec（协议/标准/白皮书单栏）。

两类文档的版式约定完全不同，管线的题注正则、分栏策略、验收口径都必须按类别
分流；本模块给出唯一判据，供 pdf_clip / pdf_extract / pdf_audit / pdf_inventory
共用，避免各处各写一套导致行为漂移。

判据（两条独立证据，任一命中即 spec）：
  1. 单栏版式：正文块（len>=60）中宽度 >=0.70*页宽 的占比 >=0.70
     （ACM 双栏正文约 0.41*页宽，占比接近 0）；
  2. 章节前缀题注：存在 "Figure 7-132  Title" / "Table 6-4  Title" 形式的行
     （编号带 "<章>-" 前缀且无冒号），ACM 论文用 "Figure 12: Title"。

对论文类返回 "paper"，此时所有脚本必须保持历史行为不变（零回归承诺）。
"""
import re

import pymupdf

PREFIX_CAP_RE = re.compile(r"^(Figure|Table)\s+\d+-\d+\s+[A-Z0-9(]")
COLON_CAP_RE = re.compile(r"^(Figure|Table)\s+\d+:")
# IEEE/类 IEEE 论文题注（paper 类内部的第二种风格）：
#   图题标签独立成行 "Fig. 1."（两行式）；或单行块 "Fig. 11. Title..."（单行式）；
#   表题为全大写罗马数字 "TABLE I"。正文交叉引用（"Fig. 8 shows ..."）同行带
#   小写动词或多行，不会命中 fullmatch / 单行式规则。
IEEE_FIG_LABEL_RE = re.compile(r"Fig\.\s*(\d+)\.")
IEEE_FIG_ONELINE_RE = re.compile(r"Fig\.\s*(\d+)\.\s+[A-Z]")
IEEE_TAB_RE = re.compile(r"TABLE\s+([IVX]+)")
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
         "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12}


def roman2int(s):
    return ROMAN.get(s.strip().upper())


def block_lines(page):
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for ln in b["lines"]:
            t = "".join(s["text"] for s in ln["spans"]).strip()
            if t:
                yield pymupdf.Rect(ln["bbox"]), t


def detect(pdf, start, end, sample=24):
    """返回 'spec' 或 'paper'。只采样前 sample 页，成本可忽略。"""
    doc = pymupdf.open(pdf)
    last = min(end, start - 1 + sample)
    wide = tot = 0
    prefix = colon = 0
    for p in range(start - 1, last):
        page = doc[p]
        pw = page.rect.width
        for b in page.get_text("blocks"):
            if b[6] != 0 or len(b[4].strip()) < 60:
                continue
            tot += 1
            if b[2] - b[0] >= 0.70 * pw:
                wide += 1
        for _, t in block_lines(page):
            if PREFIX_CAP_RE.match(t):
                prefix += 1
            elif COLON_CAP_RE.match(t):
                colon += 1
    single = bool(tot) and wide / tot >= 0.70
    if prefix and prefix >= colon:
        return "spec"
    return "spec" if single else "paper"


def caption_style(pdf, start, end, sample=24):
    """paper 类内部的题注风格：'acm'（Figure N:）vs 'ieee'（Fig. N. / TABLE 罗马）。

    仅当**完全没有** ACM 冒号题注、且存在 IEEE 题注证据时才判 'ieee'，
    否则一律 'acm'——这是 paper 路径零回归承诺的开关：ACM 论文永远不会
    走进 ieee 分支。spec 类直接返回 'spec'（其题注走章节前缀口径）。
    """
    if detect(pdf, start, end, sample) == "spec":
        return "spec"
    doc = pymupdf.open(pdf)
    last = min(end, start - 1 + sample)
    colon = ieee = 0
    for p in range(start - 1, last):
        for _, t in block_lines(doc[p]):
            tt = t.replace("\u00a7", "").strip()
            if COLON_CAP_RE.match(tt):
                colon += 1
            elif IEEE_FIG_LABEL_RE.fullmatch(tt) or IEEE_TAB_RE.fullmatch(tt):
                ieee += 1
    return "ieee" if (ieee and not colon) else "acm"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 4 and sys.argv[4] == "style":
        print(caption_style(sys.argv[1], int(sys.argv[2]), int(sys.argv[3])))
    else:
        print(detect(sys.argv[1], int(sys.argv[2]), int(sys.argv[3])))
