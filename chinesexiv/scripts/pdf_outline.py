#!/usr/bin/env python3
"""提取协议/标准类文档的编号标题树（含页码），供译稿骨架对齐与节级门禁。

Usage:
  pdf_outline.py PDF START END [--json OUT]

为什么需要：spec 文档有五级编号标题（1 / 1.5 / 1.5.4 / 1.5.4.4 / 1.5.4.4.1），
译稿骨架靠人肉对齐时最容易整节漏译；structure 门禁只数内容单元数，数不出
「少了 1.5.4.4.2 这一节」。本脚本把源文档的标题树打出来，
`pdf_audit.py sections` 再拿它与译稿标题宏的编号集合逐层比对。

判定（与 _spec_src_units 的标题排除规则同源，避免两边口径漂移）：
  * 行首是 `N[.N]*` 编号 + 空格 + 大写开头的标题文字；
  * 该文本块宽度 < 0.5*页宽（正文段落是全宽或接近全宽）；
  * 排除页眉页脚带（y<40 / y>页高-45）与纯编号行。
论文类文档也能提取（ACM 标题同样是 "1 Introduction"），但 sections 门禁只在
spec 类启用——论文译稿用 \\section{标题} 不带字面编号，比对没有意义。
"""
import argparse
import json
import re

import pymupdf

# 标题允许下划线：规范文档的三级以下标题常带机器可读名（如 "Vendor_Defined Messages"、
# "Max_Payload_Size"），不加 _ 会漏检该节，导致 sections 门禁误报译稿多出编号。
HEAD_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+([A-Z][A-Za-z0-9_,/\-() ]{3,80})$")


def outline(pdf, start, end):
    doc = pymupdf.open(pdf)
    out = []
    for p in range(start - 1, end):
        page = doc[p]
        pw, ph = page.rect.width, page.rect.height
        sizes = [s["size"] for b in page.get_text("dict")["blocks"] if b.get("type") == 0
                 for ln in b["lines"] for s in ln["spans"] if s["text"].strip()]
        if not sizes:
            continue
        body = sorted(sizes)[len(sizes) // 2]
        for b in page.get_text("dict")["blocks"]:
            if b.get("type") != 0 or not b["lines"]:
                continue
            r0 = pymupdf.Rect(b["lines"][0]["bbox"])   # 用首行行宽，不是块宽：
            if r0.y0 < 40 or r0.y0 > ph - 45:
                continue            # 标题常与首段同块，块宽会是整页宽
            if r0.width >= 0.85 * pw:
                continue            # 正文首行几乎擑满栏宽，标题不会
            first = "".join(s["text"] for s in b["lines"][0]["spans"]).strip()
            # 字号判据：表格行「2.5 GT/s」之类也满足编号+大写形式，
            # 但它们是正文字号；标题必须比页面中位字号大。
            if b["lines"][0]["spans"][0]["size"] < body + 0.5:
                continue
            m = HEAD_RE.match(first.replace("§", "").strip())
            if not m:
                continue
            # 多行标题（如 "1.4 Hardware/Software Model for Discovery,\n Configuration"）
            title = m.group(2)
            for ln in b["lines"][1:]:
                t = "".join(s["text"] for s in ln["spans"]).strip()
                if t and not HEAD_RE.match(t):
                    title += " " + t
            out.append({"num": m.group(1), "page": p + 1,
                        "title": re.sub(r"\s+", " ", title).strip()})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pdf")
    ap.add_argument("start", type=int)
    ap.add_argument("end", type=int)
    ap.add_argument("--json")
    a = ap.parse_args()
    items = outline(a.pdf, a.start, a.end)
    if a.json:
        json.dump(items, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"wrote {a.json} ({len(items)} headings)")
    for it in items:
        depth = it["num"].count(".")
        print(f"{'  ' * depth}{it['num']:<12} p{it['page']:<5} {it['title']}")


if __name__ == "__main__":
    main()
