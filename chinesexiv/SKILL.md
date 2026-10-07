---
name: chinesexiv
description: 把论文自动翻译为中文 PDF 的 ChineseXiv skill。触发后按本 skill 步骤顺序直接执行，勿长篇规划。用户提供论文标题或 arXiv ID、说「翻译论文」「我想读中文版」时立即使用；用户只提供 PDF（单篇或整本会议论文集、无 arXiv 源码）时改走 PDF 管线（第零步路由 + 「PDF 输入管线」一节）。支持本地 xelatex 与在线编译双引擎、英文原文 _zh 副本对照、多篇并行处理。每篇论文文件夹同时保留英文原文 PDF 与中文译文 PDF。无需用户手动操作。
---

# ChineseXiv：论文中文翻译（arXiv 源码 / PDF 双路径）

**目标：** 将指定论文译为中文并编译得到 PDF。输入是 arXiv LaTeX 源码时走第一至四步；输入只有 PDF 时走「PDF 输入管线」。

**流程：** 须严格按下文「第一步」至「第四步」顺序执行，不得擅自省略、合并或调换步骤。

**交互：** 仅在论文 ID 无法确定、检索结果存在多个需用户择一才可向用户提问；其余情况一律无中断的执行得到最终翻译后的PDF。

**翻译：** 翻译全部由当前对话模型自身完成，严禁使用外部翻译工具以及下载已有的翻译版本。

---

## 第零步：判断输入类型（路由）

- 用户给了 arXiv ID/URL，或能检索到 arXiv 源码 → **源码管线**：第一步至第四步。
- 用户只给了 PDF（单篇论文 PDF、或整本会议论文集），或该论文无 arXiv 预印本（如仅在 ACM DL/IEEE 出版）→ **PDF 管线**：见下文「PDF 输入管线」。
- 整本论文集先问清/检索出要哪几篇；若用户已列标题则直接定位，不额外提问。

---

## PDF 输入管线（无 arXiv 源码）

**产出与源码管线一致**：`$OUTPUT_DIR/` 内含英文原文子 PDF、`$PDF_NAME_ZH.pdf`、`source/main_zh.tex` + `source/fig/` + `source/refs.tex`。命名约定同第二步（`$PARENT/$PAPER_ID-$PDF_NAME_ZH`，`$PAPER_ID` 用 DOI 后缀或短名）。

**P1 定位页码。** 整本论文集先跑 `scripts/pdf_locate.py PDF --out manifest.json` 得到每篇 `pdf_start/pdf_end/doi/title`；单篇 PDF 跳过此步（1..末页）。

**P2 预处理。** 对每篇跑：

先跑 `scripts/doc_class.py PDF START END` 判定文档类别（`paper` = ACM/USENIX 双栏论文，
`spec` = 协议/标准/白皮书单栏）。类别决定题注正则、分栏策略与验收口径的分流；
**paper 路径是零回归承诺区**，行为差异与 spec 专属规则见 `references/pdf-pipeline.md`
末节，回归测试 `scripts/tests/test_doc_classes.py`（改任何脚本后必跑）。

```bash
python3 {SKILL_DIR}/scripts/pdf_prep.py "$PDF" START END "$OUTPUT_DIR" "$PDF_NAME_EN_STEM"
```

它产出 `_text.txt`（栏感知阅读序）、`source/fig/*.png`（图与表）、英文子 PDF、`source/refs.tex`（数字键 rN 的 thebibliography）。**stdout 中以 `!!` 开头的行是裁不出的图题，必须逐条手工处理后才能继续**（方法见 `references/pdf-pipeline.md` 的 Manual overrides）。

**P3 裁切目视审计（强制）。** 跑 `scripts/pdf_audit.py sheet "$OUTPUT_DIR/source/fig" /tmp/sheet` 并用 Read 逐张过目：截断、串图、英文图题残留、表格混入只能这样发现。发现问题先修裁切（重跑 pdf_prep 或手工框定），**不要带着坏图进翻译**。

