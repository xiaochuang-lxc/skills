# SpinalSim 仿真参考手册

> **加载时机**：本手册仅在用户明确要求仿真/验证时加载。架构设计与代码生成阶段无需加载。
> **源码依据**：`core/src/main/scala/spinal/core/sim/`（package.scala、SimBootstraps.scala、ClockDomain.scala）+ `lib/src/main/scala/spinal/lib/sim/`

## 1. 仿真配置与启动

### 1.1 SimConfig — 仿真入口

```scala
import spinal.core._
import spinal.core.sim._

SimConfig
  .withConfig(SpinalConfig(nameWhenByFile = false, genLineComments = true, mergeSyncProcess = false)) // 工程约定三件套必设，见下方说明
  .withWave               // 记录波形（默认 VCD）
  .withWaveDepth(2)       // 波形层次深度（0=全部）
  .compile(new MyTop)     // 编译 DUT（Verilator 后端）
  .doSim { dut =>
    dut.clockDomain.forkStimulus(10)   // 10 时间单位周期的时钟
    // 测试主体
  }
```

**工程约定三件套：`nameWhenByFile = false` + `genLineComments = true` + `mergeSyncProcess = false`（DE/DV 一致，必须）**。默认 true 时 when/switch 条件信号被命名为 `when_<文件>_l<行号>`/`switch_<文件>_l<行号>`（when.scala:79/153，1.11.0 已核实）；false 时条件信号不命名，落入匿名 `_zz_*` 中间变量。配套 genLineComments=true 使生成 RTL 每条赋值语句行尾带 `// @ <文件>.scala l<行号>` 注释（Statement.scala:322 + ComponentEmitterVerilog.scala:679），RTL↔Scala 映射改由注释承载；mergeSyncProcess=false 使每个寄存器独立 always 块（ComponentEmitter.scala:202 分组键含寄存器自身），RTL 结构与 Scala 寄存器一一对应。对波形调试的影响：条件信号不再携带源码行号线索，波形定位一律以用户定义信号（Scala val 名）为准，`_zz_*`/匿名条件信号只作过滤对象；需回溯源码时读生成 RTL 的行尾注释定位 Scala 行号。

### 1.2 SpinalSimConfig 完整 API

**后端选择**（默认 Verilator）：

| 方法 | 后端 | 说明 |
|------|------|------|
| `.withVerilator` | Verilator | C++ 编译，最快，`'x'/'z'` 随机化 |
| `.withGhdl()` | GHDL | VHDL 仿真（生成 VHDL） |
| `.withIVerilog` | Icarus Verilog | 开源 VPI 仿真 |
| `.withVCS` / `.withVCS(flags)` | Synopsys VCS | 商业仿真 |
| `.withXSim` | Xilinx XSim | Vivado 仿真（支持 xci/bd） |

**波形控制**：

| 方法 | 说明 |
|------|------|
| `.withWave` | 默认格式（Verilator→VCD，VCS→VPD） |
| `.withWave(depth: Int)` | 波形 + 深度限制 |
| `.withVcdWave` / `.withFstWave` / `.withFsdbWave` / `.withVPDWave` | 指定格式 |
| `.withWaveDepth(depth)` | 波形层次深度（0=全深度） |
| `.waveFilePrefix(prefix)` | 波形文件名前缀 |

**编译与工作区**：

| 方法 | 说明 |
|------|------|
| `.workspacePath(path)` | 工作区路径（默认 `./simWorkspace`，或 `SPINALSIM_WORKSPACE` 环境变量） |
| `.workspaceName(name)` | 工作区名称（默认 toplevel 名） |
| `.withConfig(spinalConfig)` | 传入 SpinalConfig（SimBootstraps.scala:844 已核实）；**工程约定必传 `SpinalConfig(nameWhenByFile = false, genLineComments = true, mergeSyncProcess = false)`** |
| `.addRtl(path)` / `.addIncludeDir(dir)` | 附加 Verilog 源/头文件 |
| `.addSimulatorFlag(flag)` / `.addRunFlag(flag)` | 传给仿真器/运行时标志 |
| `.noOptimisation` / `.fewOptimisation` / `.normalOptimisation` / `.allOptimisation` | Verilator 优化等级（默认 0） |
| `.disableCache` | 禁用编译缓存 |
| `.withCoverage` | Verilator 覆盖率 |
| `.withTimeScale(t)` / `.withTimePrecision(t)` / `.withTimeSpec(scale, precision)` | 时间单位/精度 |
| `.setTestPath(path)` | 测试输出路径（`$WORKSPACE`/`$COMPILED`/`$TEST` 变量） |

