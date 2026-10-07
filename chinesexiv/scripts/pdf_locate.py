#!/usr/bin/env python3
"""Locate individual papers inside a whole-proceedings PDF.

Usage:
  pdf_locate.py PDF [--doi-regex REGEX] [--out FILE]

A paper's first page is recognised by the ACM reference-format block: a line
matching the DOI regex together with "ACM Reference Format" or an ISBN/copyright
line on the same page. The paper spans until the page before the next paper's
first page. Emits JSON: [{pdf_start, pdf_end, doi, title}].

The title is reconstructed from the first text lines of the page, stopping at
the author block (a line ending in a comma-less name list is hard to detect, so
we stop at the first line that looks like an affiliation or at 4 lines).
"""
import argparse
import json
import re

import pymupdf


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pdf")
    ap.add_argument("--doi-regex", default=r"10\.\d{4,9}/[^\s,]+")
    ap.add_argument("--out")
    a = ap.parse_args()

    doi_re = re.compile(a.doi_regex)
    doc = pymupdf.open(a.pdf)
    starts = []
    for i in range(doc.page_count):
        text = doc[i].get_text()
        m = doi_re.search(text)
        if m and ("Reference Format" in text or "ISBN" in text):
            starts.append((i + 1, m.group(0)))

    papers = []
    for k, (pno, doi) in enumerate(starts):
        end = starts[k + 1][0] - 1 if k + 1 < len(starts) else doc.page_count
        lines = [l.strip() for l in doc[pno - 1].get_text().splitlines() if l.strip()]
        title = " ".join(lines[:2]) if lines else ""
        papers.append({"pdf_start": pno, "pdf_end": end, "doi": doi, "title": title})

    blob = json.dumps(papers, ensure_ascii=False, indent=1)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(blob + "\n")
        print(f"wrote {a.out} ({len(papers)} papers)")
    else:
        print(blob)


if __name__ == "__main__":
    main()
