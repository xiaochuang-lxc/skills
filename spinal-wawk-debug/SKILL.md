---
name: spinal-wawk-debug
description: >-
  Use when debugging SpinalHDL simulation failures by waveform analysis with
  wawk/WAL on FST/VCD — locating which user-defined signal misbehaves, tracing
  it back to the Scala source line, and producing a SpinalHDL-level fix.
  Use when a SpinalSim scoreboard/whitebox assertion fails and the FST waveform
  must be inspected, when tempted to debug generated Verilog wires (_zz_*,
  anonymous intermediates) instead of SpinalHDL signals, or when a wawk program
  for a SpinalHDL waveform fails to parse. Called from spinal-dv.
---

# SpinalHDL 层 wawk 波形定位调试

## Overview

用 wawk 对 SpinalSim 产生的 FST/VCD 波形做根因定位，**全程停留在 SpinalHDL 抽象层**。三条核心原则：

1. **只看 SpinalHDL 层定义的信号**：波形观察对象 = Scala 源码中用户命名的信号（val 名/IO 字段名）；编译器生成的中间变量（`_zz_*`、匿名条件信号）一律过滤，不作为定位依据
2. **映射靠行尾注释，不靠信号名**：工程约定三件套下条件信号不带行号，波形信号 → Scala 源码的映射通过生成 Verilog 赋值行尾的 `// @ <文件>.scala l<行号>` 注释完成
3. **交付 SpinalHDL 代码，不交付 Verilog**：定位结论必须落到 Scala 文件+行号+代码片段+修改建议；禁止把 Verilog wire/assign 修改作为修复方案（那是生成物，改它无效且会被下次生成覆盖）

**REQUIRED SUB-SKILL:** wawk 语法/陷阱全集用 **wawk-debug** skill；仿真测试台语义（§14 时序等）用 **spinal-dv** skill。本 skill 只负责 SpinalHDL 层的信号分类、映射与交付形态。

## 工程约定三件套（波形干净的前提）

生成波形前 SimConfig 必须（与 spinal-de/spinal-dv 一致，已源码核实 1.11.0）：

```scala
SimConfig.withConfig(SpinalConfig(
  nameWhenByFile = false,    // when/switch 条件信号不落 when_<文件>_l<行号> 名，归入匿名 _zz_*
  genLineComments = true,    // 生成 RTL 每条赋值行尾 // @ <文件>.scala l<行号>（映射载体）
  mergeSyncProcess = false   // 每寄存器独立 always 块，RTL 结构与 Scala 一一对应
)).withFstWave.withWaveDepth(0).compile(SimEnv)
```

拿到旧波形先检查是否满足三件套（信号清单里有无 `when_*`/`switch_*`）；不满足时注明映射线索差异（旧波形条件信号名自带行号，可直接用）。

## 定位次序（先归属，后排查；工程纪律，必须遵守）

1. **归属分类**：对每个可疑模块/信号先判定是自研代码（工程 src/main 里的 Component/Area/接线）还是 SpinalHDL 自带 lib（spinal.lib.*/spinal.core.* 组件，如 StreamFifo/StreamArbiter/BufferCC）
2. **lib 先黑盒**：对官方 lib 组件只看边界——输入是否符合协议契约（Stream 握手规则、配置参数语义），输出是否符合契约；**首轮 SIGNAL_PLAN 与 wawk 程序不引用 lib 内部信号**（如 `fifo.logic_*`、RAM 读写口），不读 lib 内部实现
3. **聚焦自研代码**：重点排查自研驱动/控制/数据通路/接线逻辑；典型首刀：在 lib 边界比对“自研逻辑送入 lib 的值” vs “原始输入”（如 push payload vs io.in.payload），不等则污染在自研侧，lib 无嫌疑
4. **最后才查 lib 内部**：仅当自研代码全部排除、且 lib 输入完全符合契约而输出仍违约时，才观察 lib 内部信号/读 lib 源码（此时走 spinal-dv/spinal-de 的依赖源码核实流程读同版本源码，不凭记忆断言 lib 行为）

黑盒判定依据：lib 边界输入输出比对结果（如“push 口数据已被改 → 自研接线污染”“push 正确而 pop 违约 → 才轮到 lib 嫌疑”）。次序颠倒（首轮就钻 lib 内部）会在 lib 内部海量信号中浪费时间，且容易把自研 bug 误判为 lib 问题。

## 信号分类配方（SIGNAL_PLAN 的依据）

对 FST 信号清单（`BEGIN: { print(SIGNALS); }` + 哑语句 `0: { }` 盘点）逐个分类：

