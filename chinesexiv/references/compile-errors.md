# 编译错误速查

## 常见错误与修复

**字体未找到** `Font "XXX" not found`
→ 请求的 CJK 字体在远程服务器上不存在。改用已确认可用的字体：`Noto Serif CJK SC`（已在 latex.ytotech.com 验证）。

**宏包冲突**（`fontenc` 或 `inputenc`）
→ 注释掉 `\usepackage[T1]{fontenc}` 和 `\usepackage[utf8]{inputenc}`——XeLaTeX / LuaLaTeX 的 Unicode 编译栈原生支持 UTF-8，通常不需要这两个包。

**宏重复定义** `LaTeX Error: Command \xxx already defined`
→ 常见于为中文支持引入 `luatexja` 后，与论文源码里的 `\newcommand\xxx...` 冲突。优先把源码中的该行从 `\newcommand` 改为 `\renewcommand`（保留论文作者期望的宏定义）。

**编译“成功”但引用/交叉引用仍是问号**（PDF 里出现 `??` 或 `[?]`）
→ 这通常意味着编译过程里发生了 LaTeX 错误，但在 `nonstopmode` 下仍生成了 PDF，导致 `latexmk` 没能完成多次编译而解析引用/交叉引用。
→ 解决思路：开启 `-halt-on-error`（让错误直接失败并返回日志）并修复首个报错后重试。

**宏包缺失** `File 'xxx.sty' not found`
→ 该包未安装在远程服务器上。可在 `https://latex.ytotech.com/packages` 查询可用包列表。若缺失，尝试注释掉该包或替换为等价的可用包。

**中文溢出 / Overfull \hbox**
→ preamble 中已包含 `\setlength{\emergencystretch}{3em}`，通常足够。若仍溢出，添加 `\sloppy`。

**参考文献问题（bibtex/biber）**
→ 确认 `.bib` 文件已存在于工作目录并被正确引用；若论文自带 `.bbl` 而没有 `.bib`，优先复用 `.bbl`。如需 biber，在请求中设置 `options.bibliography.command`。

**远端编译超时 / 变慢**
→ 检查工作目录里是否混入了历史产物（尤其是无关的 PDF、`.aux`、`.log`、旧输出文件）。这些文件会被一并上传，显著拖慢远端编译，甚至导致超时。

**编译成功但源码自带 `.bbl` 被误删**（重编后引用变 `??`）
→ 不少 arXiv 论文不发 `.bib`，而是直接附带预生成的 `main.bbl`。这种 `.bbl` 是**源码**，不是中间产物。如果误删（早期 cleanup.py 会一并清理 source 根目录下的 `.bbl`），下次重编就会出现一堆 `??`。修复：从 `arxiv.org/e-print/{paper_id}` 重新下载源码，把 `main.bbl` 拷回 `source/`。

## CJK 排版陷阱（仅渲染才看得出来）

下面这些问题**编译 exit code = 0 也不会报错**，必须**渲染首页/相关页面到 PNG 实际看一遍**才能发现。SKILL.md 第四步的「排版自检」就是为此而存在的。

**作者块溢出右边距**
→ 中文机构名加上 `（English）` 对照常常是英文原作的 1.5–2 倍长。原作 `\quad` 串起来的一行翻完会切到页外。详见 `references/author-block.md` §7：作者名 3-3-3 一行，机构每个一行。

**表格压到对面栏中文上 / 多列表格挤压 / 列宽不足 / 文字与边框重叠**
→ **首选方案：用 `\resizebox{\linewidth}{!}{...}` 包裹外层 `\begin{tabular}`**。`\linewidth` 在 `table` 里 = 栏宽，在 `table*` 里 = 页宽，一段代码窄表宽表通吃；只对真正超宽的表起作用、按比例保留作者排版意图、小表不被强行拉宽。完整诊断流程与二级手段见 `references/table-overflow.md`。
→ 如果 `\resizebox` 后字号过小（原作已 `\scriptsize`、再缩 25%+），改用 `pdflscape` 把整个表横版：

```latex
\begin{landscape}
\begin{table}[t!]
  \centering
  \scriptsize
  \setlength{\tabcolsep}{4pt}
  \renewcommand{\arraystretch}{1.18}
  \begin{tabularx}{\linewidth}{...更宽的列宽...}
    ...
  \end{tabularx}
\end{table}
\end{landscape}
```

`pdflscape` 通常已经在原作 preamble 里 `\usepackage{pdflscape}`，直接用即可；横版后 `\linewidth` 变为页面长边（约 23 cm 而非 16 cm），有充裕空间放中文。同时把窄列从 `m{0.55cm}` 这类拉宽到 `m{0.8cm}`，把 X 弹性列保留给最长的「描述」列。