### 1.3 doSim 系列

| 方法 | 说明 |
|------|------|
| `.doSim { dut => ... }` | 运行仿真（body 线程结束后自动结束） |
| `.doSim("testName") { dut => ... }` | 指定测试名（用于波形文件命名） |
| `.doSim(seed) { dut => ... }` | 指定随机种子 |
| `.doSim("name", seed) { dut => ... }` | 同时指定 |
| `.doSimUntilVoid { dut => ... }` | 等所有 fork 线程结束后才结束（用于自驱动测试） |

> **seed 规则**：默认随机 seed；可用 `SPINAL_SIM_SEED` 环境变量固定。仿真内 `simRandom` 与该 seed 关联，保证可复现。

## 2. 信号读写

### 2.1 赋值（# =）

```scala
dut.io.valid #= true                    // Bool ← Boolean
dut.io.payload #= 42                    // UInt/Bits ← Int/Long
dut.io.payload #= BigInt("DEADBEEF", 16)// 大位宽 ← BigInt
dut.io.payload #= Array[Byte](...)      // BitVector ← 字节数组
dut.myEnum #= MyEnum.sIDLE              // SpinalEnum ← 枚举元素
dut.myUfix #= 3.14                      // UFix/SFix/AFix ← Double/BigDecimal
```

### 2.2 读取

```scala
dut.io.valid.toBoolean                  // Bool → Boolean
dut.io.payload.toInt                    // BitVector → Int
dut.io.payload.toLong                   // BitVector → Long
dut.io.payload.toBigInt                 // BitVector → BigInt
dut.myEnum.toEnum                       // → SpinalEnumElement
dut.myUfix.toBigDecimal                 // UFix/SFix/AFix → BigDecimal
```

### 2.3 随机化

```scala
dut.io.payload.randomize()              // 随机赋值，返回随机值
dut.io.someBundle.randomize()           // Data.randomize → 递归随机化所有叶子
simRandom.nextInt(100)                  // 专用随机源（与 seed 关联）
```

### 2.4 访问内部信号 — simPublic

```scala
// 硬件侧（生成阶段）：
val internalCounter = Reg(UInt(8 bits))
internalCounter.simPublic()             // 暴露给仿真
val mem = Mem(Bits(32 bits), 1024)
mem.simPublic()                         // 暴露 Mem

// 仿真侧（doSim 内）：
val c = dut.internalCounter.toInt       // 直接读写

// 错误提示：未 simPublic 的信号访问会报 UNACCESSIBLE SIGNAL
```

### 2.5 Mem 仿真读写

```scala
dut.mem.simPublic()                     // 硬件侧先暴露
// 仿真侧（doSim 内）：
dut.mem.setBigInt(address = 5, data = 0x1234)  // 写
val v = dut.mem.getBigInt(address = 5)         // 读
```

## 3. 时钟域 API

### 3.1 时钟激励

```scala
dut.clockDomain.forkStimulus(10)        // 周期 10 时间单位（默认复位 16 周期）
dut.clockDomain.forkStimulus(10 MHz)    // 按频率
dut.clockDomain.forkStimulus()          // 需 ClockDomain 有 FixedFrequency
```

**复位行为**：`forkStimulus` 自动处理复位——ASYNC 复位先拉高 16 周期再释放；SYNC 复位在时钟运行中保持 16 周期；BOOT 复位无信号。

### 3.2 等待原语

