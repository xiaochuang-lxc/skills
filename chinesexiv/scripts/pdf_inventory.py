#!/usr/bin/env python3
"""Inventory the numbered math/algorithm/theorem/figure assets of a paper.

Usage:
  pdf_inventory.py TEXT_FILE [--out FILE]

PDF-extracted text scrambles displayed equations into glyph soup, so a
translator working from it silently drops formulas. This script builds the
checklist that prevents that: every numbered equation, algorithm, theorem-like
block and figure/table, with its page and the raw fragment lines around it (the
fragment is what the translator reconstructs into LaTeX).

Detection rules (all line-anchored, tuned on ACM two-column extracts):
  equation number : a line that is exactly "(n)"
  algorithm       : "Algorithm n Title"
  theorem-like    : "Theorem/Lemma/Definition/Corollary/Proposition n[.m]"
  figure/table    : "Figure n:" / "Table n:"
The raw fragment for an equation is the 14 lines preceding its number line,
which is where ACM places the displayed math glyphs.
"""
import argparse
import json
import re

PAGE_RE = re.compile(r"========== \[PAGE (\d+)\] ==========")
EQ_RE = re.compile(r"^\((\d+)\)$")
ALG_RE = re.compile(r"^Algorithm\s+(\d+)\s*(.*)$")
TH_RE = re.compile(r"^(Theorem|Lemma|Definition|Corollary|Proposition)\s+([A-Z]\.\d+|[A-Z]?\d+(?:\.\d+)?)")
FT_RE = re.compile(r"^(Figure|Table)\s+(\d+):")
# 协议/标准类："Figure 7-132  Title"（无冒号、编号带章节前缀）。
FT_PREFIX_RE = re.compile(r"^(Figure|Table)\s+(\d+-\d+)\s+(?=[A-Z0-9(])")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("text")
    ap.add_argument("--out")
    ap.add_argument("--fragment", type=int, default=14)
    a = ap.parse_args()

    lines = open(a.text, encoding="utf-8").read().splitlines()
    # 题注行可能带超链接残留符（§ 既在行首也在 "Figure§ 1-2" 中间），整行剔除。
    stripped = [re.sub(r"^[^A-Za-z\d]{0,3}", "", l.replace("§", "").strip())
                for l in lines]
    # 类别从文本自身判定：出现章节前缀题注即 spec，此时两种风格都收。
    spec = any(FT_PREFIX_RE.match(s) for s in stripped)
    page = 0
    inv = {"equations": [], "algorithms": [], "theorems": [], "figures": [], "tables": []}
    for i, raw in enumerate(lines):
        s = raw.strip()
        sc = stripped[i]          # 只用于题注匹配，避免误伤 PAGE_RE/EQ_RE 的行首锚定
        m = PAGE_RE.match(s)
        if m:
            page = int(m.group(1))
            continue
        m = EQ_RE.match(s)
        if m:
            n = int(m.group(1))
            if not 1 <= n <= 120:      # glyph soup like "(00000)" is not an equation
                continue
            lo = max(0, i - a.fragment)
            prev = [x.strip() for x in lines[lo:i] if x.strip()]
            # spec 类文档的图内标签（如 Root Port 的 "(1) (2) (3) (4)"）是连续成串的
            # "(n)" 行；显示公式的编号则前后紧邻的是数学碎片，不会成串。
            def nxt(k):
                while 0 <= k + 1 < len(lines):
                    k += 1
                    t = lines[k].strip()
                    if t:
                        return t
                return ""

            def prv(k):
                while 0 <= k - 1 < len(lines):
                    k -= 1
                    t = lines[k].strip()
                    if t:
                        return t
                return ""

            if EQ_RE.match(nxt(i)) or EQ_RE.match(prv(i)):
                continue
            # 另一条证据：真显示公式被抽取成碎片短 token，散文上下文则是完整长句。
            avg = (sum(len(x) for x in prev) / len(prev)) if prev else 0.0
            if avg > 70 or sum(1 for x in prev if len(x) < 40) < 3:
                continue
            inv["equations"].append({
                "n": n, "page": page,
                "fragment": " / ".join(x.strip() for x in lines[lo:i] if x.strip())})
            continue
        m = ALG_RE.match(s)
        if m:
            inv["algorithms"].append({"n": int(m.group(1)), "title": m.group(2), "page": page})
            continue
        m = TH_RE.match(s)
        if m:
            inv["theorems"].append({"kind": m.group(1), "n": m.group(2), "page": page,
                                    "head": s[:90]})
            continue
        m = FT_RE.match(sc)
        if not m and spec:
            mp = FT_PREFIX_RE.match(sc)
            if mp:
                kind, num = mp.group(1), int(mp.group(2).split("-")[1])
                inv["figures" if kind == "Figure" else "tables"].append(
                    {"n": num, "page": page, "caption": s[:80]})
                continue
        if m:
            inv["figures" if m.group(1) == "Figure" else "tables"].append(
                {"n": int(m.group(2)), "page": page, "caption": s[:80]})

    summary = {k: (len(v) if k != "equations" else len(v)) for k, v in inv.items()}
    if not any(summary.values()):
        # 全 0 不是「没有资产」而是「正则没吃到」的高发信号：以前这里静默
        # 写空清单，下游 coverage 会拿 source 0 去比 tex 环境数造成假失败。
        print("WARN inventory all-zero: 检查题注/公式格式是否与本脚本正则匹配"
              "（无冒号？带章节前缀？公式编号不在行尾？）")
    blob = json.dumps({"summary": summary, **inv}, ensure_ascii=False, indent=1)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(blob + "\n")
    print(json.dumps(summary, ensure_ascii=False))
    for e in inv["equations"]:
        print(f"  eq ({e['n']}) p{e['page']}: {e['fragment'][:110]}")
    for t in inv["theorems"]:
        print(f"  {t['kind']} {t['n']} p{t['page']}: {t['head']}")
    for t in inv["algorithms"]:
        print(f"  Algorithm {t['n']} p{t['page']}: {t['title']}")
    if a.out:
        print("wrote", a.out)


if __name__ == "__main__":
    main()
