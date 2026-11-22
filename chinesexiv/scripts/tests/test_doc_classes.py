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
# 窄散文（宽 <0.7*页宽）：避免单行 PROSE 被 detect 误判为单栏 spec。
PROSE_N = ("The quick brown fox jumps over the lazy dog and keeps running.")


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


def make_ieee(path):
    """IEEE 双栏：Fig. N. 两行式题注 + 跨栏图（figure*）+ TABLE 罗马 + 正文交叉引用。
    坐标是断言的一部分（跨栏图两半矢量框分落左右栏），不要随手改。"""
    doc = pymupdf.open()
    pg = doc.new_page(width=612, height=792)
    for x in (50, 320):
        pg.insert_text((x, 120), PROSE, fontsize=9)
        pg.insert_text((x, 140), PROSE, fontsize=9)
    pg.draw_rect(pymupdf.Rect(60, 200, 280, 300))     # 跨栏图左半
    pg.draw_rect(pymupdf.Rect(320, 200, 550, 300))    # 跨栏图右半
    pg.insert_text((60, 320), "Fig. 1.", fontsize=10)
    pg.insert_text((60, 332), "The algorithmic framework.", fontsize=10)
    # 正文交叉引用（同行小写动词）不得被当题注
    pg.insert_text((60, 360), "Fig. 1 shows the framework and more details here.", fontsize=9)
    pg.insert_text((320, 60), "TABLE I", fontsize=10)
    pg.insert_text((320, 72), "EXAMPLE RULE SET", fontsize=10)
    doc.save(path)


def make_ieee_top(path):
    """图体矢量框顶到 y<72（页顶图例）：ieee 下应并入并集而非被页眉阈值切掉。"""
    doc = pymupdf.open()
    pg = doc.new_page(width=612, height=792)
    pg.draw_rect(pymupdf.Rect(60, 50, 280, 150))
    pg.insert_text((60, 170), "Fig. 1.", fontsize=10)
    pg.insert_text((60, 182), "Top legend figure.", fontsize=10)
    pg.insert_text((60, 220), PROSE_N, fontsize=9)
    doc.save(path)


def make_ieee_stack(path):
    """同栏上下两张图：第二张带顶不得落到页顶混入第一张图体。"""
    doc = pymupdf.open()
    pg = doc.new_page(width=612, height=792)
    pg.draw_rect(pymupdf.Rect(60, 100, 280, 180))
    pg.insert_text((60, 190), "Fig. 1.", fontsize=10)
    pg.insert_text((60, 202), "First figure.", fontsize=10)
    pg.draw_rect(pymupdf.Rect(60, 230, 280, 300))
    pg.insert_text((60, 310), "Fig. 2.", fontsize=10)
    pg.insert_text((60, 322), "Second figure.", fontsize=10)
    doc.save(path)


def make_ieee_tablecol(path):
    """右栏图 + 左栏表同带：左栏表框不得作为本图跨栏证据。"""
    doc = pymupdf.open()
    pg = doc.new_page(width=612, height=792)
    pg.insert_text((60, 210), "TABLE I", fontsize=10)
    pg.insert_text((60, 222), "Example rule set.", fontsize=10)
    pg.draw_rect(pymupdf.Rect(60, 230, 280, 300))
    pg.draw_rect(pymupdf.Rect(320, 230, 550, 300))
    pg.insert_text((320, 310), "Fig. 1.", fontsize=10)
    pg.insert_text((320, 322), "Right column figure with a much longer caption title here.", fontsize=10)
    doc.save(path)


def make_mixed(path):
    """同时含 ACM 冒号题注与 IEEE 题注：必须保持 acm（零回归开关）。"""
    doc = pymupdf.open()
    pg = doc.new_page(width=612, height=792)
    pg.insert_text((50, 120), PROSE_N, fontsize=9)
    pg.insert_text((320, 150), PROSE_N, fontsize=9)
    pg.draw_rect(pymupdf.Rect(60, 200, 280, 300))
    pg.insert_text((60, 320), "Figure 1: ACM style caption", fontsize=10)
    pg.insert_text((60, 360), "Fig. 2.", fontsize=10)
    doc.save(path)