| 方法 | 说明 |
|------|------|
| `cd.waitSampling()` / `cd.waitSampling(n)` | 等有效采样沿（复位释放 + 时钟使能 + 有效边沿） |
| `cd.waitSamplingWhere(cond)` | 等满足条件的采样沿 |
| `cd.waitSamplingWhere(timeout)(cond)` | 带超时（返回 true=超时） |
| `cd.waitRisingEdge()` / `cd.waitRisingEdge(n)` | 等上升沿（不受复位影响） |
| `cd.waitFallingEdge(n)` / `cd.waitEdge(n)` | 等下降沿/任意沿 |
| `cd.waitActiveEdge(n)` | 等 ClockDomain 配置的有效沿 |
| `cd.waitRisingEdgeWhere(cond)` | 等满足条件的上升沿 |

### 3.3 回调注册（无线程开销）

| 方法 | 说明 |
|------|------|
| `cd.onSamplings { ... }` | 每个有效采样沿执行（多回调共享一个敏感器） |
| `cd.onNextSampling { ... }` | 仅下一个采样沿执行一次 |
| `cd.onSamplingWhile { ... }` | 反复执行直到返回 false |
| `cd.onRisingEdges` / `cd.onFallingEdges` / `cd.onEdges` / `cd.onActiveEdges` | 对应边沿回调 |

### 3.4 复位/使能控制

```scala
dut.clockDomain.assertReset()           // 拉高复位
dut.clockDomain.deassertReset()         // 释放复位
dut.clockDomain.isResetAsserted         // 查询复位状态
dut.clockDomain.isSamplingEnable        // 复位释放且时钟使能有效
dut.clockDomain.forkSimSpeedPrinter()   // 每秒打印仿真速度（k cycles/s）
```

## 4. 线程与调度

```scala
fork {                                  // 创建新仿真线程
  while(true) { dut.io.x #= simRandom.nextBoolean(); cd.waitSampling() }
}

forkJoin(task1 _, task2 _)              // 并行执行并等待全部完成

sleep(100)                              // 线程睡眠 100 时间单位
sleep(1 ms)                             // 支持时间字面量

waitUntil(dut.io.done.toBoolean)        // 等条件为真（忙等敏感）

forkSensitive { ... }                   // 值变化即执行（无线程）
forkSensitiveWhile { cond }             // 值变化执行直到返回 false
forkSensitive(dut.io.x) { ... }         // 指定信号变化触发
forkSensitive2(dut.io.a, dut.io.b) { ... }  // 多信号触发

delayed(100) { ... }                    // 100 时间单位后执行一次
periodically(10) { ... }                // 每 10 时间单位执行

simTime()                               // 当前仿真时间
simDeltaCycle()                         // 当前 delta cycle 数
```

**线程 vs 敏感器**：`fork`+`wait` 是线程 API（直观但慢）；`forkSensitive`/`onSamplings` 是无线程 API（快）。`StreamDriver`/`StreamMonitor` 内部用无线程实现。

## 5. 仿真流程控制

```scala
simSuccess()                            // 立即成功结束
simFailure("msg")                       // 立即失败结束
SimTimeout(10000)                       // 10000 时间单位后超时失败（防挂死）
SimTimeout(1 ms)                        // 时间字面量

val mutex = SimMutex()                  // 仿真互斥锁
mutex.lock() / mutex.unlock() / mutex.await()
val mutex = SimMutex(randomized = true) // 随机唤醒顺序（测试调度鲁棒性）
```

## 6. Stream 仿真库（spinal.lib.sim）

### 6.1 StreamDriver — 驱动 valid/payload

```scala
import spinal.lib.sim._

// 方式 1：回调驱动（返回 true 表示 payload 有效）
StreamDriver(dut.io.input, dut.clockDomain) { payload =>
  if (queue.nonEmpty) { payload #= queue.dequeue(); true }
  else false                            // false → valid 拉低等待
}

// 方式 2：队列驱动
val (driver, cmdQueue) = StreamDriver.queue(dut.io.input, dut.clockDomain)
cmdQueue.enqueue(p => p.data #= 0xAB)   // 依次入队

// 方式 3：从集合驱动
StreamDriver.fromIterable(dut.io.input, dut.clockDomain, Seq(1, 2, 3))
```