**P4 撰写 `source/main_zh.tex`。** 单栏重排、`[H]` 钉死浮动体、**一图一环境一表一环境且按原文顺序**（保证译文图号=原文图号）；导言固定件见 `references/pdf-pipeline.md`。**动笔前必须先跑 `scripts/pdf_inventory.py "$OUTPUT_DIR/_text.txt" --out "$OUTPUT_DIR/_inventory.json"`** 得到编号公式/算法/定理/引理/定义/图表清单（PDF 抽取会把显示公式打成 glyph 碎片，不列清单必丢公式）；翻译时逐条覆盖，公式用 `equation` 环境保持原编号顺序、算法用非浮动 tabular 逐行呈现。大文件分块写（Write 首段 + SearchReplace 以 `\end{document}` 为锚追加）。引用用 `\cite{rN}`，末尾 `\input{refs}`。
**同一本书分多批翻译时**（规范/标准类常见），在父目录维护 `glossary.md`（术语 → 中译，一行一条）：
每批动笔前先读，结束后把新术语追加进去；否则第 2 批的「虚通道」到第 7 批会漂成「虚拟通道」。

**P5 编译。** 同第四步：`compile.py "$OUTPUT_DIR/source" main_zh.tex "$OUTPUT_DIR/$PDF_NAME_ZH.pdf" --engine auto`；编译日志里 `Overfull \hbox` 与 `Overfull \vbox` 都必须归零（作者行拆行、`\emergencystretch`；竖版/超大图会因 `Overfull \vbox too high` 被 `[H]` 静默丢弃 caption、导致 numbers 报缺号，须缩小该图 width）。

**P6 验收（强制，五项全过才交付）。** ① `scripts/pdf_audit.py coverage "$WORK_DIR/main_zh.tex" "$OUTPUT_DIR/_inventory.json"` 必须 COVERAGE OK（公式/算法/定理/图/表无遗漏，MISSING 列表为空）；② `scripts/pdf_audit.py structure "$PDF" START END "$WORK_DIR/main_zh.tex"` 必须 STRUCTURE OK（译稿段落数 ≥ 原文散文块数的 90%，防整段合并/丢失）；③ `scripts/pdf_audit.py fidelity "$PDF" START END "$WORK_DIR/main_zh.tex"` 必须 FIDELITY OK——它对每个含数字的原文散文块做「数字指纹」覆盖率检查（剔除引用编号、年份、节号、版权页），**段数对但内容被合并/丢句子时只有它能发现**，SUSPECT 列表逐条回原文补译；④ `scripts/pdf_audit.py numbers "$OUTPUT_DIR/$PDF_NAME_ZH.pdf" "$OUTPUT_DIR/_text.txt"` 必须全 OK；⑤ 渲染抽查并排图页与表格页目视。
**spec 类追加三项门禁**（paper 类调用会自行 skip，两类互不影响）：
⑥ `pdf_audit.py xrefs "$WORK_DIR/main_zh.tex"` 必须 XREFS OK——残留 `§` 或英文
`Section/Chapter/Figure/Table N` 都说明该处交叉引用没译成「第 N 节 / 图 N」；
⑦ `pdf_audit.py footnotes "$PDF" START END "$WORK_DIR/main_zh.tex"` 必须 FOOTNOTES OK——
源脚注定义数 == `\footnote` 数，且 `\setcounter{footnote}{k}` 钉回的编号落在源编号集合内；
⑧ `pdf_audit.py sections "$PDF" START END "$WORK_DIR/main_zh.tex"` 必须 SECTIONS OK——
源标题树（`pdf_outline.py` 提取）的每个编号都出现在译稿标题宏里，防整节漏译。
**门禁判读注意**：`numbers` / `structure` / `inventory` 现在按类别分流；看到
`WARN ... vacuous` 或 `WARN inventory all-zero` **不是通过**，是正则没吃到该文档的题注格式，
必须先查格式（无冒号？带章节前缀？）再决定是否交付；spec 类 structure 会额外打印
`[spec metric]` 行给出列表项/逻辑段两个计数。

**保真度声明（必须告知用户）：** PDF 管线产出是「单栏重排的可读中文译本」，不复刻原双栏版式；图表为位图裁切（表格可重建为中文 LaTeX 表），这是 PDF→LaTeX 路线的固有降级。

---

## 第一步：确定论文 ID

- arXiv URL/ID → 直接提取 ID
- 论文标题 → 搜索 arXiv / 网页查找 ID；找不到时给出候选让用户确认

---

## 第二步：获取源码

```bash
python3 {SKILL_DIR}/scripts/download.py "{PAPER_ID}" "$OUTPUT_DIR/source"
```

