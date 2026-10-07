#!/usr/bin/env python3
"""One-shot preprocessing of a single paper from a proceedings PDF.

Usage:
  pdf_prep.py PDF START END OUTDIR EN_PDF_STEM

Creates OUTDIR with the three raw inputs the translation step needs:
  _text.txt          column-aware reading-order text (pdf_extract.py)
  source/fig/*.png   figures and tables clipped by pdf_clip.py
  <EN_PDF_STEM>.pdf  the paper's own page range, cut from the proceedings
  source/refs.tex    thebibliography with numeric keys (pdf_refs.py)

pdf_clip.py lines starting with "!!" are printed again at the end: every one of
them is a caption that must be handled manually before translating.
"""
import os
import subprocess
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
pdf, start, end = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
outdir, en_stem = os.path.abspath(sys.argv[4]), sys.argv[5]

os.makedirs(os.path.join(outdir, "source", "fig"), exist_ok=True)
txt = os.path.join(outdir, "_text.txt")

subprocess.run([sys.executable, os.path.join(HERE, "pdf_extract.py"),
                pdf, str(start), str(end), txt], check=True)

clip = subprocess.run([sys.executable, os.path.join(HERE, "pdf_clip.py"),
                       pdf, str(start), str(end),
                       os.path.join(outdir, "source", "fig")],
                      capture_output=True, text=True, check=False)
sys.stdout.write(clip.stdout)
if clip.returncode == 2:
    # 零题注命中：fig/ 为空。不中断（无图论文也走这条路），但必须让调用者看见。
    print("!! WARNING: pdf_clip found no captions; continuing with empty fig/. "
          "确认该页码范围确实没有图，否则检查题注格式/页码范围。", flush=True)
elif clip.returncode != 0:
    sys.stderr.write(clip.stderr)
    raise SystemExit(clip.returncode)

subprocess.run([sys.executable, os.path.join(HERE, "pdf_refs.py"),
                txt, os.path.join(outdir, "source", "refs.tex")], check=False)
# check=False：无参考文献节的文档（规范/标准类）不该中断后面的英文子 PDF 裁切

doc = pymupdf.open(pdf)
sub = pymupdf.open()
sub.insert_pdf(doc, from_page=start - 1, to_page=end - 1)
sub.save(os.path.join(outdir, en_stem + ".pdf"))
sub.close()

figs = sorted(os.listdir(os.path.join(outdir, "source", "fig")))
print(f"enpdf  -> {en_stem}.pdf ({end - start + 1} pages)")
print(f"figs   -> {len(figs)}: {figs}")
miss = [l for l in clip.stdout.splitlines() if l.startswith("!!")]
print(f"misses -> {len(miss)}")
for l in miss:
    print("   " + l)
