#!/usr/bin/env python3
"""Column-aware text extractor for two-column proceedings pages.

Usage:
  pdf_extract.py PDF START END [OUT_FILE]

PyMuPDF's get_text(sort=True) interleaves the two columns and this proceedings
family also corrupts ligatures (fi -> Ï, ff -> Ò). This script classifies every
text block as full-width / left / right by its centre x, sorts each group by y0
and repairs the ligatures, emitting reading-order text with page and column
markers.
"""
import sys

import pymupdf

import doc_class

pdf, start, end = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
out = sys.argv[4] if len(sys.argv) > 4 else None

doc = pymupdf.open(pdf)
page_w = doc[start - 1].rect.width
mid = page_w / 2.0


def fix(s):
    return (s.replace("Ï", "fi").replace("Ò", "ff").replace("ﬁ", "fi")
            .replace("ﬂ", "fl").replace("­", "").replace("ÿ", "y"))


# 单栏文档（协议/标准/白皮书，以及部分单栏预印本）不能按中心 x 分栏：
# 子项目符号块宽度常落在 (0.30, 0.62)*页宽，会被误分到 left/right 组各自
# 排序，阅读序打乱（条目跳到段首）。判据统一在 doc_class，双栏论文返回
# "paper" 时下面走历史路径，行为不变。
SINGLE = doc_class.detect(pdf, start, end) == "spec"
if SINGLE:
    print("single-column layout detected; using natural reading order", file=sys.stderr)

lines = []
for p in range(start, end + 1):
    page = doc[p - 1]
    blocks = [b for b in page.get_text("blocks") if b[6] == 0 and b[4].strip()]
    lines.append(f"\n========== [PAGE {p}] ==========")
    if SINGLE:
        for b in sorted(blocks, key=lambda b: (round(b[1], 1), b[0])):
            lines.append(fix(b[4]).rstrip())
        continue
    left, right, full = [], [], []
    for b in blocks:
        x0, y0, x1, txt = b[0], b[1], b[2], b[4]
        cx, w = (x0 + x1) / 2, x1 - x0
        if w > page_w * 0.62:
            full.append((y0, txt))
        elif cx < mid:
            left.append((y0, txt))
        else:
            right.append((y0, txt))
    for grp, name in ((sorted(full), None), (sorted(left), "LEFT COLUMN"),
                      (sorted(right), "RIGHT COLUMN")):
        if name:
            lines.append(f"---- {name} ----")
        for _, t in grp:
            lines.append(fix(t).rstrip())

text = "\n".join(lines) + "\n"
if out:
    open(out, "w", encoding="utf-8").write(text)
    print(f"wrote {out} ({len(lines)} lines)")
else:
    sys.stdout.write(text)