`download.py` 一步完成：下载源码 → 解压 → 递归查找 `.tex` → 定位主文件 → 提取标题 → 把主文件以及它通过 `\input{}` / `\include{}` 引用的子 `.tex` 文件都复制为 `_zh.tex` 副本，并把 zh 主文件里的 input 引用一并改写到 `_zh` 版本 → **直接下载 arXiv 官方编译好的英文 PDF**（按英文标题命名）落在 `source/` 同级目录，稍后与中文译稿 PDF 并排存放。

### `OUTPUT_DIR` 的命名约定

用户通常给出**父目录**（例如 `~/papers`、`~/projects/paper-reading`）。约定每篇论文落在一个**独立子目录**下，命名为 `{paperid}-{中文标题}`，目录里**同时**放英文原文 PDF 与中文译文 PDF：

```
~/projects/paper-reading/
├── 1706.03762-你所需要的只是Attention/
│   ├── source/
│   ├── Attention Is All You Need.pdf        ← 英文原文（arXiv 官方 PDF，download.py 自动下载）
│   └── 你所需要的只是Attention.pdf            ← 中文译文（compile.py 编译）
└── 2605.17792-HydroAgent_基于模拟器驱动…/
    ├── source/
    ├── HydroAgent_Bridging the Gap….pdf      ← 英文原文
    └── HydroAgent_基于模拟器驱动….pdf          ← 中文译文
```

由于中文标题在翻译完成前不可知，按下列两阶段处理：

1. **下载阶段**：先用 `$OUTPUT_DIR = $PARENT/$PAPER_ID` 占位（**只用 arXiv ID，无标题后缀**）。
2. **翻译完成、确定 `\title{}` 中文标题后**：把整个目录从 `$PARENT/$PAPER_ID` 重命名为 `$PARENT/$PAPER_ID-$PDF_NAME_ZH`，再调用 `compile.py` 把 PDF 写到新目录里。`$PDF_NAME_ZH` **不是** `\title{}` 的原样，而是把 `\title{}` 里的全角 `：` 替换为 `_`（详见第三步「文件系统命名」），例如 `\title{HydroAgent：基于模拟器驱动……}` → `$PDF_NAME_ZH=HydroAgent_基于模拟器驱动……`。

   ```bash
   mv "$PARENT/$PAPER_ID" "$PARENT/$PAPER_ID-$PDF_NAME_ZH"
   OUTPUT_DIR="$PARENT/$PAPER_ID-$PDF_NAME_ZH"
   WORK_DIR="$OUTPUT_DIR/source"
   ```

若用户只翻一篇论文，没有「父目录」语义（例如直接说「放到 `~/Desktop`」），保持 `$OUTPUT_DIR = ~/Desktop/$PAPER_ID-$PDF_NAME_ZH` 即可。**不要把多篇论文的 `source/` 直接堆在同一个父目录里**——会互相覆盖。

源码统一落在 `$OUTPUT_DIR/source/`（不再使用 `.tmp_arxiv` 之类的临时名）。

无源码（仅 PDF）则告知用户跳过。

脚本向 stdout 输出六行，格式如下：
```
WORK_DIR=<源码目录绝对路径，即 $OUTPUT_DIR/source>
MAIN_TEX=<英文原始主文件相对路径，只读快照>
MAIN_TEX_ZH=<供翻译的中文主文件相对路径（download.py 已自动复制好）>
PDF_NAME=<论文英文标题（仅供生成备用名）>
PDF_NAME_EN=<英文原文 PDF 的跨平台安全文件名，冒号等已替换为 _>
PDF_EN=<已下载的英文 PDF 绝对路径；若没下到则为空字符串>
```

`MAIN_TEX` 永远是英文原文，**永远不要修改**；翻译只动 `MAIN_TEX_ZH` 及其 `_zh` 子文件。两者并列存放，方便对照。

### 英文原文 PDF（强制：必须与中文译文同在一个文件夹）

每个论文文件夹里**必须**同时有「英文原文 PDF」和「中文译文 PDF」，缺一不可。英文原文 PDF 的获取分两条路，**按优先级**走：

