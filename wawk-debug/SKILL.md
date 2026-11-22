---
name: wawk-debug
description: Use when debugging simulation waveforms in FST or VCD format with wawk/WAL — locating x/z propagation, unknown-condition fail-fast errors, protocol handshake violations (valid/ready), cycle-accurate event search, latency/histogram statistics, or when a .wawk program fails to parse or crashes at runtime.
---

# wawk-debug：FST/VCD 仿真波形调试

用 wawk（WAL 的 AWK 风格前端）对仿真波形做程序化调试。程序由 `条件: { 动作 }` 组成，
条件在波形**每个时间索引**（每次信号变化的时间戳）求值，逗号分隔的条件是 **AND** 关系。
按文件扩展名自动选择后端：`.fst`（需 pylibfst）、`.vcd`、`.csv`。

**核心原则：本 skill 的每条语法结论都在真实 FST/VCD 上运行验证过；wawk 语法与 C/Verilog
直觉有多处偏差（见陷阱表），写程序前先查表，报错时先对照陷阱表再改代码。**

## 何时使用

- 调试 FST/VCD 波形：找 x/z 传播源头、定位某信号异常的时刻
- 协议检查：valid/ready 握手延迟、stall 期间数据变化、溢出/计数器统计
- 报错关键词：`UnknownConditionError`、`unknown value 'x' used as condition`、
  `variable MAX is undefined`、`whenever: expects exactly two arguments`、
  `resolve-group: No signal with name`、`No terminal matches '='`、`pylibfst`
- 不适用：RTL 设计/生成（用 spinal-de）、SpinalSim 测试台（用 spinal-dv）

## 环境（本机已验证）

```bash
wawk prog.wawk trace.fst        # PATH 上的 wawk = wal_eh 仓库 editable 安装，FST/VCD 均可
wawk prog.wawk trace.vcd arg1   # 额外参数进入 args 列表
wawk -o out.wal prog.wawk trace.fst   # 只转译成 WAL 不执行（调试语法/优先级必备）
```

- 仓库：`/Users/feng/Desktop/Code/wal_eh`；测试波形：`examples/basics/counter.fst`、
  `examples/four-state/xz.vcd`、`examples/four-state/xz.fst`
- FST 依赖 pylibfst。本机 `wawk` 走 Python 3.9（CommandLineTools，已装 pylibfst）；
  `python3`（3.11）**没有** pylibfst，用它跑 FST 会 ModuleNotFoundError。
  Python API 或备用入口用：`/Library/Developer/CommandLineTools/usr/bin/python3 -m wawk.wawk`
  （在仓库目录下，或设 `PYTHONPATH=/Users/feng/Desktop/Code/wal_eh`）

## 调试工作流

1. **摸清信号**：FST 用 `BEGIN: { print(SIGNALS); print(SCOPES); }` + 一条哑语句 `0: { }`；
   VCD 的 SIGNALS 只含程序里字面引用过的信号（keep_signals 过滤），发现信号直接
   `grep '\$var' trace.vcd`。见 `examples/inspect.wawk`。
2. **写程序**：BEGIN 初始化（列表必须 `xs = [];`）→ 若干 `条件: { 动作; }` → END 汇总。
   语句以 `;` 结尾，注释 `//`。模板见 examples/。
3. **运行并读错误**：fail-fast 报错自带信号名与 TS，直接给出 x 污染位置；
   解析错误先用 `wawk -o` 转译检查实际 WAL 结构。
4. **迭代定位**：`find(条件)` 返回所有命中索引；`sig@-1` 取前一索引值；
   数组做直方图；`import(mod); call(mod.fn, ...)` 调 Python 译码（模块需在 cwd）。
5. **交叉验证**：同一程序在 FST 与 VCD 上输出应一致（四态示例已验证逐字节相同）。

## 速查表

| 目的 | 写法（均已验证） |
|---|---|
| 上升沿后采样 | `tb.clk == 1, tb.clk@-1 == 0: { ... }` |
| 沿前（setup）值 | `rising(tb.clk): { ... }`（在沿**前一索引**触发，clk 仍为 0） |
| 找 x/z | `find(x?(tb.data))`、`find(z?(tb.bus))` |
| 精确匹配含 x 值 | `tb.data === 0b01xz`（`==` 遇 x 产生未知并 fail-fast） |
| x 容忍守卫 | `known?(tb.data), tb.data == 0: { ... }` |
| 历史值 | `sig@-1`、`sig@-2`（越界返回 false，需 `INDEX >= n` 守卫） |
| 位/切片 | `sig[0]`、`sig[7:4]`（仅信号可下标；值用 `slice(v, 3, 1)`） |
| 直方图 | `hist[sig] = hist[sig] + 1;`（缺失键读作 0，数组自动创建） |
| 最大索引 | `eval(parse("MAX-INDEX"))`（带连字符的名字不能直接写） |
| 信号位宽 | `eval(parse("(signal-width 'tb.data)"))` |
| 打印四态值 | `print("v=", sig)` 逗号分隔，或 `printf("%s", sig)` |
| 运行时参数 | `args[0]`、`args[1]` |