def make_mixed_dot(path):
    """同时含 ACM 冒号题注与 acmdot 句点题注：必须保持 acm（零回归开关）。"""
    doc = pymupdf.open()
    pg = doc.new_page(width=612, height=792)
    pg.insert_text((50, 120), PROSE_N, fontsize=9)
    pg.insert_text((320, 150), PROSE_N, fontsize=9)
    pg.draw_rect(pymupdf.Rect(60, 200, 280, 300))
    pg.insert_text((60, 320), "Figure 1: ACM style caption", fontsize=10)
    pg.draw_rect(pymupdf.Rect(320, 200, 560, 300))
    pg.insert_text((320, 320), "Figure 2. Dot style caption", fontsize=10)
    doc.save(path)


def make_acmdot(path):
    """EuroSys / acmart format=true 双栏：题注用句点（"Figure 1. Title"），
    图体在题注上方（同 ACM），但**表体也在题注上方**（与 ACM 惯例相反），
    题注还可与子图标签同块（标签在前）。坐标是断言的一部分，不要随手改。"""
    doc = pymupdf.open()
    pg = doc.new_page(width=612, height=792)
    # 两栏散文错开基线，避免 PyMuPDF 把同行文字合成一个通栏块（会被 detect 误判单栏）
    for x, dy in ((50, 0), (320, 4)):
        for k in range(2):
            pg.insert_text((x, 120 + dy + 20 * k), PROSE_N, fontsize=9)
    # 左栏图 1：图体在上、句点题注在下
    pg.draw_rect(pymupdf.Rect(60, 200, 280, 300))
    pg.insert_text((60, 320), "Figure 1. Architecture of the chipset.", fontsize=10)
    # 左栏图 2：子图标签与题注同一文本块（标签行在前，题注是末行）
    pg.draw_rect(pymupdf.Rect(60, 380, 160, 440))
    pg.draw_rect(pymupdf.Rect(170, 380, 280, 440))
    assert pg.insert_textbox(pymupdf.Rect(58, 445, 300, 505),
                             "(a) Baseline\n(b) Ours\n"
                             "Figure 2. (Exp#1) Latency under load.", fontsize=9) >= 0
    # 左栏散文：中间行恰好以 "Table 1. Hardware…" 开头（换行落在句边界），
    # 既非块首也非块末，不得被当题注
    assert pg.insert_textbox(pymupdf.Rect(58, 560, 300, 620),
                             "the quick brown fox jumps over the lazy dog and keeps\n"
                             "Table 1. Hardware features of chips differ a lot here,\n"
                             "running across the whole paragraph so it stays prose", fontsize=9) >= 0
    # 右栏表 1：表体在上、题注在下（本风格的关键差异）
    pg.draw_rect(pymupdf.Rect(320, 200, 560, 280))
    pg.insert_text((325, 230), "Switch Chips   Vendor A   Ours", fontsize=9)
    pg.insert_text((325, 250), "Bandwidth   1.6 Tbps   1.2 Tbps", fontsize=9)
    pg.insert_text((320, 300), "Table 1. Hardware features of existing chips.", fontsize=10)
    # 右栏图 3：在表题注下方，带上界必须被表题注钉住，不得把表体渗进来
    pg.draw_rect(pymupdf.Rect(320, 340, 560, 400))
    pg.insert_text((320, 420), "Figure 3. (Exp#2) Throughput comparison.", fontsize=10)
    # 正文交叉引用（无句点）不得成为题注
    pg.insert_text((320, 460), "Figure 1 shows the architecture and more details here.", fontsize=9)
    pg.insert_text((320, 480), "Table 1 lists the bandwidth and the memory size.", fontsize=9)
    pg.insert_text((320, 700), "References", fontsize=10)
    pg.insert_text((320, 720), "[1] Author, Title of the referenced work, 2026.", fontsize=9)
    doc.save(path)