| 类别 | 识别规则 | 处置 |
|------|----------|------|
| 用户信号 | 名字能在 DUT/SimEnv Scala 源码中找到对应 val/IO 字段（IO 经 noIoPrefix/flatten 后为 `port_in_data` 等下划线拼接；自定义 rename 的按 rename 后名） | **观察对象**，SIGNAL_PLAN 只列这类 |
| lib 边界信号 | 官方 lib 组件的 io 端口（如 `fifo.io_push_payload`/`fifo.io_pop_valid`） | **首轮观察对象**（黑盒输入输出比对） |
| lib 内部信号 | 官方 lib 组件内部（如 `fifo.logic_*`、RAM 读写口、指针） | **首轮过滤**；仅当定位次序第 4 步条件成立才观察 |
| 生成中间变量 | `_zz_*` 前缀（anonymSignalPrefix，Phase.scala:3056）；三件套下的匿名 when/switch 条件信号 | **过滤**，不列入观察计划、不作为根因证据 |
| 时钟/复位 | `clk`/`reset`（或自定义域名） | 仅作采样基准 |

- 分类存疑时：读生成 Verilog 声明区 + Scala 源码对照确认，**不猜**
- 需要观察的内部信号必须在 SimEnv 内 `.simPublic()`（spinal-dv 范式）；波形里没有 ≠ 不存在，先查 simPublic
- 根因推理可以引用中间变量的**值**作辅助证据（如 `_zz_shift_num` 的算术），但结论与修复必须落在用户信号对应的 Scala 代码

## 映射链（波形 → Scala）

```
波形信号名（用户 val 名）
  → 生成 Verilog 中该信号的赋值语句（always 块/assign）
  → 行尾注释 // @ <文件>.scala l<行号>   ← genLineComments=true 提供
  → Scala 源码该行（when 分支上下文）
  → 修复建议（Scala 代码片段）
```

注意：行尾注释标的是**赋值语句**的 Scala 行号（如 when 块内的赋值行），不是 when 条件行；组合逻辑的临时算术可能拆到 `_zz_*` wire 的 assign（无注释或注释指向 BaseType.scala 等库文件）——此时按消费该 wire 的用户信号赋值注释定位。

## wawk 模板（全部在本工程真实 FST 上运行验证过，直接套用）

信号全名前缀 `TOP.<SimEnv名>.`（SimEnv 继承 DUT，顶层即 SimEnv）。**逐字使用下列语法**，勿凭 awk/C 直觉改写。

### 盘点信号

```wawk
BEGIN: { print(SIGNALS); }
0: { }
```

### 逐拍快照 + 违例检测（printf 带空格，print 逗号拼接无空格已实测）

```wawk
BEGIN: { bad = 0; }
// 上升沿后快照（沿前值语义见 spinal-dv §14）
TOP.MySimEnv.clk == 1, TOP.MySimEnv.clk@-1 == 0: {
  printf("cyc ts=%d sig=%d\n", TS, TOP.MySimEnv.my_signal);
}
// 违例：known? 守卫防 x fail-fast；条件逗号=AND
known?(TOP.MySimEnv.my_signal), TOP.MySimEnv.my_signal != 24: {
  bad = bad + 1;
  printf("[BAD] ts=%d sig=%d\n", TS, TOP.MySimEnv.my_signal);
}
END: { printf("bad=%d\n", bad); }
```

### 语法红线（本 skill 实测复现，违反即解析失败/输出不可读）

| 错误写法 | 后果 | 正确写法 |
|----------|------|----------|
| `BEGIN {` / `END {`（awk 风格） | 解析崩溃 | `BEGIN: {` / `END: {`（冒号必须） |
| `print("a=", 1, "b=", 2)` 期望有空格 | 输出 `a=1b=2` 粘连不可读 | `printf("a=%d b=%d\n", 1, 2)` |
| 只有 BEGIN 无条件语句 | whenever 崩溃 | 补哑语句 `0: { }` |
| `sig == 0` 遇 x | UnknownConditionError | `known?` 守卫或 `===` |
| `append(xs, v)` 裸语句 | 纯函数返回新列表被静默丢弃，数组永远空 | `xs = append(xs, v)` 回写 |
| list 数组变量下标读 `xs[i]` | **静默读 0**（geta/default 要 dict，list 不匹配；字面量下标却正常，已实测） | 跨规则有序队列比对用下方 Python 互操作模板 |

### 有序队列比对模板（push/pop 逐笔比对，Python 互操作，已实测）

wawk 两套数组体系不兼容（list：`xs=[]`/append+字面量下标；dict：`h[k]=h[k]+1` 自动创建+整体 print），跨规则变量下标队列比对两者都不可靠，用 cwd 下 Python 模块持真队列：

```python
# swq.py（与 wawk 程序同目录）
q = []
def push(v):
    q.append(int(v)); return len(q)
def check(v):
    if not q: return -1
    e = q.pop(0)
    return 0 if int(v) == e else e   # 0=匹配，否则返回期望值
def left():
    return len(q)
```

