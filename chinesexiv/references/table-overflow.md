# 表格与中文重叠 — 诊断 + 修复范式

## 现象

英文论文翻译成中文后，编译能过、exit code = 0，但渲染出来发现：

- 表格右侧伸到对面栏的中文正文上，**字与表格线重叠**；
- 或者表格列宽塞不下中文，单元格里的字被截断、压成竖排；
- 或者宽表挤掉了下方段落，正文乱跑到表格中间。

**根因**：中文方块字单字宽度约为英文比例字体的 1.5–2 倍。原论文按英文宽度调好的 `\small / \tabcolsep / m{X.Xcm}` 在中文下普遍宽度溢出 5–20%。LaTeX 不会自动缩放，只是默默把表格画到栏外。

---

## 不要"一刀切"地缩小所有表

读者反复反映过这种焦虑：要么不修，要么把所有表 `\scriptsize` 一遍——后者会把本来就够紧的表变得难以阅读。**正确的做法是按需修复**：只对真正溢出的表动手，对没溢出的表保持原作的字号与排版意图。

---

## 诊断（一行命令拿到溢出清单）

编译完一遍后，**先 grep 编译日志**：

```bash
grep -E "Overfull \\\\hbox \([0-9]+\.[0-9]+pt" "$WORK_DIR/build/${MAIN_TEX_ZH%.tex}.log" \
    | awk -F'[()]' '$2+0 > 5 {print}'
```

> `> 5` 是经验阈值：< 5pt 的小溢出通常是图片宽度故意设为 1.02\linewidth 之类的有意行为，不必动；> 5pt 几乎一定是中英换算导致的表格/段落超宽。

每条 `Overfull \hbox (XX.XXpt too wide) in paragraph at lines AAA--BBB` 告诉你**精确行号区间**。把这些区间和 `\begin{tabular}...\end{tabular}` 块匹配，就拿到了"需要修的表"清单。

辅助命令：列出所有 tabular 边界，便于把溢出行号对应到具体表：

```bash
grep -n "^\\\\begin{tabular}\|^\\\\end{tabular}\|^\\\\begin{table\*\?}" "$WORK_DIR/$MAIN_TEX_ZH"
```

注意 **区分外层和单元格内嵌的 tabular**：`\begin{tabular}[c]{@{}c@{}}...` 这种带 `[c]` 选项参数、出现在行首之外的，是 `\makecell` 风格的内嵌表头，**不要包**；只包行首的、跟 `\begin{table}` / `\begin{table*}` 同级的外层 tabular。

---

## 修复：`\resizebox{\linewidth}{!}{...}` 包裹外层 tabular（首选）

对每个溢出的**外层** `\begin{tabular}{...}` 块，整体包成：

```latex
\resizebox{\linewidth}{!}{%
\begin{tabular}{...}
...
\end{tabular}
}
```

**为什么选 `\resizebox{\linewidth}`**：

1. **`\linewidth` 自适应栏宽**：在 `\begin{table}` 里它等于 `\columnwidth`，在 `\begin{table*}` 里它等于 `\textwidth`。同一段代码对窄表和宽表都对。
2. **按比例缩放，不破坏作者意图**：作者已经调好的 `\small / \tabcolsep / 列宽` 比例关系全部保留，只是整体按比例缩到一个允许的宽度内——不会出现"行高被改、字号被改、列宽不一致"这种连锁问题。
3. **只缩不放**：`\resizebox` 在自然宽度大于目标宽度时缩，等于时不变，**不会把小表强行拉宽**。所以可以对所有怀疑溢出的表都包上，没溢出的表完全不受影响。
4. **可批量自动化**：定位行号后用 Python/sed 在 `\begin{tabular}` 前插入 `\resizebox{\linewidth}{!}{%`、在 `\end{tabular}` 后插入 `}` 即可，一次改完所有溢出表。

**可读性下限**：原作字号通常已经 `\small`（≈9pt）或 `\scriptsize`（≈7pt）。`\resizebox` 缩 15% 后约 7.65pt / 5.95pt，仍可读；缩 25% 后约 6.75pt / 5.25pt，是底线。**如果某张表溢出超过 25%**，单靠 `\resizebox` 字号会过小，要叠加下面的"二级手段"。

---

## 二级手段（溢出超过 20% 或视觉仍挤）

按顺序尝试，**不要从最重的方案开始**：

