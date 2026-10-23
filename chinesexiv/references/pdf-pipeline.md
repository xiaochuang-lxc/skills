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
| 紧贴节标题的图把「4.1 Traffic Measurement Module」等**节标题裁进图里** | 节标题既非散文也非图题，未被当作带上界、又进了并集 | `pdf_clip.py` 用**字号**识别节标题（首行为 `\\d+(\\.\\d+)*` 且 max span size ≥10pt：真标题 ~11pt，图内数字标签 ≤6pt，页码 ~9pt），将其排除出并集并作为 figure 带上界。**不可只用「首行是数字」判定**——会吃掉树节点/坐标轴数字标签把图切碎（已验证回归） |
| paper 类表图里混入英文表题（与中文 \\caption 重复） | spec 适配时把「表裁切含题注」设成了无条件 | 题注包含仅对 **spec（allow_prefix）** 生效；paper 类 `top=cr.y1` 且 `cr` 不入候选集 |
| 竖版/超大图**静默丢 caption**（numbers 报某图号缺失、但图存在且计数器已推进） | 图太高 → `Overfull \vbox … too high` → `[H]` 浮动体被丢、caption 未排版 | 编译日志除 hbox 外**必须 grep `Overfull \vbox.*too high`**；缩小该图 width（竖版图常需 ≤0.5\linewidth）直到 vbox 归零；numbers 门禁正是靠「缺号」暴露它 |
| coverage 误报重建图/表「未包含」 | 原「Figure N」其实是表、被重建成 figure 内的 tabular；booktabs 表用描述性 `\label{tab:x}` 而非 `tab:N` | coverage 改为「裁剪 png 数 + 重建环境数 == 源数」的全局一致性判定，不再硬性要求每个 `figureN.png`/`tab:N` |
| fidelity 误报裁剪表格/图内文字 | 裁剪的表体/图内矢量文字以 block 泄漏，数字在图片里、不在 tex | fidelity 先用 `find_tables()` 排除表区，再按 ACM 惯例排除**图题上方 / 表题下方 ±200pt 带内**的块 |
| 整页零题注命中（fig/ 空、inventory 全 0、numbers vacuous） | 题注是 IEEE `Fig. N.`（句点、标签常独立成行）/ `TABLE 罗马`，而 clip/inventory/numbers 只认 ACM `Figure N:` | `doc_class.caption_style` 判 `ieee` 后三脚本自动走 IEEE 口径（仅当**无** ACM 冒号题注且有 IEEE 证据才启用，ACM 零回归）；**不再需要**手工规范化 _text.txt |
| 跨栏图（figure\*）被裁成单栏、丢右半 | figure\* 的题注文本窄且左对齐，按题注中心 x 分栏误判单栏 | ieee 下单题注行若带内矢量框同时落左右两栏→整页宽；但若另一栏有表/图题注伸入本带（其 `y1 >= floor`），则该栏框属另一资产，不判跨栏 |
| 图顶部图例/标签被切（如 KickTree Fig 1/2/10/12） | y<72 页眉阈值把图体矢量框排除出并集 | ieee 下矢量框/细线下界放宽到 y>=40；文字块仍按 72 过滤页眉 |
| 本图混入上一张图残留（Fig 4 混 Fig 3、Fig 8 混 Fig 7） | 带顶落到页顶 | ieee 下已裁图体（clipped_bodies）作为后续图带上界 |
| 表位图底部混入正文/参考文献首行（KickTree 表 4/5） | 手工框 y1 估到散文行 | y1 取「表体最后一条矢量横线 y1 + 少量 pad」，且必须 < 下一条散文块 y0；用 `get_drawings()` 的横线簇定位，勿目测 |
| `find_tables()` 对无边框 booktabs 表返回空 | 无线框 | 不要依赖 find_tables 定位表体；用题注 y + get_drawings 横线簇 |
| fidelity 报首页基金/稿件脚注缺数字 | 首页脚注含 Grant 号与单位邮编，属被指纹的散文块 | 译稿必须译出该脚注（含全部 Grant 号与邮编），否则 fidelity SUSPECT |
| paper 类表图裁入下方正文段落（FlowTurbo 表 3 裁入 §5.3/5.4/5.5 全部正文） | `table_stop()` 只认 solid box 和 >10pt 间隙，ACM 表与正文间无 solid box 且间隙<10pt 时 prose 被误纳入表体 | `table_stop()` 新增 prose 检测：已积累表内容后，遇到宽度≥0.30×页宽且平均行长≥40 的块即判定为正文、停止扩展 |
| paper 类表图底部残留英文表题（FlowTurbo 表 2 底部出现 "Table 3: Resource utilization…"） | caption block bbox 因 PDF 解析原因延伸至表数据区下方，或 caption 实际位于表下方，导致 `cr.y1` 不可靠 | paper 类表裁切新增二次防护：扫描候选块中是否含 caption-like 文本（匹配 `CAP_RE`），若有则以其 y0 收紧 crop 下界 |
| 陈旧图未重裁导致已交付译文带旧版 clip bug（ROE/Spillway/NetPila/FlowTurbo 均曾发生） | clip 器加固后未重裁已产出译文的论文，早期一次性裁的图停留在旧版行为 | P6 验收新增⑥陈旧图检查（强制）：clip 器改动后必须重裁所有已产出译文的论文并逐张目视比对，差异者目视确认无截断再替换、重编译 |

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

## IEEE / 类 IEEE 论文（caption_style == "ieee"）

`doc_class.caption_style(pdf,start,end)` 在 paper 类内部再分 `acm` / `ieee`：
**仅当完全没有 ACM 冒号题注、且存在 `Fig. N.` 独立行或 `TABLE 罗马` 行**才判 ieee，
否则一律 acm——这是 paper 路径零回归的开关。spec 类返回 `spec` 不受影响。

ieee 下已自动化的部分（勿再手工绕）：
- `pdf_clip` 识别 `Fig. N.`（两行式 fullmatch / 单行块 `Fig. N. 大写标题`）与 `TABLE 罗马`；
  正文交叉引用（`Fig. 8 shows…` 同行小写动词、多行）不会命中。
- 跨栏图整页宽、y>=40 矢量框并入、已裁图体作带顶（见上表）。
- `pdf_inventory` / `pdf_audit numbers` 按集合语义收 IEEE 题注（正文交叉引用只引用
  已存在图号，不污染集合），门禁对 IEEE 真实非空。
- `pdf_audit fidelity` 的图/表带排除同时认 IEEE 题注。

ieee 下仍需手工的部分：
- **表格**：clip 器对 ieee 只把表题注用于带上界、**不产出 tableN.png**（booktabs 无边框,
  自动表体不可靠）。表格用位图手工框定（y1 用最后一条矢量横线）或重建为中文 LaTeX 表，
  并把手工 rect 追加进 `fig/_clip_manifest.json`（fidelity/structure 靠它扣除表区）。
- **首页脚注**：稿件日期 + 基金 Grant 号 + 单位邮编会被 fidelity 指纹，必须译出。
- **排版**：`article` 类摘要标题需 `\renewcommand{\abstractname}{摘要}`；作者行人数多
  必须拆行（否则溢出右 margin）；算法用非浮动 tabular 时 `\multicolumn` 表头行末尾必须
  有 `\\`，且不要把 `\label` 放在 tabular 行内（会未定义引用/Extra alignment tab）。

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
