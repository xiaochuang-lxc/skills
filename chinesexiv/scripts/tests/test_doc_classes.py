#!/usr/bin/env python3
"""两类文档（paper / spec）的管线回归测试。

为什么需要：skill 的题注正则、分栏策略、验收口径现在按 doc_class 分流，
任何一边的改动都可能悄悄破坏另一边。本测试用 PyMuPDF 合成两份最小 fixture
（双栏论文版式 / 单栏规范版式），对每个被改过的行为分支做断言：

  paper 类（零回归承诺）：
    * detect -> "paper"；extract 输出带 LEFT/RIGHT COLUMN 标记
    * clip 只认冒号题注，产出 figure1.png
    * numbers 用冒号口径，空清单报 WARN 且 exit 0（不再假绿 "OK 1..0"）
    * structure 走逐行 CJK>40 的历史口径
  spec 类（新增能力）：
    * detect -> "spec"；extract 无列标记且列表顺序不乱
    * clip 认 "Figure 1-1  Title"，产出 figure1-1.png；零题注范围 exit 2
    * refs 无 References 时 exit 0 并写空 refs.tex
    * inventory 收章节前缀题注；全 0 时 WARN
    * numbers / structure 用 spec 口径给出真实结论

运行：python3 tests/test_doc_classes.py   （退出码 0 = 全过）
"""
import os
import re
import subprocess
import sys
import tempfile

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)

FAILS = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}{('  ' + detail) if detail and not cond else ''}")
    if not cond:
        FAILS.append(name)


def run(script, *args):
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args],
                          capture_output=True, text=True)


PROSE = ("The quick brown fox jumps over the lazy dog and keeps running "
         "across the whole paragraph so that the block is long enough.")


def make_paper(path):
    """双栏：正文块宽 ~0.39*页宽，冒号题注。"""
    doc = pymupdf.open()
    pg = doc.new_page(width=612, height=792)
    for col, x in (("L", 50), ("R", 320)):
        pg.insert_text((x, 120), PROSE, fontsize=9)
        pg.insert_text((x, 140), PROSE, fontsize=9)
    pg.draw_rect(pymupdf.Rect(60, 200, 280, 320))          # 图框
    pg.insert_text((60, 340), "Figure 1: Latency under load", fontsize=10)
    pg.insert_text((60, 380), PROSE, fontsize=9)
    pg.insert_text((60, 700), "References", fontsize=10)
    pg.insert_text((60, 720), "[1] Author, Title of the referenced work, 2024.", fontsize=9)
    doc.save(path)


def make_spec(path, with_caption=True):
    """单栏：正文块宽 ~0.83*页宽，章节前缀题注，三级列表。"""
    doc = pymupdf.open()
    pg = doc.new_page(width=612, height=792)
    pg.insert_text((50, 100), "1. Introduction", fontsize=12)
    pg.insert_text((50, 120), PROSE + " " + PROSE, fontsize=9)
    for i, y in enumerate((150, 165, 180, 195)):
        pg.insert_text((60, y), f"•  Requirement number {i} shall be supported by all.", fontsize=9)
    if with_caption:
        pg.draw_rect(pymupdf.Rect(60, 220, 550, 340))
        pg.insert_text((60, 360), "Figure 1-1 Example topology", fontsize=10)
    pg.insert_text((50, 400), PROSE + " " + PROSE, fontsize=9)
    doc.save(path)


def make_spec_torture(path):
    """spec 类的全部脏特征合集：§ 在行首与编号中间、多行图例、表下脚注、
    五级标题中的两级。坐标是断言的一部分，不要随手改。"""
    doc = pymupdf.open()
    pg = doc.new_page(width=612, height=792)
    long_ = PROSE + " " + PROSE
    pg.insert_text((50, 100), "1. Scope", fontsize=12)
    pg.insert_text((50, 120), long_, fontsize=9)
    pg.insert_text((60, 150), "•  First requirement shall be supported by all.", fontsize=9)
    pg.insert_text((60, 165), "•  Second requirement shall be supported by all.", fontsize=9)
    pg.draw_rect(pymupdf.Rect(60, 200, 550, 300))
    pg.insert_text((70, 250), long_, fontsize=9)      # 图带内的多行图例
    pg.insert_text((70, 262), long_, fontsize=9)
    pg.insert_text((60, 320), "§ Figure 1-1 Example topology", fontsize=10)
    pg.insert_text((50, 350), long_, fontsize=9)
    pg.draw_rect(pymupdf.Rect(60, 380, 550, 450))
    pg.insert_text((60, 470), "Figure§ 1-2 Second figure", fontsize=10)
    pg.insert_text((60, 520), "Table 1-1 Signaling matrix", fontsize=10)
    for i, y in enumerate((540, 555, 570)):
        pg.insert_text((70, y), f"row {i} value", fontsize=9)
    pg.insert_text((50, 610), "1. Terms like gen3 are ambiguous and this footnote line is long enough to count.", fontsize=8)
    pg.insert_text((50, 650), long_, fontsize=9)
    pg.insert_text((50, 690), "1.1 Subsection title here", fontsize=11)
    doc.save(path)


