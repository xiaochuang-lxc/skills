# PDF 管线参考（无 arXiv 源码时的翻译路径）

当用户给的是**论文集/单篇 PDF** 而非 arXiv LaTeX 源码时走本管线。脚本：
`pdf_locate.py`（定位论文页码）→ `pdf_prep.py`（抽取+裁图+裁子PDF+参考文献）→
人工撰写 `source/main_zh.tex` → `compile.py` 编译 → `pdf_audit.py` 验收。

## 失败模式 → 修复规则（全部来自真实事故）

| 事故现象 | 根因 | 规则 |
|---|---|---|
| 正文两栏交错、连字损坏（Ï/Ò） | `get_text(sort=True)` | 用 `pdf_extract.py` 按块中心 x 分栏 + 连字修复 |
| 裁出的图缺左右坐标轴 | 旋转轴标题/刻度是**文字块**，不在 `get_drawings()` 里 | 非图题、非段落的文字块必须并入并集 |
| 裁出的图缺闭合边框 | 图框是 0 高/0 宽路径；PyMuPDF 视零面积矩形为 EMPTY，`|` 并集**静默丢弃** | 细线膨胀 0.6pt 后再并集；但不得参与间隙检测 |
| 密集页把邻图与英文图题一起抓进 | 固定高度窗向上并集 | 纵向带 = 上方最近**段落/图题/表格主体**底边 → 图题顶边 |
| 并排子图互相渗透 | 用图题中点切分，而图常比图题宽 | 在同一行图题之间取**合并占用区间的最大真实空隙**（空隙中点须落在两图题之间 ±10pt）切分 |
| 邻图整框/整页横线渗进本图 | 宽框按中心误归属 | 宽于 0.70×页宽的框只归属整宽窗口（不要用内缩修碎边：会切掉本图自己的轴标签） |
| 图裁进作者行/摘要/页眉/页码 | 页眉页码混入候选集 | 排除 y<72 与 y>页高−45 的块；纯数字块（folio）一律排除 |
| 整栏正文混入图的并集 | 段落判定阈值 0.45×页宽 漏掉双栏正文（约 0.41×页宽） | 段落三条件：len≥60 且 宽≥0.30×页宽 且 平均行长≥40（子标签行宽但参差，须排除） |
| 表格裁不出 / 裁进下方的图 | ACM 表题在表体**上方**，方向与图相反；且无停止条件 | Table 带向下取；遇第一个 >10pt 空隙或第一个矢量图即止；表格主体同时作为其下方图的带上界 |
| 正文 "Figure 10 illustrates…" 被当图题 | 正则未要求冒号 | `^(Figure|Table)\s+(\d+):` 且**按行**匹配（子图题 `(a)…(b)…Figure N:` 同块） |
| 译文图号与原文错位 | 并排图合并进一个 figure 环境；表被重建成 table 环境占位 | **一图一环境、一表一环境，按原文顺序**；重建的中文表格也放进对应编号的环境内 |
| 章节散文被合并/丢段（如原文 §2.1 两段译成一段） | 凭笔记骨架或记忆写译稿，段落结构未与原文对齐 | 逐段对照 `_text.txt` 翻译；交付前跑 `pdf_audit.py structure`，译稿段落数须 ≥ 原文散文块数 90\%，否则按逐节对照表回原文补译 |
| 段数相符但句子/数字被丢（如引言丢验证实验、丢贡献条目） | 计数门禁只看段落数，合并两句仍计一段 | `pdf_audit.py fidelity` 对每个含数字的源段做数字指纹覆盖（≥70\% 的数字须出现在译稿），SUSPECT 逐条回原文补译 |
| §2–§6 公式/算法/定理整段丢失 | PDF 抽取把显示公式打成 glyph 碎片，凭笔记骨架写译稿时静默跳过 | 动笔前跑 `pdf_inventory.py` 列全编号公式/算法/定理清单并附原文碎片；译后跑 `pdf_audit.py coverage` 强制比对，MISSING 非空不得交付 |
| 编译报 Missing $ / invalid character | 参考文献含数学斜体 Unicode 与控制字符 | `pdf_refs.py`：NFKD → 丢弃非 ASCII 与控制符 → 转义 `\ % & _ $ #` |
| Overfull hbox 300pt+ | 参考文献长 URL/代码串不可断行 | 转义后在 `/ _ #` 后插 `\allowbreak{}`；导言加 `\emergencystretch{3em}` |
| 竖版/超大图**静默丢 caption**（numbers 报某图号缺失、但图存在且计数器已推进） | 图太高 → `Overfull \vbox … too high` → `[H]` 浮动体被丢、caption 未排版 | 编译日志除 hbox 外**必须 grep `Overfull \vbox.*too high`**；缩小该图 width（竖版图常需 ≤0.5\linewidth）直到 vbox 归零；numbers 门禁正是靠「缺号」暴露它 |
| coverage 误报重建图/表「未包含」 | 原「Figure N」其实是表、被重建成 figure 内的 tabular；booktabs 表用描述性 `\label{tab:x}` 而非 `tab:N` | coverage 改为「裁剪 png 数 + 重建环境数 == 源数」的全局一致性判定，不再硬性要求每个 `figureN.png`/`tab:N` |
| fidelity 误报裁剪表格/图内文字 | 裁剪的表体/图内矢量文字以 block 泄漏，数字在图片里、不在 tex | fidelity 先用 `find_tables()` 排除表区，再按 ACM 惯例排除**图题上方 / 表题下方 ±200pt 带内**的块 |

