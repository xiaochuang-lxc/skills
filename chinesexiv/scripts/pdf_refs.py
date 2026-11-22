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
    (otherwise "Overfull hbox 300pt+");
  * drop running headers/footers and stop at the appendix - otherwise the
    page header of every page lands inside some bibitem, and (worse) the whole
    appendix after the bibliography gets swallowed into the last entry.
"""
import re
import sys
import unicodedata
from collections import defaultdict

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

# 页眉/页脚识别：按页标记把全文分行归页，某行若在 >=3 个不同页出现、且至
# 少有一页在 References 之前，它就是版式页眉（而不是换行后的引文尾行）。
# 只靠「重复次数」不够：多条引文可能以同样的 "In Proc. of ACM SIGCOMM." 收尾。
ref_page = 1
page = 1
where = defaultdict(set)
for k, l in enumerate(lines):
    m = re.match(r"=+ \[PAGE (\d+)\] =+", l.strip())
    if m:
        page = int(m.group(1))
        if k < i:
            ref_page = page + 1        # References 之前的页（含其所在页不算）
        continue
    s = l.strip()
    if s and not s.startswith("====") and not s.startswith("----"):
        where[s].add(page)
boiler = {s for s, pgs in where.items() if len(pgs) >= 3
          and any(p < ref_page for p in pgs)}

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
    if s in boiler:                      # 页眉/页脚（标题、会议名、作者行）
        continue
    if len(s) < 40 and re.match(r"^(Appendix|APPENDIX|APPENDICES)\b", s):
        break                            # 附录标题不属于引文（整段附录不得被吐进末条）
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
    # 先把破折号/引号类标点换为 ASCII：否则下一步「丢非 ASCII」会把
    # "87\u201395" 页码粘成 "8795"（EuroSys/ACM 引文里很常见）。
    txt = (txt.replace("\u2013", "-").replace("\u2014", "-")
              .replace("\u2212", "-").replace("\u00ad", "-")
              .replace("\u2018", "'").replace("\u2019", "'")
              .replace("\u201c", '"').replace("\u201d", '"')
              .replace("\u00a0", " "))
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