1. **先把 `\tabcolsep` 压紧**：在 `\begin{table}` 内加 `\setlength{\tabcolsep}{2pt}`（或在原 `\addtolength{\tabcolsep}{-X.Xpt}` 基础上再 -1.5pt）。这是免费的，不动字号也不动行高。
2. **降低行间距**：`\renewcommand{\arraystretch}{0.95}`。中文方块字本来就把行抬高了，回压 5% 视觉影响小。
3. **缩短表头/单元格中的长术语**：例如 "图像尺寸 (Image Size)" → "尺寸"、"参数量 (#Param.)" → "#参数"。表头是最容易超宽的地方，**写表头时尽量用 2–3 字的短词**。
4. **窄列改宽列**：原作里 `m{1.10cm}` 这种为英文设计的窄列，中文一定塞不下。改为 `m{1.4cm}` 或者把所有窄列改用 `\centering` 不再固定宽度（让 LaTeX 自适应）。
5. **整张表横版**：`\begin{landscape}\begin{table}...\end{table}\end{landscape}`（需要 `\usepackage{pdflscape}`，原作通常已有）。`\linewidth` 横版后变成 23 cm 而不是 16 cm，给中文充裕空间。**仅在前面手段无效时用**——横版会让读者必须扭头看 PDF。
6. **拆表**：原作里把多个独立子表硬塞进一个 `\begin{table}` 的（典型：Swin Transformer 论文 Table 2 = (a)+(b)+(c) 三个 tabular 叠在一个 table 环境里），可以拆成 `\begin{table}[t]`...(a)...`\end{table}` + `\begin{table}[t]`...(b)... 三个独立 float。**这是最后选项**——会改变图表编号或交叉引用的语义，需要谨慎处理。

---

## 不要做这些

- **不要全文 `\scriptsize`**：会把没溢出的表也变小，论文整体视觉劣化。
- **不要直接删表头里的字以求"短"**：把"图像尺寸"删成"图"会失去信息。`\resizebox` 优先于阉割内容。
- **不要单独缩字号而不缩列宽**（如把 `\small` 改 `\tiny` 但不改 `\tabcolsep`）：字小了但列宽没变，列间空白变大，**视觉更乱**。
- **不要去掉 `\begin{tabular}` 外层的 `\centering`**——`\resizebox` 是单个盒子，不破坏对齐。
- **不要把整页 `\textwidth` 模式（`table*`）的表改成 `table`**：那样会强行塞到单栏，无解。

---

## 自动化检查脚本（建议每次编译后跑）

```bash
LOG="$WORK_DIR/build/${MAIN_TEX_ZH%.tex}.log"
echo "=== Overfull \\hbox 总数 ==="
grep -c "^Overfull" "$LOG"
echo "=== 严重溢出（>5pt）==="
grep -E "Overfull \\\\hbox \([0-9]+\.[0-9]+pt" "$LOG" | awk -F'[()]' '$2+0 > 5 {print}'
```

**收敛标准**：所有 > 5pt 的 Overfull 都消失（或剩下的明确属于"作者故意 1.02\linewidth"这类合理项）。

---

## 视觉失败但日志干净：13 列 benchmark 表的处理

有些大表在日志里只剩 `< 5pt` 的轻微 `Overfull`，但渲染后仍然明显失败：

- `Bas./Adv.`、`Text/Icon` 这类子表头贴在一起；
- 多个数字之间几乎没有空隙，看起来像 `43.936.8`；
- 表格没有越出页边，但**读者已经无法可靠区分列**。

这类问题不是“编译溢出”，而是**视觉可读性溢出**，必须用渲染页判断。常见于 MMBench / ScreenSpot 这类 12–13 个数值列的大 benchmark 表。

先不要默认横向页。13 列 benchmark 表经常“看起来很宽”，但在单页竖版里仍可能通过紧凑列设计保持可读。先做一个临时副本，尝试竖版紧凑方案：

```latex
\begin{table}[p]
  \centering
  \tiny
  \renewcommand{\arraystretch}{0.88}
  \setlength{\tabcolsep}{1.0pt}
  \caption{...}
  \begin{tabularx}{\linewidth}{
    @{}>{\raggedright\arraybackslash}p{0.255\linewidth}
    | *{12}{>{\centering\arraybackslash}X}
    | >{\centering\arraybackslash}p{0.042\linewidth}@{}}
  ...
  \end{tabularx}
\end{table}
```

竖版通过标准：