**驱动节奏控制**：

```scala
val driver = StreamDriver(dut.io.input, dut.clockDomain) { p => ... }
driver.setFactor(0.5f)                  // 每周期 50% 概率发送（1.0=每拍发）
driver.setFactorPeriodically(100)        // 每 100 周期随机化概率
driver.transactionDelay = () => 5        // 自定义间隔周期数
```

### 6.2 StreamMonitor — 监视 fire 事件

```scala
StreamMonitor(dut.io.output, dut.clockDomain) { payload =>
  println(s"fire: ${payload.toInt}")
  score.pushRef(payload.toInt)          // 典型用法：接入记分板
}
```

### 6.3 StreamReadyRandomizer — 随机化 ready

```scala
StreamReadyRandomizer(dut.io.output, dut.clockDomain)
  .setFactor(0.7f)                      // 70% 概率 ready
// 或带条件：
StreamReadyRandomizer(dut.io.output, cd) { () => someCondition }
```

### 6.4 StreamDriverOoo — 乱序突发驱动

```scala
val ooo = StreamDriverOoo(dut.io.cmd, dut.clockDomain)
ooo.burst { push =>
  push { p => p.addr #= 0x1000 }        // 突发内保序
  push { p => p.addr #= 0x1004 }
}
ooo.single { p => p.addr #= 0x2000 }    // 单事务
// 多个 burst/single 之间乱序调度
```

### 6.5 SimStreamAssert — 协议断言

```scala
new SimStreamAssert(dut.io.stream, dut.clockDomain)
// 断言：valid 保持期间 payload 不变；ready 后 valid 才可变
```

## 7. Flow 仿真库

```scala
FlowDriver(dut.io.input, dut.clockDomain) { payload => ... }
FlowDriver.queue(flow, cd)               // 队列驱动
FlowDriver.fromIterable(flow, cd, Seq(...))
FlowMonitor(dut.io.output, dut.clockDomain) { payload => ... }
```

## 8. ScoreboardInOrder — 有序记分板

```scala
val score = ScoreboardInOrder[Int]()

// 参考模型侧（输入监视）
StreamMonitor(dut.io.input, dut.clockDomain) { p =>
  score.pushRef(myModel(p.toInt))        // 参考值入队
}

// DUT 侧（输出监视）
StreamMonitor(dut.io.output, dut.clockDomain) { p =>
  score.pushDut(p.toInt)                 // DUT 值入队，两侧对头即比对
}

// 结束检查（配合 Phase 或手动调用）
score.checkEmptyness()                   // 队列非空 → 失败并打印差异（注意官方拼写少一个 i，已源码核实 Scoreboard.scala:62，1.11.0；checkEmptiness 不存在）
```

**比对语义**：`pushRef`+`pushDut` 各自入队，两侧都有数据时立即比较队头；不匹配打印 REF/DUT 并 `simFailure`。

## 9. Phase — 阶段化管理

```scala
import spinal.lib.sim.Phase

Phase.boot()                             // 在 doSim 体内首先调用
Phase.setup { /* 初始化：Fork 时钟、驱动 */ }
Phase.stimulus { /* 激励主体 */ }
Phase.flush { /* 排空 FIFO 等残余 */ }
Phase.check { /* 终检：score.checkEmptyness() */ }
// check 阶段全部线程结束后自动进入 end 阶段并 simSuccess（object Phase.end 为 private，不直接调用）

// Phase 内的线程自动被追踪，全部完成后进入下一阶段
Phase.stimulus.retainer(1).release()     // 手动控制阶段推进
```

**阶段顺序**：`setup → stimulus → flush → check → end`。未使用 Phase 时需手动调用 `checkEmptyness()`（官方拼写少一个 i，勿写成 checkEmptiness）。

## 10. SparseMemory 与区域分配