def main():
    tmp = tempfile.mkdtemp(prefix="cxiv_test_")
    paper_pdf = os.path.join(tmp, "paper.pdf")
    spec_pdf = os.path.join(tmp, "spec.pdf")
    nocap_pdf = os.path.join(tmp, "nocap.pdf")
    make_paper(paper_pdf)
    make_spec(spec_pdf)
    make_spec(nocap_pdf, with_caption=False)

    import doc_class
    check("detect paper", doc_class.detect(paper_pdf, 1, 1) == "paper")
    check("detect spec", doc_class.detect(spec_pdf, 1, 1) == "spec")

    # ---- extract ----
    p_txt = os.path.join(tmp, "paper.txt")
    s_txt = os.path.join(tmp, "spec.txt")
    r = run("pdf_extract.py", paper_pdf, "1", "1", p_txt)
    body = open(p_txt, encoding="utf-8").read()
    check("paper extract keeps column markers", "LEFT COLUMN" in body, r.stderr[:200])
    r = run("pdf_extract.py", spec_pdf, "1", "1", s_txt)
    body = open(s_txt, encoding="utf-8").read()
    check("spec extract has no column markers", "LEFT COLUMN" not in body)
    reqs = [i for i, l in enumerate(body.splitlines())
            if re.match(r"^[•·◦▪]", l)]
    check("spec extract bullet order intact", reqs == list(range(reqs[0], reqs[0] + 4)),
          str(reqs))

    # ---- clip ----
    p_fig = os.path.join(tmp, "pfig")
    s_fig = os.path.join(tmp, "sfig")
    r = run("pdf_clip.py", paper_pdf, "1", "1", p_fig)
    check("paper clip colon caption", os.path.exists(os.path.join(p_fig, "figure1.png")),
          r.stdout[-300:])
    check("paper clip reports class paper", "class=paper" in r.stdout)
    r = run("pdf_clip.py", spec_pdf, "1", "1", s_fig)
    check("spec clip prefix caption", os.path.exists(os.path.join(s_fig, "figure1-1.png")),
          r.stdout[-300:])
    r = run("pdf_clip.py", nocap_pdf, "1", "1", os.path.join(tmp, "nfig"))
    check("zero-caption range exits 2 loudly", r.returncode == 2 and "NO CAPTION MATCHED" in r.stdout,
          f"rc={r.returncode}")

    # ---- refs ----
    refs = os.path.join(tmp, "refs.tex")
    r = run("pdf_refs.py", s_txt, refs)
    check("no References -> exit 0 + empty refs.tex",
          r.returncode == 0 and os.path.exists(refs), f"rc={r.returncode} {r.stderr[:120]}")
    refs2 = os.path.join(tmp, "refs2.tex")
    r = run("pdf_refs.py", p_txt, refs2)
    check("paper References still parsed",
          r.returncode == 0 and "\\bibitem{r1}" in open(refs2, encoding="utf-8").read())

    # ---- inventory ----
    r = run("pdf_inventory.py", s_txt, "--out", os.path.join(tmp, "inv.json"))
    check("inventory counts prefix captions", '"figures": 1' in r.stdout.replace(" ", "") or
          re.search(r'"figures":\s*1', r.stdout) is not None, r.stdout[:200])
    empty = os.path.join(tmp, "empty.txt")
    open(empty, "w").write("nothing here\n")
    r = run("pdf_inventory.py", empty)
    check("inventory all-zero warns", "WARN inventory all-zero" in r.stdout)

    # 图内标签串 "(1)(2)(3)" 不得被当成显示公式；真公式（碎片短行 + 独立编号）必须被认出
    eqtxt = os.path.join(tmp, "eq.txt")
    with open(eqtxt, "w", encoding="utf-8") as f:
        f.write("========== [PAGE 1] ==========\n")
        f.write("Root Port\nRoot Port\n(1)\n(2)\n(3)\n(4)\n")
        f.write("CRC\n= 0 1 0 1 1 1 0 0 1\nLFSR in\nXOR\n(7)\n")
    r = run("pdf_inventory.py", eqtxt)
    check("inventory ignores label runs but keeps real equation",
          re.search(r'"equations":\s*1', r.stdout) is not None, r.stdout[:200])

    # ---- numbers ----
    zh = os.path.join(tmp, "zh.pdf")
    d = pymupdf.open()
    pg = d.new_page()
    # 默认 Base-14 字体不含 CJK，必须显式用内置中文字体，否则「图 1-1」写不进去
    pg.insert_text((72, 200), "图 1-1  示例拓扑", fontsize=11, fontname="china-s")
    d.save(zh)
    r = run("pdf_audit.py", "numbers", zh, s_txt)
    check("numbers spec metric OK", r.returncode == 0 and "OK figures" in r.stdout,
          r.stdout[:200])
    zh2 = os.path.join(tmp, "zh2.pdf")
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_text((72, 200), "图 1: 负载下的延迟", fontsize=11, fontname="china-s")
    d.save(zh2)
    r = run("pdf_audit.py", "numbers", zh2, p_txt)
    check("numbers paper metric OK", r.returncode == 0 and "OK figures" in r.stdout,
          r.stdout[:200])
    r = run("pdf_audit.py", "numbers", zh2, empty)
    check("numbers vacuous warns instead of fake OK",
          r.returncode == 0 and "vacuous" in r.stdout and "OK figures: 1..0" not in r.stdout,
          r.stdout[:200])

    # ---- structure ----
    tex_ok = os.path.join(tmp, "ok.tex")
    with open(tex_ok, "w", encoding="utf-8") as f:
        f.write("\\begin{document}\n")
        f.write("本章给出架构与关键概念的概览，这一段是足够长的中文散文用于计数。\n\n")
        for i in range(4):
            f.write(f"\\item 第 {i} 条需求应当被所有实现支持，这是一条足够长的列表项。\n")
        f.write("\n如图 1-1 所示，第二个散文段也必须出现在译稿里，否则单元数对不上。\n")
        f.write("\\end{document}\n")
    r = run("pdf_audit.py", "structure", spec_pdf, "1", "1", tex_ok)
    check("structure spec metric OK", r.returncode == 0 and "STRUCTURE OK" in r.stdout,
          r.stdout[-300:])
    tex_bad = os.path.join(tmp, "bad.tex")
    with open(tex_bad, "w", encoding="utf-8") as f:
        f.write("\\begin{document}\n\\item 只译了一条。\n\\end{document}\n")
    r = run("pdf_audit.py", "structure", spec_pdf, "1", "1", tex_bad)
    check("structure spec metric catches dropped items",
          r.returncode == 1 and "STRUCTURE FAIL" in r.stdout, r.stdout[-300:])
    ptex = os.path.join(tmp, "paper.tex")
    with open(ptex, "w", encoding="utf-8") as f:
        f.write("\\begin{document}\n")
        for _ in range(5):
            # 论文历史口径是「单行 CJK>40」，fixture 行必须真的超过 40 汉字
            f.write("这一段是足够长的中文散文，超过四十个汉字，用于论文口径的逐行计数检查，"
                    "因此这里再补半句以确保阈值被跨过。\n")
        f.write("\\end{document}\n")
    r = run("pdf_audit.py", "structure", paper_pdf, "1", "1", ptex)
    check("structure paper metric unchanged", r.returncode == 0 and "STRUCTURE OK" in r.stdout,
          r.stdout[-300:])

    # ---- spec-torture：§ 残留 / 多行图例 / 表下脚注 / 标题树 ----
    tor_pdf = os.path.join(tmp, "torture.pdf")
    make_spec_torture(tor_pdf)
    check("detect torture spec", doc_class.detect(tor_pdf, 1, 1) == "spec")
    t_txt = os.path.join(tmp, "torture.txt")
    run("pdf_extract.py", tor_pdf, "1", "1", t_txt)

    r = run("pdf_clip.py", tor_pdf, "1", "1", os.path.join(tmp, "tfig"))
    out = r.stdout
    check("torture clips both §-polluted captions",
          "figure1-1" in out and "figure1-2" in out, out[-400:])
    m = re.search(r"table1-1 p1 .*clip=\((\d+),(\d+),(\d+),(\d+)\)", out)
    check("torture table band stops before footnote",
          bool(m) and 575 <= int(m.group(4)) <= 605, out[-400:])

    r = run("pdf_inventory.py", t_txt)
    check("inventory sees §-polluted prefix captions",
          re.search(r'"figures":\s*2', r.stdout) and re.search(r'"tables":\s*1', r.stdout),
          r.stdout[:200])

    zh3 = os.path.join(tmp, "zh3.pdf")
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_text((72, 150), "图 1-1  示例拓扑", fontsize=11, fontname="china-s")
    pg.insert_text((72, 200), "图 1-2  第二张图", fontsize=11, fontname="china-s")
    pg.insert_text((72, 250), "表 1-1  信令矩阵", fontsize=11, fontname="china-s")
    d.save(zh3)
    r = run("pdf_audit.py", "numbers", zh3, t_txt)
    check("numbers OK on §-polluted source",
          r.returncode == 0 and "OK figures: 1..2" in r.stdout, r.stdout[:200])

    # structure：图例两行不得计入源侧单元（2 列表项 + 3 散文 = 5）
    ttex = os.path.join(tmp, "ttex.tex")
    with open(ttex, "w", encoding="utf-8") as f:
        f.write("\\begin{document}\n"
                "\\hdA{1\\quad 范围}\n"
                "本章给出范围与关键概念，这一段是足够长的中文散文用于计数。\n\n"
                "\\item 第一条需求应当被所有实现支持，这是一条足够长的列表项。\n"
                "\\item 第二条需求应当被所有实现支持，这是一条足够长的列表项。\n\n"
                "如图 1-1 所示的第二段散文，也必须出现在译稿里才能对得上。\n\n"
                "第三段散文在表 1-1 之后，同样需要被译出并计入单元数。\n"
                "\\hdB{1.1\\quad 子节标题}\n"
                "\\end{document}\n")
    r = run("pdf_audit.py", "structure", tor_pdf, "1", "1", ttex)
    check("structure excludes in-figure legend text",
          r.returncode == 0 and "source units 5" in r.stdout, r.stdout[-300:])

    # outline + sections
    r = run("pdf_outline.py", tor_pdf, "1", "1")
    check("outline finds both heading levels",
          "1 " in r.stdout and "1.1" in r.stdout, r.stdout[:200])
    r = run("pdf_audit.py", "sections", tor_pdf, "1", "1", ttex)
    check("sections OK when all headings translated", r.returncode == 0 and "SECTIONS OK" in r.stdout,
          r.stdout[-200:])
    ttex_bad = ttex + ".bad"
    open(ttex_bad, "w").write(open(ttex).read().replace("\\hdB{1.1", "\\hdB{1.2"))
    r = run("pdf_audit.py", "sections", tor_pdf, "1", "1", ttex_bad)
    check("sections catches dropped section", r.returncode == 1 and "SECTIONS MISSING" in r.stdout,
          r.stdout[-200:])

    # footnotes
    ftex = os.path.join(tmp, "ftex.tex")
    open(ftex, "w").write("\\begin{document}\n正文\\setcounter{footnote}{0}\\footnote{诸如 gen3 的说法含糊。}\n\\end{document}\n")
    r = run("pdf_audit.py", "footnotes", tor_pdf, "1", "1", ftex)
    check("footnotes OK with pinned numbering", r.returncode == 0 and "FOOTNOTES OK" in r.stdout,
          r.stdout[-200:])
    ftex_bad = os.path.join(tmp, "ftex_bad.tex")
    open(ftex_bad, "w").write("\\begin{document}\n正文无脚注。\n\\end{document}\n")
    r = run("pdf_audit.py", "footnotes", tor_pdf, "1", "1", ftex_bad)
    check("footnotes catches missing footnote", r.returncode == 1 and "MISMATCH footnotes" in r.stdout,
          r.stdout[-200:])

    # xrefs
    xtex = os.path.join(tmp, "xtex.tex")
    open(xtex, "w").write("\\begin{document}\n详见 § Section 6.32 的定义。\n\\end{document}\n")
    r = run("pdf_audit.py", "xrefs", xtex)
    check("xrefs flags leftover § / English refs", r.returncode == 1 and "XREFS SUSPECT" in r.stdout,
          r.stdout[-200:])
    xtex_ok = os.path.join(tmp, "xtex_ok.tex")
    open(xtex_ok, "w").write("\\begin{document}\n详见第 6.32 节的定义，如图 1-1 所示。\n\\end{document}\n")
    r = run("pdf_audit.py", "xrefs", xtex_ok)
    check("xrefs OK on translated refs", r.returncode == 0 and "XREFS OK" in r.stdout, r.stdout[-200:])

    # ---- 隔离断言：spec 门禁在 paper 类上必须 no-op ----
    r = run("pdf_audit.py", "xrefs", xtex, "paper")
    check("xrefs no-op for paper class", r.returncode == 0 and "spec-only" in r.stdout,
          r.stdout[-200:])
    r = run("pdf_audit.py", "footnotes", paper_pdf, "1", "1", ftex_bad)
    check("footnotes no-op for paper class", r.returncode == 0 and "spec-only" in r.stdout,
          r.stdout[-200:])
    r = run("pdf_audit.py", "sections", paper_pdf, "1", "1", ttex_bad)
    check("sections no-op for paper class", r.returncode == 0 and "spec-only" in r.stdout,
          r.stdout[-200:])

    print(f"\n{len(FAILS)} failures" if FAILS else "\nALL TESTS PASSED")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