def make_heading_torture(path):
    """右栏图内含大字号（11pt）缩进数字行（首行纯数字）：不得被 is_heading
    误判为节标题（否则图上半部被切，PSN-PATH 图 4 实测事故）。坐标是断言
    的一部分，不要随手改。"""
    doc = pymupdf.open()
    pg = doc.new_page(width=612, height=792)
    for x in (50, 320):                      # 两栏散文→栏左参照 {50, 320}
        for y in (300, 312, 324):
            pg.insert_text((x, y), PROSE_N, fontsize=9)
    pg.draw_rect(pymupdf.Rect(320, 80, 560, 120))     # 图上半框
    for i, y in enumerate((132, 144, 156, 168)):      # 缩进大字号数字行
        pg.insert_text((360, y), ["3", "7", "11", "15"][i], fontsize=11)
    pg.draw_rect(pymupdf.Rect(320, 175, 560, 205))    # 图下半框
    pg.insert_text((320, 220), "Figure 1: Remapping example.", fontsize=10)
    doc.save(path)


def make_refs_headers(path):
    """跨页参考文献 + 页眉页脚 + 附录：页眉不得混进引文，附录不得被吞进末条。"""
    doc = pymupdf.open()
    for p in range(3):
        pg = doc.new_page(width=612, height=792)
        pg.insert_text((50, 40), "SHORT TITLE OF THE PAPER", fontsize=9)
        pg.insert_text((300, 40), "VENUS 26, Somewhere", fontsize=9)
        pg.insert_text((50, 700), str(100 + p), fontsize=9)
        if p == 0:
            pg.insert_text((50, 120), PROSE, fontsize=9)
            pg.insert_text((50, 200), "References", fontsize=10)
            pg.insert_text((50, 220), "[1] A. Author. 2024. First referenced work title. "
                                      "In Proc. of ACM TEST.", fontsize=9)
        elif p == 1:
            pg.insert_text((50, 120), "[2] B. Author. 2023. Second referenced work title. "
                                      "In Proc. of ACM TEST.", fontsize=9)
        else:
            pg.insert_text((50, 120), "[3] C. Author. 2022. Third referenced work title. "
                                      "In Proc. of ACM TEST.", fontsize=9)
            pg.insert_text((50, 160), "Appendix A", fontsize=10)
            pg.insert_text((50, 180), "EXTRA APPENDIX BODY THAT MUST NOT JOIN THE LAST ENTRY.",
                           fontsize=9)
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

    # ---- refs 页眉/附录污染（EuroSys 实测：页眉进引文、整段附录被吞进末条）----
    rh_pdf = os.path.join(tmp, "refshead.pdf")
    make_refs_headers(rh_pdf)
    rh_txt = os.path.join(tmp, "refshead.txt")
    run("pdf_extract.py", rh_pdf, "1", "3", rh_txt)
    rh_refs = os.path.join(tmp, "rh.tex")
    r = run("pdf_refs.py", rh_txt, rh_refs)
    blob = open(rh_refs, encoding="utf-8").read() if os.path.exists(rh_refs) else ""
    check("refs drops running headers",
          "SHORT TITLE OF THE PAPER" not in blob and "VENUS 26" not in blob, blob[:200])
    check("refs stops before appendix body",
          "EXTRA APPENDIX BODY" not in blob, blob[-200:])
    check("refs keeps all three entries",
          all(f"\\bibitem{{r{n}}}" in blob for n in (1, 2, 3))
          and "Third referenced work title" in blob, blob[:200])
    # 破折号清洗用文本级 fixture：base-14 字体的 insert_text 会把 en dash 写成
    # 中点，无法从 PDF 往返，故直接给 pdf_refs 喂含真 U+2013 的抽取文本。
    dtxt = os.path.join(tmp, "dash.txt")
    with open(dtxt, "w", encoding="utf-8") as f:
        f.write("========== [PAGE 1] ==========\nReferences\n"
                "[1] A. Author. 2024. Title of the work. ACM SIGCOMM CCR 44, 3 "
                "(2014), 87\u201395.\n")
    dref = os.path.join(tmp, "dash.tex")
    run("pdf_refs.py", dtxt, dref)
    dblob = open(dref, encoding="utf-8").read()
    check("pdf_refs maps en-dash page range to '-' instead of gluing digits",
          "87-95" in dblob and "8795" not in dblob, dblob[:200])

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

    # ---- IEEE 题注风格（paper 类内部第二种版式）----
    ieee_pdf = os.path.join(tmp, "ieee.pdf")
    make_ieee(ieee_pdf)
    check("detect ieee still paper", doc_class.detect(ieee_pdf, 1, 1) == "paper")
    check("caption_style ieee", doc_class.caption_style(ieee_pdf, 1, 1) == "ieee")
    check("caption_style acm unchanged", doc_class.caption_style(paper_pdf, 1, 1) == "acm")
    check("caption_style spec unchanged", doc_class.caption_style(spec_pdf, 1, 1) == "spec")
    i_fig = os.path.join(tmp, "ifig")
    r = run("pdf_clip.py", ieee_pdf, "1", "1", i_fig)
    out = r.stdout
    check("ieee clip finds Fig. N. caption",
          os.path.exists(os.path.join(i_fig, "figure1.png")), out[-300:])
    m = re.search(r"figure1 p1 .*clip=\((\d+),(\d+),(\d+),(\d+)\)", out)
    check("ieee full-width figure not column-truncated",
          bool(m) and (int(m.group(3)) - int(m.group(1))) > 0.7 * 612, out[-300:])
    check("ieee does not auto-crop tables",
          not os.path.exists(os.path.join(i_fig, "table1.png")))
    check("ieee body cross-ref not a caption",
          "figure2" not in out and out.count("figure1 p1") == 1, out[-300:])
    i_txt = os.path.join(tmp, "ieee.txt")
    run("pdf_extract.py", ieee_pdf, "1", "1", i_txt)
    r = run("pdf_inventory.py", i_txt)
    check("inventory counts ieee fig+table",
          re.search(r'"figures":\s*1', r.stdout) and re.search(r'"tables":\s*1', r.stdout),
          r.stdout[:200])
    zh_i = os.path.join(tmp, "zhi.pdf")
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_text((72, 200), "图 1: 算法框架", fontsize=11, fontname="china-s")
    pg.insert_text((72, 240), "表 1: 示例规则集", fontsize=11, fontname="china-s")
    d.save(zh_i)
    r = run("pdf_audit.py", "numbers", zh_i, i_txt)
    check("numbers real (non-vacuous) on ieee",
          r.returncode == 0 and "OK figures: 1..1" in r.stdout and "OK tables: 1..1" in r.stdout,
          r.stdout[:200])

    # ---- IEEE 几何修正 ----
    top_pdf = os.path.join(tmp, "ieeetop.pdf")
    make_ieee_top(top_pdf)
    r = run("pdf_clip.py", top_pdf, "1", "1", os.path.join(tmp, "tfig2"))
    m = re.search(r"figure1 p1 .*clip=\((\d+),(\d+),(\d+),(\d+)\)", r.stdout)
    check("ieee keeps figure boxes above y=72",
          bool(m) and int(m.group(2)) <= 56, r.stdout[-300:])

    stk_pdf = os.path.join(tmp, "ieeestack.pdf")
    make_ieee_stack(stk_pdf)
    r = run("pdf_clip.py", stk_pdf, "1", "1", os.path.join(tmp, "stkfig"))
    m2 = re.search(r"figure2 p1 .*clip=\((\d+),(\d+),(\d+),(\d+)\)", r.stdout)
    check("ieee stacked figure band top bounded (no bleed)",
          bool(m2) and int(m2.group(2)) >= 200, r.stdout[-300:])

    tc_pdf = os.path.join(tmp, "ieeetabcol.pdf")
    make_ieee_tablecol(tc_pdf)
    tc_fig = os.path.join(tmp, "tcfig")
    r = run("pdf_clip.py", tc_pdf, "1", "1", tc_fig)
    m3 = re.search(r"figure1 p1 .*clip=\((\d+),(\d+),(\d+),(\d+)\)", r.stdout)
    check("ieee figure beside table stays column-width",
          bool(m3) and int(m3.group(1)) > 300, r.stdout[-300:])
    check("ieee table not auto-cropped (tablecol)",
          not os.path.exists(os.path.join(tc_fig, "table1.png")))

    mix_pdf = os.path.join(tmp, "mixed.pdf")
    make_mixed(mix_pdf)
    check("mixed acm+ieee stays acm (zero-regression switch)",
          doc_class.caption_style(mix_pdf, 1, 1) == "acm")

    # ---- IEEE inventory 去重 / 罗马表 / numbers 集合语义 ----
    ietxt = os.path.join(tmp, "ieee_dedup.txt")
    with open(ietxt, "w", encoding="utf-8") as f:
        f.write("========== [PAGE 1] ==========\n"
                "Fig. 1.\nThe algorithmic framework.\n"
                "Fig. 1. Based on the framework we continue the discussion here.\n"
                "Fig. 2.\nThe construction process.\n"
                "Fig. 2 shows the construction time of data structures for various sets.\n"
                "TABLE IV\nRESOURCE UTILIZATION FOR DIFFERENT RULE SETS\n")
    r = run("pdf_inventory.py", ietxt)
    check("inventory dedupes body cross-refs, maps Roman table",
          re.search(r'"figures":\s*2', r.stdout) and re.search(r'"tables":\s*1', r.stdout),
          r.stdout[:200])
    zh_d = os.path.join(tmp, "zhd.pdf")
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_text((72, 200), "图 1: 框架", fontsize=11, fontname="china-s")
    pg.insert_text((72, 240), "图 2: 构建过程", fontsize=11, fontname="china-s")
    pg.insert_text((72, 280), "表 4: 资源利用率", fontsize=11, fontname="china-s")
    d.save(zh_d)
    r = run("pdf_audit.py", "numbers", zh_d, ietxt)
    check("numbers set-semantics with body cross-refs",
          r.returncode == 0 and "OK figures: 1..2" in r.stdout and "OK tables" in r.stdout,
          r.stdout[:200])

    # ---- acmdot（EuroSys / acmart format=true：句点题注 + 表体在题注上方）----
    dot_pdf = os.path.join(tmp, "acmdot.pdf")
    make_acmdot(dot_pdf)
    check("detect acmdot still paper", doc_class.detect(dot_pdf, 1, 1) == "paper")
    check("caption_style acmdot", doc_class.caption_style(dot_pdf, 1, 1) == "acmdot")
    md_pdf = os.path.join(tmp, "mixeddot.pdf")
    make_mixed_dot(md_pdf)
    check("mixed acm+acmdot stays acm (zero-regression switch)",
          doc_class.caption_style(md_pdf, 1, 1) == "acm")
    d_fig = os.path.join(tmp, "dfig")
    r = run("pdf_clip.py", dot_pdf, "1", "1", d_fig)
    out = r.stdout
    check("acmdot clip reports style=acmdot", "style=acmdot" in out, out[-300:])
    check("acmdot clips dot captions figure1/2/3",
          all(os.path.exists(os.path.join(d_fig, f"figure{n}.png")) for n in (1, 2, 3)),
          out[-300:])
    check("acmdot does not auto-crop tables (body sits above caption)",
          not os.path.exists(os.path.join(d_fig, "table1.png")), out[-300:])
    check("acmdot cross-refs are not captions",
          "figure4" not in out and out.count("figure1 p1") == 1, out[-300:])
    import pdf_clip
    d_blocks, d_caps = pdf_clip.text_blocks(pymupdf.open(dot_pdf)[0], dot=True)
    check("acmdot recognizes exactly fig1/2/3 + table1 as captions",
          len(d_caps) == 4, str([c[1].group(0) for c in d_caps]))
    check("acmdot returns same-block sub-figure label lines to blocks",
          any("(a) Baseline" in t for _, t in d_blocks)
          and not any(t.startswith("Figure 2.") for _, t in d_blocks))
    check("acmdot interior-line lookalike is not a caption",
          not any(t.startswith("Table 1. Hardware features of chips differ")
                  for _, t in d_blocks))
    m = re.search(r"figure2 p1 .*clip=\((\d+),(\d+),(\d+),(\d+)\)", out)
    check("acmdot figure2 covers both sub-figure rects and stops above caption",
          bool(m) and int(m.group(1)) <= 56 and int(m.group(2)) <= 380
          and int(m.group(3)) >= 284 and 435 <= int(m.group(4)) <= 471, out[-300:])
    m = re.search(r"figure3 p1 .*clip=\((\d+),(\d+),(\d+),(\d+)\)", out)
    check("acmdot figure below table caption excludes the table body",
          bool(m) and int(m.group(2)) >= 300, out[-300:])
    d_txt = os.path.join(tmp, "acmdot.txt")
    run("pdf_extract.py", dot_pdf, "1", "1", d_txt)
    r = run("pdf_inventory.py", d_txt)
    check("inventory counts acmdot fig+table",
          re.search(r'"figures":\s*3', r.stdout) and re.search(r'"tables":\s*1', r.stdout),
          r.stdout[:200])
    zh_d2 = os.path.join(tmp, "zhd2.pdf")
    d = pymupdf.open()
    pg = d.new_page()
    for i, y in enumerate((160, 200, 240, 280), start=1):
        label = "表 1: 硬件特性" if i == 4 else f"图 {i}: 句点式题注"
        pg.insert_text((72, y), label, fontsize=11, fontname="china-s")
    d.save(zh_d2)
    r = run("pdf_audit.py", "numbers", zh_d2, d_txt)
    check("numbers real (non-vacuous) on acmdot",
          r.returncode == 0 and "OK figures: 1..3" in r.stdout and "OK tables: 1..1" in r.stdout,
          r.stdout[:250])

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

    # ---- 节标题误判回归（PSN-PATH 图 4 事故）：大字号缩进数字行不得当节标题 ----
    import pdf_clip
    check("is_heading: real heading aligned to column left",
          pdf_clip.is_heading("4.1\nTraffic Measurement Module", 11.0, 318, [54, 318]))
    check("is_heading: big indented numeric row in figure is NOT heading",
          not pdf_clip.is_heading("3\n7\n11\n15 → ⋯", 10.7, 353, [54, 318]))
    check("is_heading: small size rejects",
          not pdf_clip.is_heading("4.1\nTitle", 9.0, 318, [54, 318]))
    check("is_heading: fallback to size-only when no prose on page",
          pdf_clip.is_heading("4.1\nTitle", 11.0, 318, []))
    check("col_left_edges clusters two columns",
          pdf_clip.col_left_edges([pymupdf.Rect(54, 0, 200, 10),
                                   pymupdf.Rect(55, 0, 200, 10),
                                   pymupdf.Rect(318, 0, 500, 10),
                                   pymupdf.Rect(320, 0, 500, 10)]) == [54, 318])
    ht_pdf = os.path.join(tmp, "heading.pdf")
    make_heading_torture(ht_pdf)
    ht_fig = os.path.join(tmp, "htfig")
    r = run("pdf_clip.py", ht_pdf, "1", "1", ht_fig)
    ht_png = os.path.join(ht_fig, "figure1.png")
    ht_h = pymupdf.Pixmap(ht_png).height if os.path.exists(ht_png) else 0
    # 完整图应覆盖 y80..205（≈137pt×3≈410px）；误判时只剩下半框（≈120px）
    check("figure with big indented numeric row not truncated",
          r.returncode == 0 and ht_h > 300, f"height={ht_h} {r.stdout[-200:]}")

    print(f"\n{len(FAILS)} failures" if FAILS else "\nALL TESTS PASSED")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