## 陷阱表（全部实测复现过）

| 陷阱 | 后果 | 正确写法 |
|---|---|---|
| `!a \|\| b` | `!` 吞掉整个后续表达式，转译成 `!(a \|\| b)`，**加单层括号也无效** | `a == 0 \|\| b` 或 `( !(a) ) \|\| b`；`!x && y` 安全 |
| `sig == 0` 遇 x/z | UnknownConditionError（这是有意的 x 暴露） | `===`/`!==` 或 `known?` 守卫 |
| `MAX-INDEX`、`signal-width`、`convert/bin`、`find/g` 等 | 连字符/斜杠/`->` 不在符号文法内，解析成减法/除法或报错 | `eval(parse("..."))` 包 WAL 原文 |
| 只有 BEGIN 没有条件语句 | `whenever: expects exactly two arguments` 崩溃 | 追加哑语句 `0: { }` |
| 恒真条件写 `1:` | `AttributeError: DEFUN`（Python `[1]==[True]` 误入函数定义分支） | 用 `INDEX >= 0:`；哑语句用 `0:`（安全） |
| END 里读 `INDEX` 当最大索引 | whenever 结束后索引被恢复为 0 | `eval(parse("MAX-INDEX"))` 或在循环内记录 |
| `arr[k] += 1` | 解析错误（复合赋值只支持普通变量） | `arr[k] = arr[k] + 1`；C 风格 for 更新槽同理用 `inc(i)` |
| `return x;` | 解析错误，wawk 无 return | 函数值 = 最后一个表达式；if/else 是表达式 |
| `rising(clk)` 当沿后采样 | 实际在沿前一索引触发，采到的是沿前值 | 沿后采样用 `clk == 1, clk@-1 == 0` |
| `group(["tb"])` | 拼出 `tbdata` 找不到信号 | 组名带尾点：`group(["tb."]) { #data; }` |
| VCD 中 `#sig`/动态名 | keep_signals 只保留程序字面引用的全名 | 在程序某处字面写一次全名（如 `print(tb.data);`）；FST 无此限制 |
| `~sig`、`scope(tb.dut)` | wawk 中损坏（in-scope 参数数/符号求值错误） | 用完整层次名或 `group()` |
| `append(xs, x)` 未初始化 | xs 自动定义为 0，0+列表报错 | BEGIN 里 `xs = [];`；且 append 是纯函数，必须 `xs = append(xs, x)` 回写，裸语句静默丢弃结果 |
| list 风格数组用变量下标读 `xs[i]` | 静默返回 0（不报错）：变量下标转译成 geta/default（要求 WAL dict 数组，parser.py:173），而 `xs=[]`/append 产生 Python list；字面量下标走 slice 正常——同体内 `xs[0]` 有值而 `xs[i]` 读 0（已实测） | 两套体系勿混用：list 风格（`xs=[]`/`xs=append`）只用字面量下标；hist 风格（`h[k]=h[k]+1` 自动创建 dict）只整体 print；**跨规则有序队列比对用 Python 互操作**（import(mod); call(mod.push/check, sig)，模块持真队列，已实测） |
| `printf("%d", 四态值)` | TypeError | 用 `%s`；字符串 `+` 拼接遇 x 也会出错，用逗号 print |
| `~` 当按位非 | `~` 是作用域前缀 | `bnot(v)`；位运算 `band/bor/bxor` |

## 示例（examples/，均附运行命令与期望输出）

- `inspect.wawk` — 信号/作用域/规模盘点（FST）
- `xhunt.wawk` — x/z 源头定位（xz.vcd / xz.fst 通用）
- `hist.wawk` — 计数器值直方图（counter.fst）
- `handshake.wawk` + `handshake.vcd` — valid/ready 延迟与 stall 违例自检包含期望输出

## 深入参考

语法全集、四态语义、可用函数清单、Python API、多波形对比、转译调试：见 [reference.md](reference.md)。