1. **首选——直接下载 arXiv 官方 PDF（download.py 已自动完成）。** arXiv 已编译好的 PDF 是作者最终排版、最忠于原貌的版本，比本地重编英文源码更稳更快。`download.py` 会把它按 `PDF_NAME_EN` 命名，落在 `source/` 同级（即 `$OUTPUT_DIR`）。成功时 `PDF_EN` 是该文件的绝对路径。
2. **回落——本地编译英文源码（仅当 `PDF_EN` 为空时）。** 极少数论文官方 PDF 取不到，此时在第四步（目录已重命名、工具链已就绪）顺带用 `compile.py` 编译只读的英文 `$MAIN_TEX`：

   ```bash
   # 仅当 download.py 的 PDF_EN 为空时执行；MAIN_TEX 无中文，compile.py 不会注入 CJK，按原貌编译
   python3 {SKILL_DIR}/scripts/compile.py "$WORK_DIR" "$MAIN_TEX" "$OUTPUT_DIR/$PDF_NAME_EN.pdf" --engine auto
   ```

英文 PDF 命名约定 `PDF_NAME_EN`（`download.py` 已按此实现，跨平台/网盘/Git/URL 均安全）：以英文标题为基础，**半角/全角冒号 `:`/`：` → `_`**（与中文目录命名的方法名分隔同构，如 `GeoGround: ...` → `GeoGround_...`），**空格 → `_`**（不留空格，免去 shell/URL 转义），标题里**原有的连字符 `-` 保留**（如 `Vision-Language`，与代表空格的 `_` 区分，便于还原原题），其余 `<>"|?*` 等不安全字符 → `_`。最终形如 `GeoGround_A_Unified_Large_Vision-Language_Model_for_Remote_Sensing_Visual_Grounding.pdf`，与中文 PDF `GeoGround_面向遥感视觉定位的统一大型视觉-语言模型.pdf` 同享 `GeoGround_` 前缀、一眼成对；两份文件名天然以语言区分原文与译文。

> 收尾自检：进入第四步「清理」前，**务必确认** `$OUTPUT_DIR` 下既有 `$PDF_NAME_EN.pdf`（英文原文）又有 `$PDF_NAME_ZH.pdf`（中文译文），**且两者内容范围一致**（若中文版取消注释纳入了补充材料/附录，英文也必须是含补充材料的版本，见第三步）。只有中文、缺英文（或反之）、或中英内容范围不一致，都算未完成。

---

## 第三步：翻译

由当前**对话模型**直接对 `$WORK_DIR/$MAIN_TEX_ZH`（以及它 input 进来的 `_zh` 子文件）进行翻译修改。`$MAIN_TEX` 是英文只读快照，**永远不要修改**。按以下规则翻译：

- **翻译范围：** 默认翻译全文，包括 `\appendix` 之后的附录内容。用户明确要求「只翻正文」「不翻附录」时，才在 `\appendix` 之前停止翻译。**留意源码里「写好却被 `%` 注释掉的补充材料/附录」**（arXiv 版常见：作者把 supplementary 注释掉以压缩正文页数，`download.py` 仍会把它复制成 `_zh` 子文件）——这类内容 arXiv 官方英文 PDF 往往不含，但源码既已写好，可在用户要求或同意时取消注释、一并翻译编译，让中文版比 arXiv PDF 更完整；取消注释前先确认其引用的图表资产（`fig/` 等目录下）齐全，再编译。**关键：中文版一旦纳入补充材料，英文 PDF 也必须同步含补充材料才能逐页对照** —— 复制英文主文件为 `main_en.tex`（**不动只读的 `$MAIN_TEX`**），在副本里取消同样的 `\input{...}`，再用 `compile.py` 编译覆盖原英文 PDF。
- **必须翻译：** 正文叙述、摘要、图表标题、列表项、脚注中的描述文本、代码块中的注释；附录 `tcolorbox` / `lstlisting` / prompt example 里的**自然语言提示词、角色说明、步骤说明、动作说明、表头说明**也要翻译（这是论文内容，不是“代码本体”）；**作者/机构区的机构名**直接译为全中文（如「斯坦福大学」），不保留英文原文或中英对照；**描述性方法名/模块名**（如「自适应检索模块（Adaptive Retrieval Module, ARM）」）也要中译，按下方「术语首次出现规则」给出中英对照。
- **图表前缀与图内文字：** 中文 PDF 中 LaTeX 自动生成或正文引用里的 `Figure` / `Fig.` / `Table` / `Tab.` 前缀统一本地化为「图」「表」
  **关键：这些 `\renewcommand` 必须放进 `\AtBeginDocument`**，直接写在导言区会被 `babel` 的 `english` 选项在 `\begin{document}` 时重置回英文（症状：正文 `\ref` 已经是「图 1」，caption 却仍打印 "Figure 1"）：

  ```latex
  \AtBeginDocument{%
    \renewcommand{\figurename}{图}%
    \renewcommand{\tablename}{表}%
    \renewcommand{\lstlistingname}{代码}%
    \renewcommand{\refname}{参考文献}%
  }
  ```

  同理，若模板把 `Abstract` 标题**硬编码**在 `abstract` 环境里（如 `colm2024_conference.sty`），`\renewcommand{\abstractname}` 无效，需用 `\renewenvironment{abstract}` 整体覆盖为「摘要」。但图片、截图、外部 PDF/矢量资产内部已经渲染好的英文标注、坐标轴、界面文字默认不改，除非可在可编辑源码中自然修改且不破坏版面。