1. 编译日志没有 `> 5pt` 的严重 `Overfull \hbox`；
2. 渲染页里数字列之间有稳定空隙，读者不需要猜列边界；
3. 模型名列允许自然换行，但不能把整行撑得过高；
4. 表体实际字号不要低于约 5pt；若中位数字字号约 6pt，通常仍可接受。

如果竖版紧凑方案仍然只是“勉强没越界”、列边界难辨，或为了塞下表格必须继续压到 `\tiny` 以下，再把整张宽表放到横向页：

```latex
\usepackage{pdflscape}  % preamble

\begin{landscape}
\begin{table}[p]
  \centering
  \scriptsize
  \renewcommand{\arraystretch}{0.94}
  \setlength{\tabcolsep}{3.2pt}
  \caption{...}
  \begin{tabularx}{\linewidth}{l|*{12}{>{\centering\arraybackslash}X}|c}
  ...
  \end{tabularx}
\end{table}
\end{landscape}
```

注意点：

1. 横向页里用 `table` + `[p]`，不要再用 `table*`；横向页本身已经给了整页宽度。
2. 表体宽度用 `\linewidth`，不要写死 `\textwidth`，这样旋转后能吃到横向页宽。
3. 表头尽量译成短词：`Bas.` → `基础`，`Adv.` → `进阶`，`Avg.` → `平均`，`Text/Icon` → `文本/图标`。
4. 横向页后必须渲染该页，确认数字之间有稳定空隙、列分组线清楚、caption 不压表。

判断标准：竖版优先；横向页是可读性兜底，不是默认答案。如果 `\resizebox{\linewidth}{!}{...}` 或上面的竖版紧凑方案后仍然只是“勉强没越界”，但读者需要猜列边界，就应升级为横向页。

---

## wraptable 与图/正文重叠：不要硬留 wrap

`wraptable` / `wrapfigure` 对浮动体位置很敏感。中文变长后，原本半栏宽的小表可能向下侵入后续 figure，或与右侧 minipage 图互相压住。症状是：表 caption 被挤成竖排、表格骑到图片上、右栏图压住表格。

修法顺序：

1. 若表格只是稍宽，先给外层 `tabular` 加 `\resizebox{\linewidth}{!}{...}`。
2. 若仍与后续图或正文抢空间，**把 `wraptable` 改成普通 `table`**：

```latex
\begin{table}[!htbp]
  \centering
  \small
  \caption{...}
  \begin{tabular}{...}
  ...
  \end{tabular}
\end{table}
```

3. 重新编译并渲染该页与下一页，确认表、图、正文不再重叠。

不要为了保留原文环绕效果而继续加负 `\vspace`。中文译稿优先保证可读和不重叠；环绕只是版面优化，不是语义。

## 最后一步：视觉复核（必做，不能省）

`grep Overfull` 只看宽度，**不看相对位置**。下面这些问题日志里看不出，必须渲染：

- 浮动体落点错位（`[t]` 被推到下一页、把本页内容压到底部）。
- 单元格内的中文换行落在了奇怪的位置（`\\` 在 cell 中行为不直观）。
- 表格 caption 太长，跟下一段紧贴、视觉上像一段。

```python
import fitz
doc = fitz.open(pdf_path)
for i in pages_with_tables:
    doc[i].get_pixmap(dpi=200).save(f"/tmp/check_p{i+1}.png")
```

然后用 Read 工具实际看一遍。每张表至少看一次。

---

## 速查 checklist（每篇论文必跑一次）

```text
[ ] 编译一次 → grep Overfull > 5pt → 拿到溢出行号清单
[ ] 把溢出行号映射到外层 \begin{tabular} 块
[ ] 给每个外层 tabular 加 \resizebox{\linewidth}{!}{ ... }
[ ] 重新编译 → grep Overfull > 5pt 应该归零（或只剩故意的）
[ ] 渲染所有含表页 → 眼睛过一遍 → 无重叠 / 无截断 / 无错位浮动
[ ] 仍有问题 → 按二级手段顺序处理（tabcolsep → arraystretch → 表头精简 → 列宽 → 横版 → 拆表）
[ ] 通过 → 提交
```

**经验**：一篇 ICCV/CVPR 风格的 8 页+附录的论文，第一遍编译大概会有 8–15 处 Overfull（绝大多数都是表）。仅用 `\resizebox` 第一轮就能消掉 90% 以上，剩 1–2 处再用二级手段。**总修复时间 < 5 分钟**。这是 chinesexiv 翻译流程里固定的最后一道工序。
