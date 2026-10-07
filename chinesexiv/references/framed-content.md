# 框内的东西（tcolorbox / lstlisting）— 诊断 + 排版基线

## 现象

很多论文（尤其 LLM/数据集类工作）在附录里用 `tcolorbox` 装 GPT 提示词、JSON 模板、对话样例。原作英文版排版通常没问题，但翻译成中文后会同时出现两类问题：

1. **内容明显冲出框右边**：`<global>`、`<stage_1_reasoning>` 等模板内容紧贴右边距向外溢出，盖到下一栏的中文上。
2. **框内排版"一般般"**：纯白底 + 黑标题 + 紧贴边的内文，看起来像"裸 verbatim"而不是设计过的可读说明块。

第 1 类是**正确性问题**（必修），第 2 类是**美观与可读性问题**（强烈建议一并处理，否则译稿读起来很糙）。

---

## 根因（第 1 类：内容冲出）

box 本身（`tcolorbox` + `breakable`）会跟随 `\linewidth`，宽度不会越界。**问题不在 box，在 box 内部的 `lstlisting`**：

```latex
\begin{tcolorbox}[..., breakable]
\begin{lstlisting}
Question Intent（问题意图）：识别所提问题的类型（例如目标类别、计数、颜色、空间关系等），并确定回答它所需的视觉信息。
\end{lstlisting}
\end{tcolorbox}
```

`lstlisting` 默认 **`breaklines=false`**——它**就是设计成"原样按字符显示，不主动换行"**的。英文代码长度可控，作者写代码时手动按 80 列折行就够了；中文模板内容是一句话写到底的自然段落，`lstlisting` 拿到这种内容就会**逐字符往右排到无穷远**，越过 box 边界、越过列边界、越过页边界。

`\verb|...|` 也是同样的"不能断行"机制——如果一行里有一段超长的 `\verb`，整行也卡死不能断。

---

## 根因（第 2 类：框内"一般般"）

`tcolorbox` 默认参数走的是"画一个朴素方框"——白底、黑标题、约 2pt 的内边距。中文段落字距比英文紧、行高比英文高，套这个默认样式后视觉上有几个常见问题：

- **标题色和正文色一样**，没视觉对比；
- **内边距太小**（默认 `boxsep=2pt`），中文段落紧贴左右框线，像挤进去的；
- **纯白背景**和正文白底连成一片，框内框外没有"这是个 callout"的提示；
- **多个 box 在不同 `\begin{tcolorbox}[title=..., colframe=..., colback=..., ...]` 里各写一遍**选项，样式漂移，看起来风格不统一。

---

## 修复（首选）：preamble 里加两个 set

直接在主 `.tex` 的 preamble（一般在 `\usepackage{listings}` + `\usepackage[most]{tcolorbox}` 之后、`\input{preamble}` 或 `\begin{document}` 之前）加：

```latex
% --- 让 lstlisting 在 tcolorbox 内能自动换行，避免长中文整行冲出框 ---
\lstset{
  breaklines=true,
  breakatwhitespace=false,
  basicstyle=\small\ttfamily,
  columns=fullflexible,
  keepspaces=true,
  showstringspaces=false,
  upquote=true,
  aboveskip=4pt,
  belowskip=4pt,
  postbreak=\mbox{\textcolor{gray}{$\hookrightarrow$}\space},
}

% --- tcolorbox 统一基线（轻灰背景、紧凑内边距、标题加粗） ---
\tcbset{
  promptstyle/.style={
    enhanced,
    breakable,
    colback=gray!4,
    colframe=gray!50,
    coltitle=black,
    fonttitle=\bfseries\small,
    fontupper=\small,
    title style={gray!12},
    boxsep=3pt,
    left=8pt, right=8pt, top=5pt, bottom=5pt,
    arc=2pt,
    boxrule=0.6pt,
    before skip=8pt, after skip=8pt,
  }
}
```

然后把每个 `\begin{tcolorbox}[title=XXX, colframe=..., colback=..., coltitle=..., fonttitle=..., breakable]` 简化为：

```latex
\begin{tcolorbox}[promptstyle, title=XXX]
```

样式选项全部集中到 `promptstyle` 里，每个具体 box 只写自己的 `title=`。三个好处：

1. **所有 box 风格统一**——不再每个 `\begin{tcolorbox}[...]` 都重复写 5-6 个选项，也不会风格漂移。
2. **想全局调样式只改一个 `\tcbset`**——比如想加大左右内边距、想换框线颜色，改一处就全篇生效。
3. **`lstlisting` 自动换行**——所有 box 里的 `lstlisting` 都拿到 `breaklines=true`，长中文行自动折行，`↪` 指示符告诉读者"这是一行的接续，不是新的一项"。

---

## 一键脚本：批量替换 inline 选项 → `promptstyle`

如果论文里已经有 N 个 `\begin{tcolorbox}[title=..., colframe=..., colback=..., coltitle=..., fonttitle=..., breakable]` 这种写法，用下面的 Python 把它们全部压成 `[promptstyle, title=...]`：

```python
import re
from pathlib import Path

p = Path("path/to/suppl_zh.tex")
text = p.read_text()
pattern = re.compile(
    r"\\begin\{tcolorbox\}\[\s*title=([^,\]]+),"  # captures title up to first comma
    r"(?:[^]]*?)"                                  # eats the rest of options non-greedy
    r"\]",
    re.DOTALL,
)
new_text, n = pattern.subn(r"\\begin{tcolorbox}[promptstyle, title=\1]", text)
print(f"replaced {n} tcolorbox blocks")
p.write_text(new_text)
```