```wawk
BEGIN: { import(swq); bad = 0; }
// push fire 沿入队（known? 守卫防 x）
TOP.SimEnv.clk == 1, TOP.SimEnv.clk@-1 == 0, TOP.SimEnv.in_valid == 1, TOP.SimEnv.in_ready == 1, known?(TOP.SimEnv.in_payload): {
  call(swq.push, TOP.SimEnv.in_payload);
}
// pop fire 沿出队比对
TOP.SimEnv.clk == 1, TOP.SimEnv.clk@-1 == 0, TOP.SimEnv.out_valid == 1, TOP.SimEnv.out_ready == 1, known?(TOP.SimEnv.out_payload): {
  r = call(swq.check, TOP.SimEnv.out_payload);
  if (r != 0) { bad = bad + 1; printf("[BAD] ts=%d got=%d exp=%d\n", TS, TOP.SimEnv.out_payload, r); }
}
END: { printf("bad=%d left=%d\n", bad, call(swq.left)); }
```

其余陷阱（`!` 优先级、`@-1` 越界、数组初始化等）查 **wawk-debug** 陷阱表。

## 调试工作流

1. **读失败信息**：仿真日志/记分板 REF-DUT diff 给出失败信号与时刻（SpinalSim 的 t 是沿前快照视角，波形时间戳可能差一个 delta，按信号变化沿对齐，勿硬等数值）
2. **归属分类 + 黑盒首刀**：按「定位次序」区分自研/lib；首轮只观察用户信号 + lib 边界信号，在 lib 边界比对输入输出定污染侧
3. **SIGNAL_PLAN**：按分类配方只选用户信号与 lib 边界信号（失败信号 + 其扇入上下文寄存器/握手），lib 内部与中间变量过滤
4. **写 wawk 程序**：套上方模板，在 FST 上复现违例时刻与值
5. **执行并读输出**：`wawk prog.wawk wave.fst`（环境见 wawk-debug）；解析失败先对照语法红线表。**必须拿到真实运行输出才算证实**；“预期输出”、静态代码/Verilog 推断不能替代；运行时报错（如 IndexError/空列表访问）先修到跑通（END 汇总访问数组前检查非空/计数守卫）
6. **映射定位**：沿映射链找到 Scala 行号，读 when 分支上下文确认根因；自研排除后才按次序第 4 步查 lib 内部
7. **交付**（输出契约，四部分顺序固定）：
   - SIGNAL_PLAN：用户信号清单+理由
   - WAWK：完整可运行程序（附真实运行关键输出）
   - DIAGNOSIS：信号/时刻/行为/为什么错，引用波形证据
   - FIX：**Scala 文件路径+行号+问题片段+修改后片段+一句话理由**；按改动门禁分型：根因在 test 侧（DV）→ 可直接修复并重跑验证；根因在 main RTL（DE）→ **只交付提案，标注“待用户决策”，不直接改 main**（见 spinal-dv 硬性规则）
8. **归档**：每项改动（含被否决的 DE 提案）写入 `doc/debug_archive/<YYYYMMDD>_<模块>_<问题短名>.md`，模板见下

## 修改记录归档模板（必含字段，DE 决策字段不可省略）

```markdown
# <模块> <问题短名> 修改记录
- 日期：YYYY-MM-DD
- 模块：<包名.组件名>
- 失败现象：<断言/记分板信息，含时刻>
- 波形证据：FST 路径；wawk 程序（全文或路径）；真实关键输出（逐字）；违例时间戳
- 根因归属：自研 / 官方 lib（定位次序结论：黑盒比对证据）
- 改动类型：DV（test）/ DE（main）
- 改动内容：<文件路径 + 行号 + 改动前/后片段>
- DE 用户决策：批准 / 否决 / 待定（DV 改动填“不适用”；DE 提案必填，含决策依据/日期）
- 改后验证：<重跑 testcase 结果 / 修复后波形 wawk 复核输出>
```

## Common Mistakes

| 错误 | 纠正 |
|------|------|
| 用“预期输出”/静态推断代替 wawk 真实运行结果 | 改动门禁：必须实际跑通拿到真实输出，报错先修程序 |
| 根因在 main RTL 却直接修改 | DE 改动只交付提案（标注待用户决策），由用户决定是否修改 |
| 改动不写归档/DE 提案无决策字段 | 每项改动写 doc/debug_archive/ 记录，DE 用户决策字段必填 |
| 首轮就钻 lib 内部信号（fifo.logic_*/RAM 口） | 定位次序：lib 先黑盒只看输入输出，自研排除后才查 lib 内部 |
| 把 lib 输出异常直接判为 lib bug | 先在 lib 边界比对输入：输入已被自研逻辑污染则 lib 无嫌疑 |
| 把 `_zz_*` wire 当根因信号、建议改 Verilog assign | 生成物不可改；沿映射链回到 Scala when 分支 |
| 修复建议给 Verilog 代码片段 | FIX 必须是 Scala 片段（文件+行号） |
| 观察计划列满全部信号含中间变量 | SIGNAL_PLAN 只列用户信号，中间变量过滤 |
| 凭 awk 直觉写 `BEGIN {` | 冒号 `BEGIN: {`，套模板 |
| 用 print 逗号输出多字段 | printf 显式空格/换行 |
| 波形没有某内部信号就断言逻辑缺失 | 先查 SimEnv 是否 simPublic |