## main_zh.tex 重建规范

- 单栏重排（`article` 11pt + `geometry` margin 2.2cm），**不**复刻双栏；向用户声明这一取舍。
- 导言固定件：`graphicx/amsmath/booktabs/caption/enumitem/multirow/float/hyperref`、
  `\graphicspath{{fig/}}`、`\captionsetup{font=small,labelfont=bf}`、
  `\AtBeginDocument` 内 renew `\figurename/\tablename/\refname` 为 图/表/参考文献、
  `\setlength{\emergencystretch}{3em}`。
- 所有浮动体用 `[H]`（float 包），否则图会漂到参考文献之后。
- 正文交叉引用用 `\ref`；引用用 `\cite{rN}`（数字键，来自 `source/refs.tex`，末尾 `\input{refs}`）。
- **公式/算法强制清单（机器校验）**：`pdf_inventory.py TEXT --out inv.json` 抽取全部
  编号公式（独立成行的 `(n)`）、`Algorithm n`、`Theorem/Lemma/Definition/Corollary/Proposition`
  及图表清单，并附每条公式前 14 行原文碎片供重建 LaTeX；译文用 `equation` 环境按原顺序编号、
  算法用非浮动 tabular 逐行呈现；`pdf_audit.py coverage TEX inv.json` 校验数量与逐条存在性，
  MISSING 非零即回原文补读对应段。不得只凭摘要/笔记骨架写公式章节。
- 大文件分块写：先 Write 第一段，再用 SearchReplace 以 `\end{document}` 为锚追加。

## 验收（交付前强制）

1. `pdf_audit.py numbers 译文.pdf _text.txt` 必须全 OK（图/表编号连续且与原文一致）。
2. 编译日志 Overfull hbox 计数为 0；**并 grep `Overfull \vbox` 计数为 0**（竖版/超大图会因 vbox 溢出被静默丢弃 caption，numbers 随即报缺号——此时缩小该图 width，而非怀疑图丢失）。
3. `pdf_audit.py sheet fig/ /tmp/sheet` 后**逐张目视**总览图：截断、串图、英文图题残留只能这样发现。
4. 抽查成品 PDF 中此前出过问题的页（并排图页、表格页）。

`pdf_locate.py` 以「页内同时出现 DOI 与 Reference Format/ISBN」判定论文首页。已知边界：若某篇内页重复出现该组合（如插页广告/版权框），会被误切短；对要翻译的篇目，用 ACM 参考格式里的「N pages」核对 `pdf_end - pdf_start + 1`，不符时手工指定页码范围。

## 硬案例：并排双轴图

三张并排且带左右双轴的图（如 Dorado p477 的 Fig 17/18/19），图间留白（~4pt）小于图内部「plot→右轴」间隙（~6pt），最大间隙切分会把一张图从它自己的右轴处剖开：表现为左图右轴标签被切片、右图左缘渗入邻图右轴。最大间隙启发式无法区分二者。**处理：目视审计发现后手工框定**（Manual overrides），不要用全局参数去迁就（加内缩/加 slack 会切掉其他页的正常轴标签，已验证回归）。

## 硬案例：同一栏内的并排子图（最右一张渗进邻栏正文）