- **保留不翻：** 数学环境、LaTeX 命令、`\cite{}`/`\ref{}`/`\label{}`、图片路径、URL、`.bib`、**代码本体中的标识符 / JSON key / API action name / XML tag / 占位符**（如 `action_type`、`open_app`、`<tool_call>`、`<instruction_here>`）、**人名**、**专有模型名**（GPT-4、LLaMA、Qwen、DeepSeek 等已成符号的型号）、**专有数据集/基准名**（ImageNet、MMLU、GSM8K 等）。不要把整段 prompt 模板误判为代码而原样保留；只保留其中必须机器可读或示例结构相关的 token。
- **不要新增字体修饰：** 严禁额外添加 `\textit{}`、`\textbf{}`、`\emph{}` 等格式命令——只在原文已存在时按位置保留。作者/机构区不写英文机构对照；正文术语对照括号里的英文一律用 \textbf{正体（plain）}，不要套 `\textit{}`；括号内的英文只是为方便对照，不属于「需要强调」的内容。
- **专有名词：** Transformer、Softmax、Token、Attention、Self-Attention、Multi-Head Attention、Scaled Dot-Product Attention 等已通用化的学术术语**严格保留英文**，不要硬译为「转换器 / 注意力 / 自注意力 / 多头注意力」等。复合词同样保留：`Multi-Head Self-Attention`、`Restricted Self-Attention`、`Encoder Self-Attention` 等都不要拆译。其它领域的同类约定俗成术语（CNN、RNN、LSTM、Embedding、Token、Logits、Softmax、Dropout、BLEU 等）同理。
- **术语首次出现规则（重要）：** 全文术语、符号、代号需统一；非通用新名词、新术语、新概念在**首次出现**时给出清晰说明。
  - 反复出现（≥2 次）的较长词组，在**首次出现**时写作「中文全称（English Full Name, ABBR）」，例如「灾害行动响应智能体（Disaster Operational Response Agent, DORA）」，之后全文统一用缩写 `ABBR` 或中文简称；
  - 全文仅出现一次的，直接用中文全称即可，必要时在括号中附英文全称（不加缩写）；
  - **摘要与正文各自独立统计**：同一术语若在摘要和正文中都是首次出现，两处都要分别注明完整定义，确保摘要可以独立阅读。
  - 仅有缩写而无英文全称的写法（例如「MCP 库」「SAR 影像」）必须替换为定义形式。
- **标题要求：** `\title{}` 须改为自然中文题名，不保留英文原题或中英并列。**标点忠于原文**——原标题里的 `:` 翻成中文标准的全角 `：`（中文排版规范），不要省略也不要替换为 `-`。**若原标题以专有方法名/系统名/产品名领起**（如 `HydroAgent: ...`、`DORA: ...`、`LLaMA-Factory: ...`），中文 `\title{}` 必须保留该专有名词作为前缀，写作「专有名（英文原样）：中文副标题」，例如 `HydroAgent：基于模拟器驱动强化学习……`；不要把专有名翻成中文，也不要丢掉。
- **文件系统命名（与 `\title{}` 解耦）：** PDF 内部 `\title{}` 遵循上一条；但**目录名与 PDF 文件名要替换非 ASCII 标点**以保证跨平台（Windows、网盘、Git 都不接受裸 `:`/`：`）。采用两层分隔：
  - 外层 `-`：arxiv-ID ↔ 标题主体，例如 `2605.17792-HydroAgent_...`
  - 内层 `_`：英文方法名 ↔ 中文副标题，**替换 `\title{}` 中的全角 `：`**，例如 `HydroAgent_基于模拟器驱动…`
  - 完整范例：`2605.17792-HydroAgent_基于模拟器驱动强化学习缩小前沿LLM与人类专家在水文模型率定中的差距/` 内含同名 `.pdf`。
  - 两层分隔的目的是视觉上区分语义层级（ID/方法名/副标题）；全用 `-` 会出现 `ID-Method-Subtitle` 三段同形分隔，边界不清。`_` 与 `-` 都全平台安全。
  - 若原标题**没有**专有方法名前缀（纯描述性中文标题），直接 `$PAPER_ID-$PDF_NAME_ZH` 即可，不需要内层 `_`。