```scala
// SparseMemory 位于 spinal.lib.bus.amba4.axi.sim（非 spinal.lib.sim）
import spinal.lib.bus.amba4.axi.sim.SparseMemory

val mem = SparseMemory()
mem.write(0x1000, 0x12.toByte)                   // 单字节写（按 1MB 页分配）
mem.read(0x1000)                                 // → Byte
mem.writeBigInt(0x1000, BigInt(0x12345678), width = 4)  // 多字节写（小端）
mem.readBigInt(0x1000, length = 4)               // → BigInt
mem.writeArray(0x2000, byteArray)                // 字节数组写
mem.readArray(0x2000, 4)                         // → Array[Byte]
mem.loadBinary(0x0, "boot.bin")                  // 加载二进制文件

// MemoryRegionAllocator 位于 spinal.lib.sim
import spinal.lib.sim.MemoryRegionAllocator
val alloc = MemoryRegionAllocator(base = 0x10000000L, size = 0x10000)
val region = alloc.allocate(size = 256)          // 随机分配 SizeMapping
alloc.free(region)
alloc.isAllocated(addr)
```

## 11. SimData — 结构化快照

```scala
val snapshot = SimData.copy(dut.io.someBundle)
snapshot("fieldA")                       // 读字段值（BigInt）
snapshot("fieldA") = 42                  // 写字段值
snapshot.check(dut.io.someBundle)        // 与当前硬件值比对 → Boolean
snapshot.write(dut.io.someBundle)        // 将快照写回硬件
```

## 12. 完整示例

### 12.1 StreamFifo 仿真（driver + monitor + scoreboard）

```scala
import spinal.core._
import spinal.core.sim._
import spinal.lib._
import spinal.lib.sim._

object StreamFifoSim extends App {
  SimConfig.withWave.compile(new StreamFifo(Bits(8 bits), depth = 16)).doSim { dut =>
    dut.clockDomain.forkStimulus(10)
    SimTimeout(100000)                   // 防挂死

    val score = ScoreboardInOrder[Int]()

    // 输入驱动：随机数据
    StreamDriver(dut.io.push, dut.clockDomain) { p =>
      p.randomize(); true                // 每拍都发
    }

    // 随机反压
    StreamReadyRandomizer(dut.io.pop, dut.clockDomain).setFactor(0.5f)

    // 输入监视 → 参考值
    StreamMonitor(dut.io.push, dut.clockDomain) { p =>
      score.pushRef(p.toInt)
    }
    // 输出监视 → DUT 值
    StreamMonitor(dut.io.pop, dut.clockDomain) { p =>
      score.pushDut(p.toInt)
    }

    // 运行足够周期
    dut.clockDomain.waitSampling(200)
    score.checkEmptyness()               // 残余事务 → 失败
  }
}
```

### 12.2 复位后检查 + 内部信号访问

```scala
SimConfig.compile(new MyDut).doSim { dut =>
  dut.clockDomain.forkStimulus(10)

  // 主动复位测试
  dut.clockDomain.assertReset()
  dut.clockDomain.waitSampling(5)
  dut.clockDomain.deassertReset()
  dut.clockDomain.waitSamplingWhere(dut.io.busy.toBoolean == false)

  // 内部计数器检查（需硬件侧 simPublic()）
  waitUntil(dut.internalCounter.toInt == 100)
  simSuccess()
}
```

## 13. 常见陷阱

| 陷阱 | 对策 |
|------|------|
| 访问内部信号报 UNACCESSIBLE SIGNAL | 硬件侧调用 `.simPublic()`，并确保信号有名字 |
| 赋值在 `forkStimulus` 之前 | 先 `forkStimulus`（内部会给时钟/复位初值）再驱动信号 |
| `doSim` body 结束但 fork 线程未完 | 用 `doSimUntilVoid`（等全部线程） |
| 波形无信号 | `.withWave` + `withWaveDepth(0)` 全深度 |
| 复位期间采样无效 | `waitSampling` 不含复位期；用 `waitRisingEdge` 跳过复位 |
| `simRandom` 与全局 Random 混用 | 仿真内只用 `simRandom`（seed 关联可复现） |
| 仿真挂死无提示 | 在开头加 `SimTimeout(周期数)` |
| 仿真线程内读 `.fire`/`.first` 报 NPE（signalCache） | 读 valid/ready 后 Scala 层算 fire（§14.5，已源码核实） |
| `case class SimEnv extends case class DUT` 编译报错 | DUT 为 case class 时 SimEnv 用普通 class（§15） |
| `clockDomain.fork` 编译报错 | 用 sim 包级 `fork { }`（§15） |
| `checkEmptiness` 编译报错 | 官方 API 拼写为 `checkEmptyness()`（§8，已源码核实） |

