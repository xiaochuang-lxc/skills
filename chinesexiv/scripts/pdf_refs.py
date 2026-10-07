#!/usr/bin/env python3
"""Emit a thebibliography block with numeric keys (r1..rN) from extracted text.

Usage:
  pdf_refs.py TEXT_FILE [OUT_FILE]

Translations cite with \\cite{rN} so the bibliography never has to be
transcribed by hand. Entries are the numbered blocks between the References
heading (case-insensitive) and the end of the file; wrapped lines of one entry
are joined. Cleaning applied (each fixes a real compile failure):
  * NFKD-normalise then drop non-ASCII and control chars - reference titles
    carry math italics (U+1D400..) and stray control bytes that make xelatex
    die with "Missing $ inserted" / "invalid character";
  * escape \\ % & _ $ #;
  * insert \\allowbreak after / _ # so long URLs and code runs can wrap
    (otherwise "Overfull hbox 300pt+").
"""
import re
import sys
import unicodedata

src = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else None

lines = open(src, encoding="utf-8").read().splitlines()
try:
    i = next(k for k, l in enumerate(lines) if l.strip().lower() == "references")
except StopIteration:
    # 规范/标准/白皮书类文档常常根本没有参考文献节。以前这里 exit 1，
    # 会让 pdf_prep.py 的 check=True 在裁英文子 PDF 之前整个中断。
    # 现在写一个空 refs.tex（\input{refs} 变成无操作）并正常退出。
    if out:
        open(out, "w", encoding="utf-8").write(
            "% no References section in the translated page range\n")
        print(f"no References heading; wrote empty {out}", file=sys.stderr)
    else:
        print("no References heading found", file=sys.stderr)
    sys.exit(0)

entries, cur, num = [], None, None
ENTRY = re.compile(r"^\[(\d+)\]\s*(.*)$")
for l in lines[i + 1:]:
    s = l.strip()
    if not s or s.startswith("===="):
        continue
    if s in ("---- LEFT COLUMN ----", "---- RIGHT COLUMN ----"):
        continue
    if re.fullmatch(r"\d+", s):          # printed folio
        continue
    m = ENTRY.match(s)
    if m:
        if cur:
            entries.append((num, cur))
        num, cur = int(m.group(1)), m.group(2)
    elif cur is not None:
        cur += " " + s
if cur:
    entries.append((num, cur))

entries.sort(key=lambda e: e[0])         # column interleaving safety net

body = ["\\begin{thebibliography}{%d}" % (entries[-1][0] if entries else 0), ""]
for n, txt in entries:
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(ch for ch in txt if 32 <= ord(ch) < 128)
    txt = (txt.replace("\\", "\\textbackslash{}")
              .replace("%", "\\%").replace("&", "\\&")
              .replace("_", "\\_\\allowbreak{}")
              .replace("$", "\\$").replace("#", "\\#\\allowbreak{}")
              .replace("/", "/\\allowbreak{}"))
    body.append("\\bibitem{r%d} %s" % (n, txt))
body += ["", "\\end{thebibliography}", ""]
text = "\n".join(body)

if out:
    open(out, "w", encoding="utf-8").write(text)
    print("wrote %s (%d entries)" % (out, len(entries)))
else:
    print(text)