- **多篇处理：** 多篇论文可以分别处理；只有在用户**明确要求**并行委派时，才开启多个 subagent，否则直接顺序完成。

译后必须做自检（默认 full 模式扫描全文，扫描的是中文翻译目标文件）：

```bash
python3 {SKILL_DIR}/scripts/inspect_tex.py scan "$WORK_DIR" "$MAIN_TEX_ZH" full
```

若用户明确要求「只翻正文」，则改为：

```bash
python3 {SKILL_DIR}/scripts/inspect_tex.py scan "$WORK_DIR" "$MAIN_TEX_ZH" body
```

脚本会输出 `SUSPECT_COUNT=<数字>` 以及若干 `SUSPECT=<文件>:<行号>:<片段>`。
- 只要 `SUSPECT_COUNT` 非 0，就必须逐条回到对应位置进行翻译；
- 只有 `SUSPECT_COUNT=0`，或剩余项明确属于「保留不翻」范围时，才可进入第四步。
- **`SUSPECT_COUNT` 在真实论文上基本不可能为 0，不要反复尝试把它压到 0**：扫描器剥掉命令名后**不剥花括号内容**，所以 `\usepackage{colm2024_conference}`、`\setCJKmainfont{Noto Serif CJK SC}` 这类行必然被计为可疑；表格里的模型名（`Qwen2.5-72B-Instruct`）、基准名（`MMLU-Pro`）、语言代码（`en, es, fr`）、机器可读 token（`{query}`、`<|im_end|>`）同理。**正确做法是逐条核对后分类说明**（多少条属宏包/字体配置、多少条属模型名与基准名、多少条属机器 token），而不是追求数字归零。

---

## 第四步：编译与清理

**目录最终命名**：在编译前，按第二步的命名约定，把 `$OUTPUT_DIR` 从 `$PARENT/$PAPER_ID` 重命名为 `$PARENT/$PAPER_ID-$PDF_NAME_ZH`，使整篇论文（含 `source/` 子目录、第二步已下载的英文原文 PDF）都落在最终目录里。`$PDF_NAME_ZH` 基于翻译后的 `\title{}` 自然命名，与 `\title{}` 一致或更精炼。最终中文 PDF 直接落在 `$OUTPUT_DIR/$PDF_NAME_ZH.pdf`，与 `source/`、英文原文 PDF 同级。第二步下载的 `$PDF_NAME_EN.pdf` 在 `$OUTPUT_DIR` 内，整体 `mv` 时会自动跟着搬到最终目录，无需单独处理。

```bash
python3 {SKILL_DIR}/scripts/compile.py "$WORK_DIR" "$MAIN_TEX_ZH" "$OUTPUT_DIR/$PDF_NAME_ZH.pdf" --engine auto
```

**英文原文 PDF 兜底**：若第二步 `PDF_EN` 为空（官方 PDF 没下到），在这里顺带补一份英文 PDF，确保最终目录里中英两份都在：

```bash
[ -z "$PDF_EN" ] && python3 {SKILL_DIR}/scripts/compile.py "$WORK_DIR" "$MAIN_TEX" "$OUTPUT_DIR/$PDF_NAME_EN.pdf" --engine auto
```

**`--engine` 选项**（默认 `auto`）：
- `auto`：先检测本地是否装有 `xelatex`，装了就用本地编译；未装则回落到在线服务。**首选**。
- `local`：强制本地 `xelatex` 编译；未装 `xelatex` 直接报错。适合环境齐全 + 想完全离线的场景。
- `online`：强制走 `latex.ytotech.com` 在线编译。适合本地 TeX 环境缺包、或者想保留旧行为。

用户可以在调用时通过自然语言指定（例如「用在线编译」「强制本地编译」），否则一律传 `--engine auto`。