注意：上面的正则把 `title=` 后**第一个逗号**当成 title 的结尾。如果某个 title 内部确实写了**英文半角逗号**（中文论文里很罕见），那个 box 不会被替换，肉眼检查一下就好。

---

## 翻译边界：prompt 模板不是“代码本体”

LLM/agent 论文的附录常把系统提示词、数据清洗提示词、动作空间说明、JSON 输出格式放进 `tcolorbox`。这些内容虽然看起来像 prompt/code block，但其中大部分是**自然语言论文内容**，默认必须翻译。

处理规则：

- 翻译：任务说明、角色说明、输入/输出解释、步骤说明、动作描述、表格表头、示例中的自然语言目标。
- 保留：JSON key、API/action name、XML tag、占位符、变量名、文件名、URL，例如 `action_type`、`open_app`、`<tool_call>`、`<instruction_here>`、`{goal}`。
- 示例 JSON 可以保留 key 和结构，但 value 里的自然语言描述可以中译，例如 `"target":"blue circle button at top-right"` → `"target":"右上角蓝色圆形按钮"`。
- box 标题也要中译，例如 `SFT Training Example` → `SFT 训练示例`，`Prompt for Instruction Refinement` → `指令精炼提示词`。

反例：把整个 tcolorbox 说成“训练 prompt 按原样保留以保证完整性”。这会让附录大段英文“没有反应”，不符合全文中文 PDF 的目标。正确做法是保留机器可读 token，翻译可读说明文本。

---

## tcolorbox 基线：纯文本 prompt 也要统一样式

即使 box 内没有 `lstlisting`，也建议在 preamble 定义统一样式，然后所有 prompt box 使用：

```latex
\tcbset{
  promptstyle/.style={
    breakable,
    colback=black!3,
    colframe=black!65,
    coltitle=white,
    colbacktitle=black!70,
    fonttitle=\bfseries,
    boxrule=0.5pt,
    arc=1mm,
    left=2mm,right=2mm,top=1mm,bottom=1mm,
    before skip=8pt,after skip=8pt,
  }
}
```

然后写成：

```latex
\begin{tcolorbox}[promptstyle,title=指令精炼提示词]
...
\end{tcolorbox}
```

好处是：标题条、灰底、内边距、跨页行为全部一致；后续如果发现框太挤，只改 `promptstyle` 一处即可。

## 边界情况

**A. `lstlisting` 里有缩进/对齐结构**（如 JSON 数据样例）
→ `columns=fullflexible` 配合 `keepspaces=true` 会保留缩进。如果 JSON 排得歪了，临时换 `columns=fixed`、但仅在那一段 `[language=json]` 局部覆盖：

```latex
\lstdefinelanguage{json}{columns=fixed, ...其它原有 json 设置...}
```

**B. `\verb|...|` 仍然冲出（不是 `lstlisting`，而是行内 `\verb|...|`）**
→ `\verb` 没法配置自动断行。改成 `\texttt{...}`，或把过长的 `\verb|some\_long\_thing|` 换成 `\seqsplit{some\_long\_thing}`（需 `\usepackage{seqsplit}`）。

**C. 框跨页时 footer/header 被框压住**
→ `breakable` 已默认避开 footer/header；如果还出问题，给 box 加 `pad at break*=2mm` 让分页处有缓冲。

**D. 多语言混排（中文段落 + 英文/代码片段）**
→ 在 `\lstset` 的 `basicstyle` 上加显式中文字体可以让代码块里的中文也保持等宽：`basicstyle=\small\ttfamily\setCJKmonofont{Noto Sans Mono CJK SC}`，但需要先确认系统有这个 CJK mono 字体。多数情况下默认 `\ttfamily` 在 xeCJK 下已经能渲染中文，不需要特殊设置。

---

## 不要做这些

- **不要在每个 tcolorbox 里反复写完整选项列表**——用 `\tcbset{promptstyle/.style={...}}` 收口。
- **不要把 `lstlisting` 改成 `verbatim`**——`verbatim` 同样不会自动换行，问题原封不动。
- **不要把 lstlisting 里的中文段落改成 `text` 段落**（即跳出 `lstlisting`，改用 `\\` 手动断行）——`<global>` `<stage_1_reasoning>` 这种模板标记需要等宽字体显示，跳出 `lstlisting` 后会失去结构感。
- **不要把整个 box 改 `\resizebox{\linewidth}`**——会把字号也按比例压小，长 box 读起来更累。`\resizebox` 是表格的修法，框的修法是开 `breaklines`。

---

## 速查 checklist

```text
[ ] 编译一次 → grep Overfull \hbox > 5pt
[ ] 用 grep -B 2 "Overfull" 找文件名，看溢出是不是来自 tcolorbox 包裹的 lstlisting
[ ] 如果是 → preamble 加 \lstset{breaklines=true, ...} + \tcbset{promptstyle/.style={...}}
[ ] 用 Python 把所有 \begin{tcolorbox}[ inline 选项一堆 ] 压成 [promptstyle, title=XXX]
[ ] 重新编译 → grep Overfull 应归零
[ ] 渲染 box 所在页（200dpi+）→ 确认内容在框里、换行处有 ↪ 指示符、灰底标题区清晰
```