两张子图并排、但**整行只占一栏**（如 Spillway p911 左栏内的 Fig 11+Fig 12），最右子图的图题 x1 仍 < 0.55×页宽。clip 器对「一行多图」把最右子图的横向窗口右边界设成整页宽 `pw`，于是它把**邻栏正文**纳入并集；更糟的是该正文成了纵向带的上界，把子图本体（在图题上方）排除，导致并集退化（`!! … degenerate`）或串栏。**不要用「把外边界收敛到栏宽 pw/2」来自动修**——这会切掉跨栏宽的双轴图右轴（Dorado Fig 17/18 已验证回归）。正确做法：目视审计发现后**手工框定该子图**（见下）。这是 clip 器的已知边界，非 bug。

## 陈旧图排查（执行纪律）

clip 器每次加固后，**所有已产出译文的论文都要用最新 pdf_clip.py 重裁并重新编译**，否则早期 `.prep.py` 一次性裁的图会停留在旧版行为（如把单栏图当整页宽裁、把右栏正文/邻表串进来）。判据：重裁后与交付 fig 目录逐张比尺寸，差异者目视确认无截断再替换。ROE/Spillway/NetPila 三篇正是栽在这里。

## Manual overrides

`pdf_clip.py` 以 `!!` 行报告裁不出的图题。处理方式：用 PyMuPDF 直接
`page.get_pixmap(matrix=Matrix(3,3), clip=Rect(...))` 手工框定（先渲染整页低倍图目测坐标），
存为同名 png 覆盖；并在交付说明中列出手工项。

## 协议/标准类文档（doc_class == "spec"）的额外规则

`scripts/doc_class.py` 用两条独立证据把输入分成 paper（ACM/USENIX 双栏论文）与
spec（协议/标准/白皮书单栏）：单栏版式占比、章节前缀题注（`Figure 7-132  Title`）。
**paper 路径是零回归承诺区**：所有分流改动只允许在 spec 分支生效，
回归测试在 `scripts/tests/test_doc_classes.py`（合成双栏/单栏 fixture，19 项断言）。

spec 类在通用规则之外还要注意四点：

1. **图/表编号带章节前缀**。`\caption` 的自动编号会打印「图 1」而正文引用是「图 7-132」，
   两者必须一致，导言加：
   ```latex
   \renewcommand{\thefigure}{7-\arabic{figure}}   % 章号按实际章节改
   \renewcommand{\thetable}{7-\arabic{table}}
   \captionsetup{labelsep=quad}                    % 原文题注是「编号 + 空格 + 标题」无冒号
   ```
2. **表格重建 vs 位图的判据**。单元格内含 bit 刻度行、跨行合并、打勾矩阵、寄存器位域图
   → 位图裁切保留原貌；纯文字且 ≤6 列 → 重建为中文 LaTeX 表。
   寄存器密集型章节（如 PCIe 第 7 章 318 张表）一律位图，重建不可行。
3. **脚注编号全文连续**。规范脚注不按章重置（某章正文里可能就是注 2、注 3），
   重排后 `\footnote` 会从 1 开始与原文错位；在对应 `\footnote` 前用
   `\setcounter{footnote}{n-1}` 把编号钉回原文值。
4. **`\item` 的可选参数陷阱**。`\item [M.2]、[CEM]…` 会把首个方括号当成自定义标签，
   项目符号丢失、文字跑到标签位；以 `[` 开头的列表项必须整体包花括号：`\item {[M.2], …}`。
   同类保留字冲突：`\ss` 是 LaTeX 内置（德语 ß），自定义标题宏避开；
   `\checkmark` 需要 `amssymb`。
5. **三个 spec 专属门禁**（paper 类调用自行 skip）：`pdf_audit.py xrefs` 抓残留 `§` 与
   英文 `Section/Chapter/Figure N` 交叉引用；`pdf_audit.py footnotes` 比对源脚注定义数与
   `\footnote` 数及 `\setcounter` 钉回的编号；`pdf_audit.py sections` 拿 `pdf_outline.py`
   的标题树与译稿标题宏编号逐层比对，防整节漏译。译稿标题宏的参数必须以字面编号开头
   （如 `\hdB{1.1\quad 子节}`），否则 sections 门禁读不到。
6. **抽取文本的 `§` 残留**。PCI-SIG 类文档的超链接标记既出现在行首（`§ Figure 1-1`）
   也出现在编号前（`Figure§ 1-2`）；clip/inventory/numbers/outline 均已整行剔除，
   自写脚本时记得 `.replace("§", "").strip()`——只剥行首或忘记 strip 前导空格都会漏匹配。