`compile.py` 会统一完成以下编译前处理（两种引擎共用）：
- 默认使用 `xelatex` + `xeCJK` 编译栈；若检测到中文且主文件尚无 CJK 支持，自动注入 `fontspec` / `xeCJK` / `\setCJKmainfont{Noto Serif CJK SC}`；
- 自动注释掉与 Unicode 编译栈冲突的 `fontenc` / `inputenc`；
- 自动识别 `bibtex` / `biber` / 已内置 `.bbl` 的情况；
- 自动忽略常见编译中间文件、`build/` 子目录以及未被源码引用的游离 PDF（在线引擎下避免把无关产物上传；本地引擎下避免污染源码目录）。

编译失败时：读取 stderr 中的错误日志，参考 `references/compile-errors.md` 修复源码，重新编译（最多重试 2 次）。

**编译成功不代表排版通过**：xelatex exit 0 但日志里 `Overfull \hbox` 经常是中英换算带来的表格/段落溢出，目视才能发现。**强制**执行下一步「表格溢出扫描」。

**本地手动重编（应急）：** `source/build/` 子目录是本地 xelatex 中间产物的约定输出位置。手动重编命令：

```bash
cd "$OUTPUT_DIR/source"
xelatex -output-directory=build "$MAIN_TEX_ZH"
BIBINPUTS=".:$BIBINPUTS" bibtex "build/${MAIN_TEX_ZH%.tex}"
xelatex -output-directory=build "$MAIN_TEX_ZH"
xelatex -output-directory=build "$MAIN_TEX_ZH"
cp "build/${MAIN_TEX_ZH%.tex}.pdf" "../$PDF_NAME_ZH.pdf"
```

### 表格溢出扫描（强制，**先于目视**做）

中文方块字宽度约为英文比例字体的 1.5–2 倍。原作按英文宽度调好的 `\small / \tabcolsep` 在中文下普遍宽度溢出 5–20%，**不修就一定出现表格压到对面栏中文上**。

```bash
grep -E "Overfull \\\\hbox \([0-9]+\.[0-9]+pt" "$WORK_DIR/build/${MAIN_TEX_ZH%.tex}.log" \
    | awk -F'[()]' '$2+0 > 5 {print}'
```

每条 `Overfull \hbox (XX.XXpt too wide) in paragraph at lines AAA--BBB`：

1. 把 `AAA--BBB` 行号区间映射到 `$MAIN_TEX_ZH` 里的某个外层 `\begin{tabular}` 块（注意：行首才是外层；带 `[c]{@{}c@{}}` 出现在行中的是 `\makecell` 内嵌表头，**不要包**）。
2. 用 `\resizebox{\linewidth}{!}{ ... }` 把整个外层 `\begin{tabular}...\end{tabular}` 块包住。`\linewidth` 在 `table` 里等于栏宽、在 `table*` 里等于页宽，**一段代码窄表宽表通吃**。
3. 重新编译。第一轮过后 `> 5pt` 的 Overfull 应该接近归零。

为什么是 `\resizebox{\linewidth}` 而不是「全文 `\scriptsize`」「手工调列宽」：它**只对真正超宽的表起作用、按比例保留作者意图、且小表不被强行拉宽**——可以稳定地批量自动化，不必逐表手工权衡。完整方法论与边界情况见 `references/table-overflow.md`。

剩余「溢出 > 20%」或「`\resizebox` 后字号过小」的少数情况，按 `references/table-overflow.md` 的二级手段顺序处理（先压 `\tabcolsep`，再压 `\arraystretch`，再精简表头，最后才考虑横版或拆表）。

### 排版自检（强制）

编译成功后**必须**渲染至少首页与含「作者块」「宽表格」「wrapfigure」的页面，确认中文版排版未崩坏。**不能凭借** exit code 0 就认定编译成功——CJK 与英文模板互动经常导致内容溢出页边距、文字相互重叠这类**仅渲染才能看出来的问题**。

```python
import fitz  # PyMuPDF
doc = fitz.open("$OUTPUT_DIR/$PDF_NAME_ZH.pdf")
for i in [0, ...]:  # 首页必看；含作者块、长 caption、多列表格的页都要看
    doc[i].get_pixmap(dpi=200).save(f"/tmp/check_p{i+1}.png")
```

然后用 Read 工具把这几张 PNG 实际过一遍眼睛，确认：