## 14. 线程唤醒与写入时序语义（已源码核实，SpinalHDL 1.11.0，无需重复探索）

> **本节结论已按「依赖源码核实流程」从本工程同版本 sources.jar 逐文件核实并推演，后续会话直接采用，不必再次解压探索。**
> 依据：`sim/spinal/sim/SimManager.scala`、`SimThread.scala`、`SimVerilator.scala`、`core/spinal/core/sim/package.scala`、`ClockDomain.scala`、`lib/spinal/lib/sim/Stream.scala`。

### 14.1 主循环执行顺序（一切时序的根源）

`SimManager.runWhile`（SimManager.scala:285-349）每个迭代**严格按以下顺序**：

1. **执行到点线程**（`tPtr2.call()`，:295-305）——含时钟翻转线程 `DoClock` 与所有被唤醒的用户线程
2. **硬件求值** `if(forceDeltaCycle) raw.eval()`（:307-324）——`forceDeltaCycle` 由**上一迭代**的写入置位
3. **应用写入** `commandBuffer.foreach(_())`（:326-333）——所有 `#=` 在此真正落到 raw 信号，并置 `forceDeltaCycle=true`
4. **处理敏感器** sensitivities（:335-347）——`forkSensitive`/`waitUntil`/`onSamplings` 的条件在此检查

关键：**线程执行(1) 先于 求值(2)**；`#=` 写入是**缓冲**的（`setLong/setBigInt` 仅入队 commandBuffer，SimManager.scala:178-192），不当场生效。

### 14.2 唤醒相位：读到的是「沿前快照」

- `waitSampling()`（package.scala:856-871）= `waitUntil{时钟跳变到有效沿 && isSamplingEnable}`；`waitUntil`（SimThread.scala:28-43）注册敏感器，条件真时以 **delay 0** 把线程排入调度。
- 时钟沿写入在迭代 N 的(3)应用 → 迭代 N 的(4)敏感器看到新沿 → 线程排入 **迭代 N+1 的(1)**（同一仿真时刻、下一 delta）。
- 迭代 N+1 的(1)线程运行时，(2)eval **尚未**执行 → DUT 输出仍是上一次 eval 的结果，即**本沿之前的稳定状态**。

**结论：`waitSampling()`/`onSamplings` 唤醒后读到的是「沿前值」——正是本时钟沿所采样的值。** 沿本身的寄存器更新发生在该线程读完之后的(2)。

### 14.3 写入相位：下一沿生效

线程内 `#=` 入 commandBuffer，在本迭代(3)应用、下一迭代(2)才 eval → **写入在下一个时钟沿才被 DUT 采样**。

### 14.4 同沿多线程无竞争（Verilator）

- 同一沿唤醒的所有线程/回调都在(1)/(4)读，读到的是**同一份沿前快照**；任何写入都缓冲到(3)统一应用。
- Verilator `isBufferedWrite=false`（SimVerilator.scala:109）→ `readBypass=null`（SimManager.scala:139）→ 读直接走 raw，**不会读到本拍刚写的新值**。
- 因此「同一 wake 内读 {valid, fire, length, cfg, 内部寄存器}」是一致快照，可安全做逐拍参考模型比对。（VPI 后端 `isBufferedWrite` 可能为 true，readBypass 会前递写入值，语义略有差异；本工程用 Verilator。）

### 14.5 由此时序得出的测试平台写法（直接套用）

