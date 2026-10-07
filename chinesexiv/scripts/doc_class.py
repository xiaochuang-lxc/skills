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


if __name__ == "__main__":
    import sys
    print(detect(sys.argv[1], int(sys.argv[2]), int(sys.argv[3])))