- [ ] **作者块** 没有溢出右边距，且作者姓名保留英文/拼音、机构只保留中文译名（不写中英对照）；原作 5 个名字 + `\quad` 一行的排版常常溢出，按 `references/author-block.md` 调整。
- [ ] **多列表格** 没有任何单元格内文字被压成竖排、数字互相粘连或与边框重叠（中文字符高且方，原作 `m{1.10cm}` / 13 列 benchmark 表在中译后多半装不下；日志无严重 Overfull 也可能视觉失败，按 `references/table-overflow.md` 的“视觉失败但日志干净”范式处理：**先试竖版紧凑方案并渲染确认**，只有竖版仍不可读或字号低于底线时，才用 `pdflscape` 横向页）。
- [ ] **wrapfigure / wraptable / sidefig** 没有被切断、没有与正文或相邻 figure 重叠；若 wraptable 与右侧图/双栏浮动互相压住，优先改为普通 `table` 或移动浮动体，不要硬留 wrap。
- [ ] **tcolorbox / lstlisting / prompt example** 内容在框内完整可读；自然语言提示词已经翻译，JSON key / XML tag / placeholder 等机器可读 token 保留；统一使用 `promptstyle`，避免每个框各写一套选项。
- [ ] **图注与表注** 完整可读，加粗段没断行到奇怪位置；LaTeX 自动前缀已本地化为「图」「表」，图片资产内部英文按上方边界保留。

发现问题就回到译稿上调整 LaTeX 结构（不是改翻译文字），然后重编。直到目视确认没有崩坏，才算「编译成功」。

### 清理中间产物

编译并目视确认后，再清理（删除 `source/build/` 与 inspect 临时文件，保留英文原文与翻译稿源码以便对照与手动重编）。**清理前最后确认 `$OUTPUT_DIR` 下中英两份 PDF 都在**（`$PDF_NAME_EN.pdf` + `$PDF_NAME_ZH.pdf`）：

```bash
python3 {SKILL_DIR}/scripts/cleanup.py "$OUTPUT_DIR"
```

cleanup.py **只清 `build/` 子目录内的中间产物**，不动 `source/` 根目录的任何文件——很多 arXiv 源码会直接附带预生成的 `main.bbl`（论文没发 `.bib`），这种 `.bbl` 属于原始源码，删了下次重编会出现一堆 `??`。

多篇论文时，所有论文都完成 PDF 编译并目视确认后再进行中间文件清理。

最后告知用户：
- 中文译文 PDF：`$OUTPUT_DIR/$PDF_NAME_ZH.pdf`
- 英文原文 PDF：`$OUTPUT_DIR/$PDF_NAME_EN.pdf`（arXiv 官方 PDF；个别论文取不到时为本地编译英文源码所得）
- 源码目录：`$OUTPUT_DIR/source/`（含英文原文 + `_zh.tex` 中文译稿，可手动重编）

---

## 参考文件
- `references/pdf-pipeline.md`：**PDF 输入管线的全部规则**——失败模式→修复规则对照表（裁切截断/串图/表格方向/页眉页码/参考文献转义/图号错位）、main_zh.tex 重建规范、验收清单、手工框定方法。**输入是 PDF 时先读这个。**
- `references/table-overflow.md`：**表格与中文重叠的诊断 + 修复范式**——为什么不能"一刀切缩小所有表"、怎么用 `Overfull \hbox` 日志精确定位、怎么用 `\resizebox{\linewidth}{!}{...}` 批量修、二级手段（`\tabcolsep` / `\arraystretch` / 表头精简 / 横版 / 拆表）顺序与边界。**每篇必跑的最后一道工序，读这个。**
- `references/framed-content.md`：**附录里 `tcolorbox`/`lstlisting` 的诊断 + 排版基线**——为什么中文长行会冲出框右边、为什么默认 box 看起来很糙、preamble 里 `\lstset{breaklines=true}` + `\tcbset{promptstyle/.style={...}}` 一处统一所有 box 风格、批量把 inline 选项压成 `promptstyle` 的脚本。**论文有 GPT 提示词/JSON 模板/对话样例附录时读这个。**
- `references/compile-errors.md`：编译常见错误、CJK 排版陷阱（宽表挤压、wrapfigure caption 溢出、`.bbl` 误删等）及修复方法。
- `references/author-block.md`：作者/机构区的排版与译名规范（作者姓名保留英文/拼音、机构只保留中文译名、`\textit` 禁用规则、「全国/国家重点实验室」译法、**作者名行过长必须默认拆行**）。翻译机构/作者块前先读这个。