- **监视握手**：`clockDomain.waitSampling(); if (s.valid.toBoolean && s.ready.toBoolean) { 捕获 s.payload }` —— 恰好捕获**本沿**发生的一次传输，payload 正确。`StreamMonitor`（Stream.scala:28-48，onSamplings 实现）即此语义。
- **驱动握手**：`s.payload #= x; s.valid #= true; clockDomain.waitSamplingWhere(s.ready.toBoolean)` —— `waitSamplingWhere(cond)`（package.scala:873-885）在沿前判 cond，等到 ready=1 的沿即完成传输，随后拉低 valid。工程 `DataBusShiftSimEnv.sendPkg` 即此写法。
- **逐拍白盒账本比对**：同一 wake 读 {valid, fire=valid&&ready, length, cfg, 内部寄存器}（沿前一致快照）→ 按 DUT 状态机算期望次态 → **下一 wake** 比对实际寄存器。内部寄存器须先在硬件侧 `.simPublic()`（package.scala:373，BaseType 级；`Vec[Reg]` 需 `foreach(_.simPublic())`）。
- **复位**：`waitSampling`/`onSamplings` 受 `isSamplingEnable = 复位释放 && clockEnable`（package.scala:1212）门控；`forkStimulus(period)` 默认复位 16 周期（package.scala:1074）。复位后用 `waitSampling(n)` 跳过。
- **防挂死**：开头 `SimTimeout(周期数*周期)`。
- **结束**：自驱动多线程用 `doSimUntilVoid`；记分板用 `ScoreboardInOrder.checkEmptyness()` 终检（官方拼写少一个 i，已核实 Scoreboard.scala:62）。
- **仿真线程内禁读懒生成信号**：`Stream.fire`（lib Stream.scala:308）、`DataBus.first` 等基于 `signalCache` 的 def 在仿真线程内调用会 NPE——`signalCache` 首行即取 `Component.current.userCache`（core Misc.scala:167-171），仿真阶段 `Component.current` 为 null，**无论是否已缓存都崩**。正确做法：读 `valid`/`ready` 原始信号后在 Scala 层算 `val fire = valid.toBoolean && ready.toBoolean`（本节上文 fire=valid&&ready 即此意）；工程自身 SimEnv 均此写法。

## 15. 仿真代码目录组织与 SimEnv 范式（工程约定，必须遵守）

**仿真相关代码一律放 `src/test/scala` 下，镜像 main 的包目录；main 源码不混入任何仿真代码。**

- **目录镜像**：main `src/main/scala/libext/bus/dataBus/DataBusShift.scala` → test `src/test/scala/libext/bus/dataBus/DataBusShiftSimEnv.scala` + `DataBusShiftTest.scala`。包名与 main 一致（如 `package libext.bus.dataBus`）。
- **SimEnv 范式**：`case class XxxSimEnv(...) extends Xxx(...)`——SimEnv **继承 DUT**、位于 test 侧，封装 `init()`/驱动/监视/记分板/参考模型；需观察的内部信号在 **SimEnv 内**调 `.simPublic()`（实例：`BitMaoSimEnv extends BitMap` 内 `bitmapMem.mem.simPublic()`）。**若 DUT 本身是 case class，SimEnv 必须用普通 class**（Scala 2.11 禁止 case-to-case 继承，编译报错；已实践验证）。
- **线程 fork 用 sim 包级函数**：`fork { ... }`（`spinal.core.sim._` 导入，core sim/package.scala:233）；**不存在 `clockDomain.fork`**（Component 内 `clockDomain` 是硬件 `Handle[ClockDomain]`，无 fork 成员，已编译验证）；`clockDomain.forkStimulus` 是仿真扩展方法，两者勿混淆。
- **main 保持纯净**：不在 main 写 `simPublic`/`import spinal.core.sim._`。若 DUT 内部成员为 `private` 而 test 需观察，最小放宽为 `private[<包名>]`（包内可见，对外封装不变），由同包 SimEnv 调 simPublic；仅此一处可见性调整，不加仿真逻辑。
- **Test 范式**：`class XxxTest extends org.scalatest.FunSuite`；`val dutCompiled = SimConfig.withWave/withFstWave.compile(XxxSimEnv(...))` 复用编译产物，多个 `test("...") { dutCompiled.doSim { dut => ... } }` 组织 testcase。
- **命名**：`XxxSimEnv`（环境/驱动/监视/模型）与 `XxxTest`（testcase 组织）分离；信号/方法命名随工程风格。