**wrapfigure 中文 caption 溢出 / 与正文重叠**
→ `\begin{wrapfigure}{r}{0.45\linewidth}` 把图限制在半幅宽度，caption 自然也在半幅宽内；中文段落比英文长，caption 撑高了 wrapfigure 就会和正文相互覆盖。修复优先级：
1. 把 caption 内的加粗段精简到一句话；
2. 把 wrapfigure 改为普通 `figure[t]`（不强求文字绕排）；
3. 加大 `wrapfigure` 宽度到 `0.5\linewidth`。

**相邻堆叠的 figure + table，图注与表注上下叠字**
→ 同一栏顶部紧挨着的 `figure[t]` 与 `table[t]`（源码里两个浮动体一前一后、中间几乎没有正文），中译后图注与表注贴死、文字相互重叠。根因**不在表**，而在 figure 内 `\caption`/`\label` 之后那行用来省页的负间距（如 `\vspace{-6mm}`）：英文原作图注只占一行，`-6mm` 刚好压掉图下空白；中译后图注常涨到两行（方块字更宽 + `\linespread{1.25}`），figure 的真实高度比 `-6mm` 所假定的多出约一行，于是紧随其后堆叠的 `table` 仍按被缩短的 box 下边界往上排，正好压到图注末行上。这类问题**日志不报 Overfull**（是浮动体间距问题，不是 hbox 超宽），只有渲染该页才看得出来。
→ 修复：按「中文比英文多出的行数 × 行高」回补那行负 `\vspace`（单栏正文每行 ≈5mm，故把 `-6mm` 调成 `-1mm` 即可，并非全删），或直接删掉它；**不要**去改全局 `\textfloatsep`/`\floatsep`（会牵动全篇所有浮动体）。改完渲染该页确认两注之间留出间距、且下方浮动体没有被顶到次页。实例：RSGround-R1 第 9 页 Figure 5(`fig:std`) 与 Table 5(`tab:spacon`) 叠字，定位到 `sec/4_experiment_zh.tex` 中 `fig:std` 图注后的 `\vspace{-6mm}`，改为 `\vspace{-1mm}` 后两注分开、排版未跑版。

**附录里 tcolorbox + lstlisting 冲出右边距**
→ 不是 box 的问题，是 box 内 `lstlisting` 默认 `breaklines=false` 导致长中文整行不断行。preamble 加 `\lstset{breaklines=true, ...}` + `\tcbset{promptstyle/.style={...}}` 就一次解决排版 + 美观。完整诊断与脚本见 `references/framed-content.md`。

**长 caption 内 `（共 $87$ 个）` 这种 inline math**
→ 在 xeCJK 下，数字夹在中文标点 `（）` 中间偶尔会触发奇怪的换行点；如果发现 caption 被切断，把 `$87$` 换成纯文本 `87` 试一试，并去掉前后多余空格。

**编译看似成功但实际 silent overflow**
→ TeX 默认对 `Overfull \hbox` 只打 warning 不报错。建议每次编译后 `grep "Overfull" build/main_zh.log` 看是否有 hbox 超 50pt 的项；超过的位置就是潜在的溢出页面，必须渲染对应页 PNG 复核。

## 读取错误日志

编译失败时，服务端返回含完整日志的 JSON。找到以 `!` 开头的行定位致命错误：

```
! LaTeX Error: ...
! Undefined control sequence ...
! Missing $ inserted ...
```

优先修复第一个错误——后续错误通常是连锁反应。

## 译稿作者侧的三个高频陷阱（都在真实事故里出现过）

| 症状 | 根因 | 修复 |
|---|---|---|
| `! LaTeX Error: Command \ss already defined` | `\ss` 是 LaTeX 内置（德语 ß）；自定义五级标题宏用了它 | 标题宏改名（如 `\hdA`–`\hdE`），避开保留字 |
| 列表项项目符号消失、`M.2` 跑到标签位置 | `\item [M.2]、[CEM]…` 的首个方括号被当成 `\item` 的可选标签参数 | 以 `[` 开头的列表项整体包花括号：`\item {[M.2], [CEM], …}` |
| `! Undefined control sequence. \checkmark` | `\checkmark` 在 `amssymb` 里，只加载 `amsmath` 不够 | 导言加 `\usepackage{amssymb}` |

另：caption 自动编号与正文引用不一致（caption 打「图 1」、正文写「图 7-132」）不是编译错误
但属于交付缺陷，见 `pdf-pipeline.md` 的 spec 一节（`\renewcommand{\thefigure}`）。