## 16. 运行环境、FST 多仿真崩溃隔离与日志范式（已实践验证）

### 16.1 sbt 运行 SpinalSim 必须 fork

- `build.sbt` 需 `Test / fork := true`（VerilatorBackend.checks 强制要求，否则报「without SBT fork := true」）；建议 `Test / javaOptions += "-Xmx2g"`。
- 本工程 sbt 未全局安装，用 IDEA 内置 sbt-launch.jar 启动：`java -Xms512m -Xmx2g -classpath "<IDEA>/plugins/Scala/launcher/sbt-launch.jar" xsbt.boot.Boot Test/compile`（勿加 `-batch`）。

### 16.2 Verilator FST 多仿真 SIGSEGV 与逐例进程隔离

- **现象**：Verilator 5.030 下同一 JVM 进程内连续多次 `doSim`（用 `withFstWave`），第 3 次起在 `VerilatedTrace<VerilatedFst,...>::addModel` 原生 SIGSEGV（FST 写入器含进程级全局状态，多模型累积损坏）。单进程单仿真正常。
- **修复**：每个 testcase 独立 JVM 进程。`Test / testGrouping` 对 `testOnly` 不一定生效；可靠做法是脚本逐例调用 `testOnly <Suite> -- -z "<完整用例名>"`（每次 sbt 启动即新进程）。用**完整用例名**避免 `-z` 子串误匹配（如 "T4 Stream" 是 "T4 StreamPiped" 子串）。
- 编译产物用 `lazy val`，使每进程仅编译所需 DUT（Verilator 二进制有磁盘缓存，重复编译很快）。
- VCD（`withWave`）无此崩溃，但工程要求 FST 时用逐例隔离而非降级 VCD。

### 16.3 仿真日志范式（失败日志是除波形外的重要定位手段）

- **双输出**：控制台 + 逐 case 文件（如 `simWorkspace/logs/<caseName>.log`）；**逐行 flush**，保证崩溃/断言失败前的上下文已落盘。
- **断言先落盘再抛出**：封装 `check(cond, msg)`，失败时先 `log("[ASSERT-FAIL] "+msg)` 再 `assert(false, msg)`——否则 SpinalSim 只把异常打到控制台，不进日志文件。
- **关键事件**：init 配置、cfg 变更、每笔输入/输出握手（port/seq/len）、账本周期快照（每 N 拍 credit/loaded/hasCredit/eligible/needRefill）、终检汇总（各端口 in/out 字节/份额/剩余包数）。
- SpinalSim 线程协作式调度（同一时刻仅一个线程执行），日志写入天然串行，无需加锁。`simTime()` 仅在仿真线程上下文有效。
- 每 testcase 独立进程、单 env 时，可用文件级全局 logger 对象（`SimLog`）统一入口。

## 17. 调度器公平性/字节配比测量方法学（重要陷阱）

- **陷阱**：「全部包消费完后测每端口输出字节份额」不能验证 Q 比例——若每端口输入包都被完整输出，则**输出字节=输入字节**，由入队长度决定，与调度 Q 无关（等包数+随机长度→份额趋近相等）。
- **正确**：在**满压力稳态窗口**测量——各端口备足量包使窗口内始终背压（不提前耗尽），跑固定拍数后测字节份额/配比，**不要求全消费**。最小包长端口须备远多于大包端口的包数（字节∝包数×包长）。
- 定长包且包长整除 Q 时，每轮每端口字节=Q，长期比例精确；随机长度时误差≤MAX_PACKET/轮，需足够轮数收敛。
- 单端口饱和且 Q=len 时 `need_refill` 可**持续为 1**（唯一有效端口每拍 fire、loaded 恒 1、credit 恒 0），此为状态机正确行为（无死锁）；「need_refill 至多单拍脉冲」仅在「存在未 fire 的有效端口」时成立，**不可作为普适断言**。
