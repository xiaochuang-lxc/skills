# SpinalHDL 设计模式实战

> 从 SpinalHDL core/lib 源码中提取的设计机制、设计模式和最佳实践。

---

## A. 核心设计机制（源码解析）

### A1. SpinalHDL 编译流程

SpinalHDL 的编译过程分为以下阶段：

```
Scala 代码执行 → DSL 收集 → IR 构建 → Phase 优化 → 后端发射
```

**阶段详解：**

1. **DSL 收集阶段**：Scala 代码执行时，通过 `DslScopeStack` 收集硬件描述
   - `Component` 构造时 push 到栈上
   - 信号声明、赋值操作记录到 `ScopeStatement`
   - `GlobalData` 保存全局编译状态

2. **IR 构建阶段**：将 DSL 收集结果转换为中间表示
   - `Expression`：表达式节点（运算符、常量、信号引用）
   - `Statement`：语句节点（赋值、条件、switch）
   - `Node`：底层 IR 节点

3. **Phase 优化阶段**：多趟优化 pass
   - 类型推断和位宽传播
   - 常量折叠
   - 内存推断（Mem → BRAM/LUT）
   - 死代码消除
   - 时钟域分析

4. **后端发射阶段**：
   - `ComponentEmitterVerilog` — Verilog 发射
   - `ComponentEmitterVhdl` — VHDL 发射
   - `PhaseVerilog` / `PhaseVhdl` — 后端特定优化

### A2. 类型系统机制

**HardType[T] 延迟构造**：
```scala
// HardType 包装了类型的延迟创建
def apply[T <: Data](hardType: HardType[T]): Stream[T]
def apply[T <: Data](hardType: => T): Stream[T]  // 自动包装为 HardType

// 为什么需要 HardType？
// 1. 避免重复创建类型实例（clone 开销）
// 2. 允许类型信息在编译时传递
// 3. 支持类型推断和缓存
```

**Data 继承链**：
```
Data（所有硬件数据的基类）
├── BaseType（单值类型）
│   ├── Bool
│   ├── BitVector
│   │   ├── Bits
│   │   ├── UInt
│   │   └── SInt
│   ├── SpinalEnumCraft
│   ├── SpinalStruct
│   └── AFix / SFix / UFix
└── MultiData（复合类型）
    ├── Bundle
    ├── Vec
    ├── Union
    └── HardMap
```

**IMasterSlave 方向翻转机制**：
```scala
// Bundle with IMasterSlave 定义了 master 方向
// slave() 翻转所有信号方向
// master() 保持原方向
trait IMasterSlave {
  def asMaster(): Unit    // 定义 master 方向
  def asSlave(): Unit     // 自动翻转（默认实现）
}
```

### A3. Fiber 异步框架

**Handle[T]**：延迟求值的硬件值
```scala
// Handle 允许在硬件生成过程中延迟求值
val handle = Handle { someComputation() }
// handle 的值在首次访问时才计算
```

**Fiber / AsyncThread**：异步硬件生成
```scala
// Fiber 支持在硬件生成过程中进行异步操作
// 用于生成器（Generator）模式
```

**ScopeProperty**：上下文传播
```scala
// ScopeProperty 允许在 DSL 作用域中传播上下文信息
// 类似于动态作用域的变量
val myProp = ScopeProperty(defaultValue)
myProp.set(newValue) {
  // 在此块内 myProp 为 newValue
}
```

---

## B. 设计模式实战

### B4. Stream 驱动设计模式

#### 生产者-消费者模式

```scala
class Producer extends Component {
  val io = new Bundle {
    val output = master(Stream(UInt(8 bits)))
  }
  noIoPrefix()

  val counter = Reg(UInt(8 bits)) init(0)
  io.output.valid := True
  io.output.payload := counter
  when(io.output.fire) {
    counter := counter + 1
  }
}

class Consumer extends Component {
  val io = new Bundle {
    val input = slave(Stream(UInt(8 bits)))
  }
  noIoPrefix()

  val total = Reg(UInt(16 bits)) init(0)
  when(io.input.fire) {
    total := total + io.input.payload
  }
  io.input.ready := True
}

// 连接
class TopLevel extends Component {
  val producer = new Producer
  val consumer = new Consumer
  consumer.io.input << producer.io.output
}
```

#### 流水线插入策略

```scala
// 选择策略取决于时序需求：
// M2S：valid/payload 打拍 → 切断 valid 路径延迟
// S2M：ready 打拍 → 切断 ready 路径延迟
// FULL：全部打拍 → 最大频率，但增加延迟
// HALF：带宽减半 → 最高频率

// 典型用法：在模块输出插入 M2S 打拍
io.output << internalStream.m2sPipe()

// 在模块输入插入 S2M 打拍
internalStream << io.input.s2mPipe()

// 使用 StreamPipe 配置
val pipe = StreamPipe.M2S
io.output << pipe(internalStream)
```

#### 背压传播与死锁避免

```scala
// 规则1：valid 不得组合依赖 ready
// 错误！
when(downstream.ready) {
  stream.valid := True  // valid 依赖 ready → 违规！
}
// 正确
stream.valid := hasData
// valid 独立于 ready

// 规则2：避免循环依赖
// A.ready 依赖 B.valid，B.ready 依赖 A.valid → 死锁！
// 解决：在循环中插入寄存器

// 规则3：FIFO 防死锁
// 当不确定下游是否能接收时，插入 FIFO
stream.queue(4)  // 4 深度 FIFO 缓冲
```

#### 常用组合器模式

```scala
// 类型转换
stream.translateWith(newPayload)  // 替换 payload
stream.map(x => x + 1)           // 函数映射
stream.swapPayload(UInt(16 bits)) // 交换 payload 类型

// 过滤
stream.takeWhen(condition)   // 仅通过满足条件的数据
stream.throwWhen(condition)  // 丢弃满足条件的数据

// 分叉
val (a, b) = (stream, stream.queue(4))  // 两个消费者

// 合并
val merged = StreamArbiterFactory().roundRobin.on(Seq(s1, s2, s3))
```

---

### B5. FSM 状态机设计模式

**来源**：`lib/src/main/scala/spinal/lib/fsm/`

#### 基本用法

```scala
import spinal.lib.fsm._

class MyFsm extends Component {
  val io = new Bundle {
    val start = in Bool()
    val done = out Bool()
    val data = out UInt(8 bits)
  }

  val fsm = new StateMachine {
    val idle: State = new State with EntryPoint {
      whenIsActive {
        io.done := False
        io.data := 0
        when(io.start) {
          goto(process)
        }
      }
    }

    val process: State = new State {
      whenIsActive {
        io.data := io.data + 1
        when(io.data === 255) {
          goto(done_state)
        }
      }
      onEntry {
        // 进入状态时执行
      }
      onExit {
        // 离开状态时执行
      }
    }

    val done_state: State = new State {
      whenIsActive {
        io.done := True
        goto(idle)
      }
    }
  }
}
```

#### 关键 API

| 方法 | 说明 |
|------|------|
| `new State with EntryPoint` | 定义入口状态 |
| `whenIsActive { ... }` | 状态激活时的逻辑 |
| `onEntry { ... }` | 进入状态时执行 |
| `onExit { ... }` | 离开状态时执行 |
| `goto(nextState)` | 转移到下一状态 |
| `isActive(state)` | 查询是否在指定状态 |
| `isEntering(state)` | 查询是否正在进入 |
| `isExiting(state)` | 查询是否正在离开 |

#### 与 Stream 结合

```scala
val fsm = new StateMachine {
  val waitStream: State = new State with EntryPoint {
    whenIsActive {
      when(stream.valid) {
        stream.ready := True
        when(stream.fire) {
          goto(processData)
        }
      }
    }
  }

  val processData: State = new State {
    whenIsActive {
      // 处理 stream.payload
      goto(waitStream)
    }
  }
}
```

---

### B6. Pipeline 流水线设计模式

**来源**：`lib/src/main/scala/spinal/lib/pipeline/`

> **注意**：`spinal.lib.pipeline` 是旧版 API，推荐使用 `spinal.lib.misc.pipeline`。

#### 基本结构

```scala
import spinal.lib.pipeline._

val pip = new Pipeline {
  // 定义 Stageable（流水线中流动的数据）
  val DATA = Stageable(UInt(8 bits))
  val FLAG = Stageable(Bool())

  // 创建阶段
  val stages = Array.fill(3)(new Stage)
  connect(stages)(List(Connection.M2S()))

  val fetch = stages(0)
  val execute = stages(1)
  val writeback = stages(2)

  // 在 fetch 阶段设置数据
  fetch {
    DATA := inputValue
    FLAG := someCondition
  }

  // 在 execute 阶段使用数据
  execute {
    val result = DATA + 1
  }

  // 在 writeback 阶段输出
  writeback {
    io.output := DATA
  }
}
```

#### 连接类型

```scala
Connection.M2S()   // Master-to-Slave：valid/payload 打拍
Connection.S2M()   // Slave-to-Master：ready 打拍
Connection.DIRECT() // 直接连接（组合逻辑）
```

---

### B7. 跨时钟域设计模式

**来源**：`lib/src/main/scala/spinal/lib/CrossClock.scala`（453行）

#### 跨时钟域原语选择

| 原语 | 适用场景 | 延迟 |
|------|---------|------|
| `BufferCC` | 单 bit 信号同步 | 2-3 拍 |
| `PulseCCByToggle` | 脉冲信号跨时钟域 | 不确定 |
| `FlowCCByToggle` | Flow 协议跨时钟域（安全，基于翻转同步） | 2-3 拍 |
| `FlowCCUnsafeByToggle` | Flow 协议跨时钟域（不安全，要求发送速率 < 接收速率） | 2 拍 |
| `StreamCCByToggle` | Stream 协议跨时钟域 | 多拍 |
| `StreamFifoCC` | 数据流跨时钟域（FIFO） | 取决于深度 |

#### 使用示例

```scala
// 单 bit 同步
val syncedSignal = BufferCC(asyncSignal, init = False, bufferDepth = Some(2))

// 脉冲跨时钟域
val pulseOut = PulseCCByToggle(pulseIn, clockIn = fastClock, clockOut = slowClock)

// Flow 跨时钟域
val flowOut = FlowCCByToggle(flowIn, inputClock = fastClock, outputClock = slowClock)

// Stream 跨时钟域
val streamOut = StreamCCByToggle(
  input = streamIn,
  inputClock = fastClock,
  outputClock = slowClock
)

// 异步 FIFO（最常用）
val fifo = StreamFifoCC(
  dataType = UInt(8 bits),
  depth = 16,
  pushClock = fastClock,
  popClock = slowClock
)
fifo.io.push << producerOutput
consumerInput << fifo.io.pop
```

#### Gray 编码在跨时钟域中的应用

```scala
// FIFO 指针使用 Gray 编码避免多位同时变化
Gray.encode(binaryPtr)  // 二进制 → Gray
Gray.decode(grayPtr)    // Gray → 二进制

// StreamFifoCC 内部自动使用 Gray 编码
```

---

### B8. 总线互连架构模式

#### 拓扑选择

| 拓扑 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| 点对点 | 简单，低延迟 | 仅两个设备 | 简单外设 |
| 共享总线 | 资源节省 | 带宽竞争 | 低速设备共享 |
| Crossbar | 全带宽，并行 | 资源开销大 | 高性能互连 |

#### SlaveFactory 寄存器映射模式

```scala
// 统一的寄存器映射模式
val factory = Apb3SlaveFactory(apb3Bus, selId = 0)

// 寄存器定义
factory.read(statusReg, address = 0x00)
factory.write(controlReg, address = 0x04)
factory.readAndWrite(rwReg, address = 0x08)

// 置位/清零语义（写 1 置位 setOnSet / 写 1 保持 clearOnSet）
factory.setOnSet(setReg, address = 0x0C, bitOffset = 0)
factory.clearOnSet(clearReg, address = 0x10, bitOffset = 0)
```

#### RegIf 统一寄存器模式

```scala
// 一套定义，多种总线适配
val busIf = BusInterface(bus, SizeMapping(0x000, 256))
val reg0 = busIf.newReg(doc = "控制寄存器")
val field = reg0.field(UInt(8 bits), AccessType.RW, doc = "数据字段")
```

---

### B9. 模块化设计原则

#### Component vs Area 选择

| 场景 | 选择 | 理由 |
|------|------|------|
| 独立可复用功能 | Component | 独立模块，可实例化多次 |
| 同一时钟域的逻辑分组 | Area | 零开销，共享命名空间 |
| 需要独立仿真的模块 | Component | 可独立生成 Verilog |
| 辅助逻辑（计数器、状态） | Area | 不需要独立接口 |

#### 参数化配置模式

```scala
// 推荐：case class + require
case class MyModuleConfig(
  dataWidth: Int = 32,
  fifoDepth: Int = 16,
  withErrorCheck: Boolean = true
) {
  require(isPow2(fifoDepth))
  require(dataWidth >= 8)
}

class MyModule(config: MyModuleConfig) extends Component {
  import config._
  // 使用配置参数
}
```

#### 接口抽象模式

```scala
// Bundle + IMasterSlave 定义可复用接口
class MyBus extends Bundle with IMasterSlave {
  val addr = UInt(32 bits)
  val data = Bits(32 bits)
  val write = Bool()
  val ready = Bool()

  override def asMaster(): Unit = {
    out(addr, data, write)
    in(ready)
  }
}

// 使用 slave/master 设置方向
val io = new Bundle {
  val cmd = slave(MyBus())
  val rsp = master(MyBus())
}
```

---

### B10. 组合逻辑与寄存器分离原则

> **核心思想**：在 RTL 设计中，功能实现由组合逻辑承接，寄存器仅用于状态记录。代码应尽可能让阅读者不必同时思考时序关系和功能逻辑。

#### 原则说明

| 角色 | 承担者 | 特征 |
|------|----------|------|
| **功能逻辑** | 组合逻辑（`when/switch`、赋值、运算） | 描述“做什么”，无状态 |
| **状态记录** | 寄存器（`Reg`） | 描述“当前状态”，跨周期保持 |

**反模式**：在 `Reg` 的赋值中混合多步功能判断，读者必须同时理解时序和功能：

```scala
// ✘ 反模式：状态跳转 + 数据计算 + 输出控制全部纠缠在 Reg 赋值中
val state = Reg(UInt(3 bits)) init(0)
val result = Reg(UInt(16 bits)) init(0)
val done = Reg(Bool()) init(False)

switch(state) {
  is(0) {
    when(io.start) {
      state := 1
      result := io.a * io.b + io.c
      done := False
    }
  }
  is(1) {
    state := 2
    result := result + io.offset
    done := False
  }
  is(2) {
    when(io.mode === 0) {
      result := result | (result << 2)
    } otherwise {
      result := result ^ io.mask
    }
    state := 3
  }
  is(3) {
    state := 0
    done := True
    io.output := result
  }
}
// 读者必须同时思考：状态如何跳转？每步计算什么？输出何时有效？
```

**正确模式**：组合逻辑定义功能，寄存器仅记录状态：

```scala
// ✔ 正确：状态机、数据通路、输出逻辑各自独立

// 1. 状态机：仅描述状态跳转（“何时切换”）
val state = Reg(UInt(3 bits)) init(0)
switch(state) {
  is(0) { when(io.start) { state := 1 } }
  is(1) { state := 2 }
  is(2) { state := 3 }
  is(3) { state := 0 }
}

// 2. 数据通路：纯组合逻辑描述功能（“做什么”）
val step0Result = io.a * io.b + io.c
val step1Result = resultReg + io.offset
val step2Result = io.mode.mux(
  False -> (resultReg | (resultReg << 2)),
  True  -> (resultReg ^ io.mask)
)
val dataMux = List(step0Result, step1Result, step2Result, resultReg)(state)

// 3. 寄存器：纯状态记录（“何时保持”）
val resultReg = RegNext(dataMux) init(0)
val done = RegInit(False)
when(state === 3) { done := True }
when(state === 0) { done := False }

// 4. 输出：组合逻辑
io.output := resultReg
```

> **注意**：简单逻辑无需强制拆分。例如 `when(cond) { reg := expr }` 这种单条件单赋值，拆分反而增加冗余。分离原则针对的是**多状态、多条件、多功能交织**的复杂场景。

#### 典型应用场景

```scala
// 场景1：带使能的累加器
// ✘ 混合写法
val acc = Reg(UInt(16 bits)) init(0)
when(io.enable) { acc := acc + io.input }

// ✔ 分离写法
val nextAcc = acc + io.input  // 组合逻辑：功能
val acc = RegNextWhen(nextAcc, io.enable) init(0)  // 寄存器：状态

// 场景2：多状态 datapath
// ✘ 混合：状态跳转和功能计算纠缠
val state = Reg(UInt(2 bits)) init(0)
val data = Reg(UInt(8 bits)) init(0)
switch(state) {
  is(0) { when(go) { state := 1; data := input } }
  is(1) { state := 2; data := data * 2 }
  is(2) { state := 0; output := data }
}

// ✔ 分离：状态机 + 数据通路各自独立
// 状态机：仅描述状态跳转
val state = Reg(UInt(2 bits)) init(0)
val nextState = state
switch(state) {
  is(0) { when(go) { nextState := 1 } }
  is(1) { nextState := 2 }
  is(2) { nextState := 0 }
}
state := nextState

// 数据通路：仅描述功能逻辑
val dataNext = data * 2
val data = RegNext(dataNext) init(0)
when(state === 0 && go) { data := input }
when(state === 2) { output := data }
```

#### 设计准则

| 准则 | 说明 |
|------|------|
| 组合逻辑描述功能 | `when/switch`、运算、MUX 全部在组合域完成 |
| 寄存器仅记录状态 | `Reg`/`RegNext`/`RegNextWhen` 只用于跨周期保持 |
| 避免 `Reg` 内嵌复杂逻辑 | 复杂判断先算出组合结果，再 `RegNext` 寄存 |
| 状态机与数据通路分离 | FSM 只管跳转，数据通路只管计算 |
| 命名体现角色 | `funcResult`（组合）vs `resultReg`（寄存器） |

---

### B11. Stream/Flow 数据流抽象

> **核心思想**：电路设计中，应将数据流抽象为 Stream（有反压）或 Flow（无反压），而非手动管理 valid/ready 信号。

#### 为什么需要 Stream/Flow 抽象

Stream/Flow 抽象的核心优势是**将电路模型结构化**，使代码具备强可读性。具体体现在：

| 优势 | 说明 |
|------|------|
| **结构化电路模型** | 数据流被显式建模为 Stream/Flow，模块间关系一目了然 |
| **代码可读性强** | `stream >> fifo >> consumer` 比手动管理 valid/ready 信号清晰得多 |
| **避免凑时序代码** | 防止为了时序收敛而随意插入寄存器，导致逻辑混乱 |
| **设计意图明确** | `m2sPipe()` 明确表达"此处打拍切断组合路径"，而非 `RegNext` 含义不明 |

**反模式：凑时序代码**

在手工管理握手信号的设计中，常见"凑时序"行为——为了时序收敛随意插入寄存器，导致代码可读性极差：

```scala
// ✘ 反模式：凑时序代码，可读性差
val awValidReg = RegNext(io.axi.aw.valid) init(False)
val awReadyReg = RegNext(io.axi.aw.ready) init(False)
val wValidReg = Reg(Bool()) init(False)
when(io.axi.w.valid && !wValidReg) {
  wValidReg := True
}
// 读者疑问：这些寄存器是功能需要还是凑时序？为什么这样打拍？
```

**正确模式：Stream/Flow 结构化**

```scala
// ✓ 正确模式：数据流结构化，设计意图清晰
val awStream = io.axi.aw.m2sPipe()  // 明确：AW 通道打拍
val wStream = io.axi.w.s2mPipe()    // 明确：W 通道反压打拍
val cmdFork = StreamFork(awStream, portCount = 2)

cmdFork(0) >> dataProcessor.io.input
cmdFork(1) >> responseUnit.io.cmd
// 读者一眼看出：数据从哪来、经过什么处理、到哪去
```

> **判断标准**：如果代码中出现大量手动管理的 valid/ready 寄存器和条件判断，且无法一眼看出数据流向，说明缺乏 Stream/Flow 抽象。

#### 抽象原则

| 场景 | 抽象 | 说明 |
|------|------|------|
| 有反压的数据通路 | `Stream[T]` | valid/ready 握手，支持背压 |
| 无反压的事件流 | `Flow[T]` | 仅 valid，不阻塞 |
| 数据分叉到多路 | `StreamFork` | 复制到多个输出，全部消费后才接受下一个 |
| 多路合并 | `StreamArbiter` | 按优先级/轮询选择一路 |
| 跨时钟域 | `StreamFifoCC` | 显式例化 FIFO |

#### 实战示例：AXI4-Lite 写命令分发

**场景**：接收一个写命令（含地址+数据），需向 AXI4-Lite 总线发送 AW 地址通道和 W 数据通道，同时等待 B 写响应。要求全性能（不浪费周期）。

**设计思路**：

```
                     ┌─→ aw Stream ──→ AXI AW 通道
writeCmd ─ StreamFork ─┼─→ w  Stream ──→ AXI W  通道
   (Stream)          └─→ sync ─┬─→ m2sPipe → AXI B 通道（反接握手）
                                │
                          等待 B 响应后才接受下一条命令
```

**实现**：

```scala
class AxiLiteWriteAdapter(axiConfig: Axi4Config) extends Component {
  val io = new Bundle {
    val cmd   = slave(Stream(new Bundle {
      val addr = UInt(axiConfig.addressWidth bits)
      val data = Bits(axiConfig.dataWidth bits)
      val strb = Bits(axiConfig.bytePerWord bits)
    }))
    val axi = master(Axi4(axiConfig))
  }
  noIoPrefix()

  // 1. StreamFork 将命令分叉到 3 路
  //    Fork 语义：所有输出都 fire 后，输入才接受下一条
  val forkOut = StreamFork(io.cmd, portCount = 3, synchronous = false)

  // 2. 输出 0 → AW 地址通道（提取地址字段）
  io.axi.aw.valid      := forkOut(0).valid
  io.axi.aw.addr       := forkOut(0).payload.addr
  io.axi.aw.write      := True
  forkOut(0).ready     := io.axi.aw.ready

  // 3. 输出 1 → W 数据通道（提取数据字段）
  io.axi.w.valid       := forkOut(1).valid
  io.axi.w.data        := forkOut(1).payload.data
  io.axi.w.strb        := forkOut(1).payload.strb
  io.axi.w.last        := True
  forkOut(1).ready     := io.axi.w.ready

  // 4. 输出 2 → 与 B 响应通道反接握手
  //    “反接”：用 B 通道的 valid 反向驱动 fork 输出 2 的 ready
  //    效果：fork 输出 2 一直等到 B 响应到达才消费
  //    这样 Fork 必须等 B 响应才能接受下一条命令
  forkOut(2).ready     := io.axi.b.valid
  io.axi.b.ready       := forkOut(2).valid  // B 通道在 fork 有数据时才 ready

  // 5. 打拍切断组合路径（StreamPipe 提升 FMax）
  //    在 AW/W 通道插入 M2S 打拍，切断 valid→ready 组合环路
  //    实际设计中可在 fork 输出后统一插入：
  //    forkOut(0).m2sPipe() >> io.axi.aw
  //    forkOut(1).m2sPipe() >> io.axi.w
}
```

**关键设计要点**：

| 技术点 | 说明 |
|--------|------|
| `StreamFork(synchronous=false)` | 各输出独立 ready，先到的先采样，额外 1FF/输出 |
| 反接握手 | `forkOut(2).ready := b.valid` 将 B 响应转化为 fork 消费条件 |
| `m2sPipe()` | 切断 valid→ready 组合路径，提升频率（可选） |
| 全性能 | Fork 保证 AW/W 同时发送，不浪费等待周期 |

#### StreamJoin 场景：AXI-Lite Slave 写操作

**场景**：作为 AXI4-Lite Slave，接收写操作。AW 地址通道和 W 数据通道独立到达，需等待两者都就绪后产生 B 写响应。要求全性能。

**设计思路**：

```
AXI aw ─┐
         StreamJoin ─→ b Stream ──→ AXI b 通道（写响应）
AXI w  ─┘
```

**实现**：

```scala
class AxiLiteWriteSlave(axiConfig: Axi4Config) extends Component {
  val io = new Bundle {
    val axi = slave(Axi4(axiConfig))
  }
  noIoPrefix()

  // 1. StreamJoin 等待 AW 和 W 都到达后触发
  //    Join 语义：output.valid = aw.valid && w.valid
  //              aw.ready = w.ready = output.fire
  val joined = StreamJoin(io.axi.aw, io.axi.w)

  // 2. Join 输出驱动 B 响应通道
  //    当 AW 和 W 都有效时，Join fire，产生 B 响应
  io.axi.b.valid := joined.valid
  io.axi.b.resp  := 0  // OKAY
  joined.ready   := io.axi.b.ready

  // 3. 可选：在 Join 和 B 之间插入处理逻辑
  //    例如：写入内部 RAM、检查地址合法性等
  //    when(joined.fire) {
  //      mem.write(joined.payload._1.addr, joined.payload._2.data)
  //    }
}
```

**StreamJoin 关键特性**：

| 特性 | 说明 |
|------|------|
| `output.valid = in0.valid && in1.valid` | 所有输入都有效时输出才有效 |
| `in0.ready = in1.ready = output.fire` | 输出 fire 时所有输入才被消费 |
| 保留 payload | `output.payload._1`/`_2` 包含各输入的原始 payload |
| `StreamJoin.vec(Seq(...))` | 多路同类型 Join，输出 `Stream[Vec[T]]` |
| `StreamJoin.arg(s0, s1, ...)` | 多路 Join 但忽略 payload，输出 `Event` |
| `StreamJoin.fixedPayload(sources, payload)` | Join 并替换为自定义 payload |

> **注意**：`StreamJoin` 要求所有输入同时 valid 才能 fire。对于 AXI 协议中 AW/W 可能独立到达的场景，
> 可在 Join 前插入 `StreamFifo` 缓冲各通道，避免相互阻塞：
> `val awBuf = new StreamFifo(Axi4Aw(axiConfig), depth=4); awBuf.io.push << io.axi.aw`
> `val wBuf  = new StreamFifo(Axi4W(axiConfig), depth=4);  wBuf.io.push << io.axi.w`
> `val joined = StreamJoin(awBuf.io.pop, wBuf.io.pop)`

#### Stream/Flow 抽象的优势

| 手动管理 valid/ready | Stream/Flow 抽象 |
|---------------------|------------------|
| 手动连线，易出错 | `<<` / `>>` 自动连接 |
| 难以组合、拆分 | `StreamFork` / `StreamArbiter` 开箱即用 |
| 时序约束不透明 | `m2sPipe()` / `s2mPipe()` 显式打拍 |
| 跨时钟域复杂 | `StreamFifoCC` 一行搞定 |
| 难以参数化 | `Stream[T]` 的 T 可以是任意 Bundle |

---

### B12. AXI4 通道拆解模式

> **核心思想**：`Axi4` Bundle 内部每个通道（aw/w/b/ar/r）都是独立的 `Stream`，可以像普通 Stream 一样操作、变换、打拍。

#### Axi4 通道结构

```scala
// Axi4 Bundle 内部结构（源码）
case class Axi4(config: Axi4Config) extends Bundle with IMasterSlave {
  val aw = Stream(Axi4Aw(config))  // 写地址通道
  val w  = Stream(Axi4W(config))   // 写数据通道
  val b  = Stream(Axi4B(config))   // 写响应通道（Slave→Master 方向）
  val ar = Stream(Axi4Ar(config))  // 读地址通道
  val r  = Stream(Axi4R(config))   // 读数据通道（Slave→Master 方向）
}
```

**方向规则**：Master 驱动 aw/w/ar（out），Slave 驱动 b/r（in）。`slave()`/`master()` 自动设置所有信号方向。

#### 变体类型

| 类型 | 通道 | 适用场景 |
|------|------|----------|
| `Axi4(config)` | aw + w + b + ar + r | 完整读写 |
| `Axi4WriteOnly(config)` | aw + w + b | 仅写（如 DMA 写内存） |
| `Axi4ReadOnly(config)` | ar + r | 仅读（如 DMA 读内存） |

#### 通道级操作

```scala
val axi = master(Axi4(config))

// 1. 按通道独立打拍
val piped = axi.pipelined(
  aw = StreamPipe.M2S,   // AW 通道 M2S 打拍
  w  = StreamPipe.NONE,  // W  通道不打拍
  b  = StreamPipe.S2M,   // B  通道 S2M 打拍
  ar = StreamPipe.M2S,   // AR 通道 M2S 打拍
  r  = StreamPipe.NONE   // R  通道不打拍
)

// 2. 通道间 Stream 操作（每个通道都是普通 Stream）
val awFifo = new StreamFifo(Axi4Aw(config), depth = 8)
awFifo.io.push << axi.aw            // AW 通道进 FIFO
val awOut = awFifo.io.pop           // 从 FIFO 取出

// 3. 连接操作符
//    master >> slave：Master 驱动 aw/w/ar 到 Slave，Slave 驱动 b/r 回 Master
//    slave  << master：等价于 master >> slave
masterAxi >> slaveAxi   // 全通道连接

// 4. 拆分变体
val wo = axi.toWriteOnly()  // 提取写通道，ar/r 阻塞
val ro = axi.toReadOnly()   // 提取读通道，aw/w/b 阻塞
```

#### 设计要点

| 要点 | 说明 |
|------|------|
| 通道独立 | 每个通道是独立 Stream，可用 StreamFork/Join/Fifo/Arbiter 任意组合 |
| 方向自动 | `>>` 自动处理 aw/w/ar 正向 + b/r 反向 |
| 按需打拍 | `pipelined()` 按通道独立配置，无需全打 |
| 变体拆分 | `Axi4WriteOnly`/`Axi4ReadOnly` 避免无关通道悬空 |

---

### B13. AXI4 Master/Slave 端设计模式

> **核心思想**：Master 端组织命令发送和响应接收；Slave 端接收命令、处理数据、产生响应。两端通过 Stream 抽象实现全性能。

#### Master 端设计

**架构**：

```
                     ┌─→ aw Stream ──→ AXI AW
内部命令 ─ StreamFork ─┼─→ w  Stream ──→ AXI W
              │        └─→ sync ─→ b Stream ←── AXI B（反接握手）
              │
              ├─→ ar Stream ──→ AXI AR
              └─→ r Stream ←── AXI R（直接接收）
```

```scala
class AxiMaster(config: Axi4Config) extends Component {
  val io = new Bundle {
    val wrCmd = slave(Stream(new Bundle {
      val addr = UInt(config.addressWidth bits)
      val data = Bits(config.dataWidth bits)
    }))
    val rdCmd = slave(Stream(new Bundle {
      val addr = UInt(config.addressWidth bits)
    }))
    val rdData = master(Flow(Bits(config.dataWidth bits)))
    val axi = master(Axi4(config))
  }

  // === 写通路 ===
  // StreamFork 将写命令分叉到 AW、W、B-sync 三路
  val wFork = StreamFork(io.wrCmd, portCount = 3, synchronous = false)

  // 输出 0 → AW 通道
  io.axi.aw.valid  := wFork(0).valid
  io.axi.aw.addr   := wFork(0).payload.addr
  io.axi.aw.write  := True
  io.axi.aw.setOKAY()
  wFork(0).ready   := io.axi.aw.ready

  // 输出 1 → W 通道
  io.axi.w.valid   := wFork(1).valid
  io.axi.w.data    := wFork(1).payload.data
  io.axi.w.strb    := B((1 << config.bytePerWord) - 1, config.bytePerWord bits)
  io.axi.w.last    := True
  wFork(1).ready   := io.axi.w.ready

  // 输出 2 ← B 响应（反接握手：等 B 响应才消费写命令）
  wFork(2).ready   := io.axi.b.valid
  io.axi.b.ready   := wFork(2).valid

  // === 读通路 ===
  // AR 通道：直接驱动
  io.axi.ar.valid  := io.rdCmd.valid
  io.axi.ar.addr   := io.rdCmd.payload.addr
  io.axi.ar.setOKAY()
  io.rdCmd.ready   := io.axi.ar.ready

  // R 通道：接收读数据
  io.axi.r.ready   := True  // 无条件接收（或接 FIFO 缓冲）
  io.rdData.valid  := io.axi.r.valid
  io.rdData.payload := io.axi.r.data
}
```

#### Slave 端设计

**架构**：

```
AXI aw ─┐
         StreamJoin ─→ 写处理 ─→ b Stream ──→ AXI b（写响应）
AXI w  ─┘

AXI ar ──→ 读处理 ─→ r Stream ──→ AXI r（读数据）
```

```scala
class AxiSlave(config: Axi4Config) extends Component {
  val io = new Bundle {
    val axi = slave(Axi4(config))
  }

  // === 写通路 ===
  // StreamJoin 等待 AW 和 W 都到达后触发写操作
  val joined = StreamJoin(io.axi.aw, io.axi.w)

  // 写操作：写入内部存储（示例）
  val mem = Mem(Bits(config.dataWidth bits), wordCount = 1024)
  when(joined.fire) {
    mem.write(
      address = joined.payload._1.addr(config.wordRange),
      data    = joined.payload._2.data
    )
  }

  // B 响应：Join fire 后产生写响应
  io.axi.b.valid := joined.valid
  io.axi.b.setOKAY()
  joined.ready   := io.axi.b.ready

  // === 读通路 ===
  // AR 通道接收读命令，查表产生 R 响应
  io.axi.ar.ready := True  // 简化：始终接受读命令
  io.axi.r.valid  := RegNext(io.axi.ar.fire) init(False)
  io.axi.r.data   := mem.readSync(
    address = RegNextWhen(io.axi.ar.addr, io.axi.ar.fire)(config.wordRange)
  )
  io.axi.r.last   := True
  io.axi.r.setOKAY()
}
```

#### Master/Slave 设计准则

| 准则 | 说明 |
|------|------|
| Master 主动发命令 | AW/AR 通道由 Master 驱动 valid，payload 由 Master 决定 |
| Slave 主动发响应 | B/R 通道由 Slave 驱动 valid，payload 由 Slave 决定 |
| 写命令三通道同步 | AW+W 用 StreamFork/StreamJoin 同步，B 用反接握手同步 |
| 读命令两通道独立 | AR 独立发送，R 独立接收，无需同步 |
| 全性能关键 | Fork/Join 保证不浪费周期；简单场景可用 `haltWhen` 串行化 |

---

### B14. AXI4 Top 互联模式

> **核心思想**：Top 层负责 Master 与 Slave 的互连，核心是地址译码和路由。SpinalHDL 提供 `Axi4CrossbarFactory` 自动完成。

#### 点对点连接

最简单的场景：一个 Master 直连一个 Slave。

```scala
class SimpleTop extends Component {
  val io = new Bundle {
    val axi = slave(Axi4(Axi4Config(32, 32, 4)))
  }

  val slave = new AxiSlave(Axi4Config(32, 32, 4))
  // >> 自动连接：aw/w/ar 正向，b/r 反向
  io.axi >> slave.io.axi
}
```

#### Crossbar 多 Master 多 Slave 互连

```scala
class CrossbarTop extends Component {
  val axiConfig = Axi4Config(addressWidth = 32, dataWidth = 32, idWidth = 4)

  val io = new Bundle {
    val master0 = slave(Axi4(axiConfig))
    val master1 = slave(Axi4(axiConfig))
    val slave0  = master(Axi4(axiConfig))  // 外设 0：0x0000_0000 ~ 0x0000_FFFF
    val slave1  = master(Axi4(axiConfig))  // 外设 1：0x0001_0000 ~ 0x0001_FFFF
    val ram     = master(Axi4(axiConfig))  // RAM：  0x1000_0000 ~ 0x1000_FFFF
  }

  val xbar = Axi4CrossbarFactory()

  // 注册 Slave 及其地址映射
  xbar.addSlave(io.slave0, SizeMapping(0x00000000L, 0x10000L))
  xbar.addSlave(io.slave1, SizeMapping(0x00010000L, 0x10000L))
  xbar.addSlave(io.ram,    SizeMapping(0x10000000L, 0x10000L))

  // 注册连接关系：每个 Master 可以访问哪些 Slave
  xbar.addConnection(io.master0, Seq(io.slave0, io.slave1, io.ram))
  xbar.addConnection(io.master1, Seq(io.slave0, io.ram))  // master1 不能访问 slave1

  // 可选：添加打拍提升频率
  xbar.addPipelining(io.master0)(
    ro = (up, down) => down << up.arValidPipe(),
    wo = (up, down) => down << up.awValidPipe()
  )

  xbar.build()
}
```

#### CrossbarFactory API

| 方法 | 说明 |
|------|------|
| `addSlave(axi, mapping)` | 注册 Slave 及地址映射（`SizeMapping(base, size)`） |
| `addSlaves((axi, mapping)*)` | 批量注册 Slave |
| `addConnection(master, slaves)` | 注册 Master 可访问的 Slave 列表 |
| `addConnections((master, slaves)*)` | 批量注册连接 |
| `addPipelining(axi)(ro, wo)` | 为指定 Master 添加打拍 |
| `build()` | 生成互联逻辑（地址译码 + 仲裁 + 路由） |
| `lowLatency` | 设为 `true` 使用低延迟模式（跳过 validPipe） |

#### 互联模式选择

| 场景 | 推荐方案 |
|------|----------|
| 单 Master 单 Slave | `master >> slave` 直连 |
| 单 Master 多 Slave | `Axi4CrossbarFactory` 或手动地址译码 |
| 多 Master 多 Slave | `Axi4CrossbarFactory` 全自动 |
| 需要精确控制时序 | 手动 `StreamFork` + 地址译码 + `StreamArbiter` |

> **注意**：`Axi4CrossbarFactory` 内部自动将 `Axi4` 拆分为 `Axi4ReadOnly` + `Axi4WriteOnly` 分别交叉连接，
> 实现读写通道独立仲裁，最大化带宽利用率。

---

## C. 从 Spec 到代码的工作流

### C10. 设计规格分析流程

**步骤 1：提取接口需求**
- 确定数据流向（输入/输出）
- 选择协议类型：有反压 → Stream，无反压 → Flow
- 确定方向：master/slave
- 定义 Bundle/Interface

**步骤 2：提取功能需求**
- 划分模块边界：每个 Component 单一职责
- 确定层次：顶层 → 子模块 → Area
- 选择状态管理：FSM（顺序控制）还是 Pipeline（数据通路）

**步骤 3：提取性能需求**
- 确定流水线深度（频率 vs 延迟权衡）
- 计算总线带宽需求
- 确定 FIFO 大小（背压缓冲）

**步骤 4：提取时钟需求**
- 规划时钟域划分
- 选择跨时钟域策略（BufferCC/StreamFifoCC/FlowCCByToggle）
- 配置复位策略

**步骤 5：生成代码骨架**
```scala
class TopModule(config: TopConfig) extends Component {
  import config._
  val io = new Bundle {
    val cmd = slave(Stream(CmdType))
    val rsp = master(Stream(RspType))
  }
  noIoPrefix()

  // 子模块实例
  val subModule = new SubModule(subConfig)

  // Stream 连接
  subModule.io.input << io.cmd
  io.rsp <-< subModule.io.output  // 带打拍的连接
}
```

**步骤 6：（可选）验证与仿真 —— 转 spinal-dv skill**

仅当用户明确要求仿真时执行，且**不在本 skill（spinal-de）内编写仿真代码**：切换到 **spinal-dv** skill，加载其 `spinal-sim-reference.md` 获取完整 API（StreamDriver/StreamMonitor/Scoreboard/Phase 等）与 SimEnv 范式（SimEnv 继承 DUT、test 侧调 simPublic、逐 testcase 进程隔离）。

设计侧交付约束：main 源码保持纯净（无 `simPublic`/`import spinal.core.sim._`）；若 test 需观察 `private` 内部成员，最小放宽为 `private[<包名>]`，仅此一处可见性调整。

---

### C11. 常见设计场景模板

#### 外设控制器（APB + RegIf + FSM）

```scala
class PeriphCtrl(config: PeriphConfig) extends Component {
  val io = new Bundle {
    val bus = slave(Apb3(Apb3Config(32, 32)))
    val dataOut = master(Flow(UInt(8 bits)))
    val dataIn = slave(Flow(UInt(8 bits)))
  }
  noIoPrefix()

  val busIf = Apb3BusInterface(io.bus, selId = 0)
  val ctrlReg = busIf.newReg(doc = "控制寄存器").field(UInt(8 bits), AccessType.RW)
  val statusReg = busIf.newRegAt(0x04, doc = "状态寄存器").field(UInt(8 bits), AccessType.RO)

  val fsm = new StateMachine {
    // 状态机逻辑
  }
}
```

#### 数据通路（Stream 流水线）

```scala
class DataPath(config: DataPathConfig) extends Component {
  val io = new Bundle {
    val input = slave(Stream(UInt(config.width bits)))
    val output = master(Stream(UInt(config.width bits)))
  }
  noIoPrefix()

  // 流水线处理
  val stage1 = io.input.map(x => x + 1).m2sPipe()
  val stage2 = stage1.map(x => x * 2).m2sPipe()
  val stage3 = stage2.queue(4)  // FIFO 缓冲
  io.output << stage3
}
```

#### DMA 引擎（Stream + Bus + CrossClock）

```scala
class DmaEngine(config: DmaConfig) extends Component {
  val io = new Bundle {
    val bus = master(Axi4(config.axiConfig))
    val stream = master(Stream(UInt(config.dataWidth bits)))
    val irq = out Bool()
  }
  noIoPrefix()

  // 跨时钟域 FIFO
  val ccFifo = StreamFifoCC(UInt(config.dataWidth bits),
    depth = config.fifoDepth,
    pushClock = busClockDomain,
    popClock = streamClockDomain)

  // 读数据通路
  val readStream = Stream(UInt(config.dataWidth bits))
  // ... AXI 读逻辑
  ccFifo.io.push << readStream

  // 输出
  io.stream << ccFifo.io.pop
}
```

#### 中断控制器（RegIf + 中断工厂）

```scala
class IntCtrl(config: IntConfig) extends Component {
  val io = new Bundle {
    val bus = slave(Apb3(Apb3Config(32, 32)))
    val irqs = in Bits(config.irqCount bits)
    val interrupt = out Bool()
  }
  noIoPrefix()

  val busIf = Apb3BusInterface(io.bus, selId = 0)

  // 中断使能寄存器
  val enableReg = busIf.newReg(doc = "中断使能").field(Bits(config.irqCount bits), AccessType.RW)

  // 中断状态寄存器（写1清零）
  val statusReg = busIf.newReg(doc = "中断状态").field(Bits(config.irqCount bits), AccessType.W1C)

  // 中断逻辑
  statusReg := (statusReg | io.irqs) & enableReg
  io.interrupt := (statusReg & enableReg).orR
}
```

---

## 12. 新版流水线框架（spinal.lib.misc.pipeline）

> **注意**：旧版 `spinal.lib.pipeline`（Pipeline/Stage/Stageable）已废弃，新设计应使用 `spinal.lib.misc.pipeline`。

### 12.1 核心概念

新版 pipeline 框架由三个核心抽象组成：

| 抽象 | 说明 |
|------|------|
| **Payload[T]** | 流水线中传输的数据类型定义（= `NamedType[T]`） |
| **Node** | 流水线中的一个节点（可访问 valid/ready/payload） |
| **Link** | 连接两个 Node 的硬件逻辑（决定打拍、组合、控制等） |

```
Node ──Link──▶ Node ──Link──▶ Node
  ↑              ↑              ↑
  可访问           连接逻辑        可访问
  valid/ready    (StageLink/     valid/ready
  + Payload      CtrlLink/...)   + Payload
```

### 12.2 基本用法：StagePipeline

最简单的方式是用 `StagePipeline` 自动创建打拍级联：

```scala
import spinal.lib.misc.pipeline._

val PAYLOAD_A = Payload(UInt(8 bits))
val PAYLOAD_B = Payload(UInt(16 bits))

val pip = new StagePipeline {
  // 定义各级逻辑（用 new node(i).Area 创建硬件区域）
  new node(0).Area {  // 输入级
    PAYLOAD_A := io.input.payload
    valid := io.input.valid
    io.input.ready := isReady
  }
  new node(1).Area {  // 中间级（自动 M2S 打拍）
    PAYLOAD_B := PAYLOAD_A * 2
  }
  new node(2).Area {  // 输出级
    io.output.payload := PAYLOAD_B
    io.output.valid := isValid
    // isReady 由下游驱动
  }

  // 构建（自动在相邻 node 间插入 StageLink）
  build()
}
```

### 12.3 灵活连接：Node + Link 手动组装

对于复杂拓扑，手动创建 Node 和 Link：

```scala
val n0 = Node()
val n1 = Node()
val n2 = Node()

// n0 逻辑（用 new node.Area 创建硬件区域）
new n0.Area {
  PAYLOAD_A := io.input.payload
  valid := io.input.valid
  io.input.ready := isReady
}

// n1 逻辑
new n1.Area {
  PAYLOAD_B := PAYLOAD_A * 2
}

// n2 逻辑
new n2.Area {
  io.output.payload := PAYLOAD_B
  io.output.valid := isValid
}

// 连接：n0 →(M2S)→ n1 →(组合)→ n2
Builder(
  StageLink(n0, n1),   // M2S 打拍
  DirectLink(n1, n2)   // 组合连接
)
```

### 12.4 CtrlLink — 带流控的级间连接

`CtrlLink` 提供丰富的流控操作，适合 CPU 流水线等需要 halt/throw/bypass 的场景：

```scala
val pip = new StageCtrlPipeline {
  // CtrlLink 0 的上游节点：驱动输入
  new ctrl(0).up.Area {
    PAYLOAD_A := io.input.payload
    valid := io.input.valid
    io.input.ready := isReady
  }

  // CtrlLink 0 流控操作（直接在 CtrlApi 上调用）
  ctrl(0).haltWhen(stallCondition)            // 暂停：up.ready:=False, down.valid:=False
  ctrl(0).throwWhen(errorDetected)            // 丢弃：取消事务 + 通知上游
  val fwd = ctrl(0).bypass(PAYLOAD_A)         // 数据旁路（修复数据冒险）
  when(fwdHit) { fwd := fwdValue }

  // CtrlLink 0 的下游节点：处理后的数据
  new ctrl(0).down.Area {
    PAYLOAD_B := PAYLOAD_A + 1  // PAYLOAD_A 通过 CtrlApi 隐式转换访问
  }

  // CtrlLink 1：下一级
  new ctrl(1).up.Area {
    // 使用 ctrl(1) 的 Payload ...
  }

  build()  // 自动在 ctrl(0).down → ctrl(1).up 间插入 StageLink
}
```

> **注意**：`ctrl(i)` 返回 `CtrlLinkMirror`（CtrlApi），流控方法直接调用；
> `ctrl(i).up`/`ctrl(i).down` 返回 `NodeApi`，需用 `new ctrl(i).up.Area { ... }` 创建硬件区域。

#### CtrlLink 流控 API

| 方法 | 说明 | 效果 |
|------|------|------|
| `haltWhen(cond)` | 暂停事务 | up.ready:=False, down.valid:=False |
| `haltIt()` | 无条件暂停 | 同上（用于 when 块内） |
| `throwWhen(cond, usingReady=false)` | 丢弃事务 | terminate + forgetOne（或 ignoreReady） |
| `throwIt(usingReady=false)` | 无条件丢弃 | 同上 |
| `terminateWhen(cond)` | 仅清除下游 valid | down.valid:=False |
| `terminateIt()` | 无条件终止 | 同上 |
| `duplicateWhen(cond)` | 复制事务（up.ready:=False） | 事务不前进但 down 侧可见 |
| `duplicateIt()` | 无条件复制 | 同上 |
| `forgetOneWhen(cond)` | 通知上游忘记事务 | 不影响 down.valid |
| `forgetOneNow()` | 无条件忘记 | 同上 |
| `ignoreReadyWhen(cond)` | 忽略下游 ready | up.ready:=True |
| `ignoreReadyNow()` | 无条件忽略 | 同上 |
| `bypass(payload)` | 条件覆盖 payload 值 | 用于数据前递（forwarding） |
| `forkStream(forceSpawn, enabled=True)` | 分叉出 Stream[NoData] | 阻塞直到 fork 成功 |
| `forkFlow(enabled=True)` | 分叉出 Flow[NoData] | 不阻塞 |

### 12.5 高级拓扑：ForkLink / JoinLink

```scala
// Fork：一个 Node 分叉到多个
val forkUp = Node()
val forkDown0 = Node()
val forkDown1 = Node()
Builder(
  ForkLink(forkUp, Seq(forkDown0, forkDown1), synchronous = false)
)
// synchronous=false: 各输出可独立 ready（额外 1FF/输出）
// synchronous=true: 所有输出必须同时 ready

// Join：多个 Node 汇合到一个
val joinUp0 = Node()
val joinUp1 = Node()
val joinDown = Node()
Builder(
  JoinLink(Seq(joinUp0, joinUp1), joinDown)
)
// joinDown.valid = joinUp0.isValid && joinUp1.isValid
// joinUp.ready = joinDown.isValid && joinDown.isReady
```

### 12.6 S2MLink — ready 打拍

```scala
// S2M 打拍：ready 信号寄存，valid/payload 组合
Builder(S2MLink(n0, n1))
// 特点：延迟 0 周期，但切断 ready→valid 组合路径
```

### 12.7 Stream/Flow 接口

```scala
// 从 Stream 驱动 Node
val myNode = Node()
myNode.driveFrom(io.inputStream) { (node, payload) =>
  PAYLOAD_A := payload
}
// 或仅连接握手：
myNode.arbitrateFrom(io.inputStream)

// Node 输出为 Stream
val outputStream = myNode.toStream { node =>
  val result = PAYLOAD_A + 1
  result  // 作为 Stream 的 payload
}
// 或仅连接握手：
myNode.arbitrateTo(io.outputStream)

// Flow 版本（无反压）
myNode.arbitrateFrom(io.inputFlow)
val outputFlow = myNode.toFlow { node => PAYLOAD_A }
```

### 12.8 设计指南

| 场景 | 推荐方案 |
|------|----------|
| 简单数据通路（DSP、滤波） | `StagePipeline` + `StageLink` |
| CPU 流水线（需要 bypass/halt） | `StageCtrlPipeline` + `CtrlLink` |
| 混合拓扑（fork/join） | 手动 `Node` + `Builder(...)` |
| 纯组合级间 | `DirectLink` |
| 切断 ready 组合路径 | `S2MLink` |
| 一分多 | `ForkLink(synchronous=false)` |
| 多合一 | `JoinLink` |

### 12.9 旧版→新版迁移指南

> 旧版 `spinal.lib.pipeline`（Pipeline/Stage/Stageable）已废弃，以下为旧版 API 在新版 `spinal.lib.misc.pipeline` 中的对应方案。

#### 流控操作映射

| 旧版 API | 新版对应 | 差异说明 |
|----------|----------|----------|
| `stage.haltIt(cond)` | `ctrl.haltWhen(cond)` | 需使用 CtrlLink（StageLink 无流控） |
| `stage.throwIt(cond, root=true)` | `ctrl.throwWhen(cond)` | 语义更完整：terminate + forgetOne |
| **`stage.flushIt(cond, root=true)`** | **`ctrl.throwWhen(cond)`** | **全局冲刷 → 单点触发 + forgetOne 反向传播** |
| **`stage.flushNext(cond)`** | **`ctrl.forgetOneWhen(cond)`** | **冲刷下级 → 仅通知上游忘记，不清本级** |
| `stage.forkIt(cond)` | `ctrl.duplicateWhen(cond)` | 复制事务：阻塞上游 `up.ready:=False`，下游仍可见 |
| `stage.spawnIt(cond)` | `node.valid := True`（手动） | 生成新事务；新版无专用原语，直接在 Node 中设置 valid |
| `stage.forkStream(cond)` | `ctrl.forkStream(enabled=cond)` | CtrlLink 方法，参数为 `enabled` |
| `stage.forkFlow(cond)` | `ctrl.forkFlow(enabled=cond)` | CtrlLink 方法，不阻塞 |
| `stage.toStream()` | `node.toStream { n => payload }` | 需显式提供 payload 构造闭包 |
| `stage.driveFrom(stream)` | `node.driveFrom(stream) { (n, p) => ... }` | 需显式提供 payload 回调 |
| `stage.driveFrom(stage, cond, values)` | 通过 Link 自动传播 Payload | 旧版手动指定值列表，新版 Link 自动匹配同名 Payload |

#### 数据类型与结构映射

| 旧版 API | 新版对应 | 差异说明 |
|----------|----------|----------|
| `Stageable[T](gen)` | `Payload[T](gen)` | 类型别名从 `HardType` 变为 `NamedType` |
| `new Pipeline` | `new StagePipeline` | 自动创建 StageLink 级联 |
| `new Stage` | `Node()` 或 `pip.node(i)` | 独立 Node 或 StagePipeline 内的编号节点 |
| `stage(STAGEABLE)` | `node(PAYLOAD)` | 访问 Payload 在本级的硬件信号 |
| `stage(STAGEABLE, subKey)` | `node(PAYLOAD, subKey)` | 带子键访问（多通道/多 lane） |
| `stage.insert(value)` | `node.insert(value)` | 创建新 Payload 并连接组合信号 |
| `stage.overloaded(key)` | — | 新版无直接对应，用 `node(PAYLOAD, subKey)` 替代 |
| `stage.resulting(key)` | — | 新版无直接对应，用 `node.insert()` 创建本地结果 |
| `stage.terminal(key)` | — | 新版无直接对应；Payload 传播由 Link 自动管理 |
| `connect(stages)(List(Connection.M2S()))` | `Builder(StageLink(n0, n1))` 或 `StagePipeline.build()` | 手动用 Link 或自动打拍 |
| `Connection.M2S(collapse, holdPayload, flushPreserveInput)` | `StageLink(up, down)` | 新增 `withoutCollapse`/`withPayloadHold`；`flushPreserveInput` 由 CtrlLink `throwWhen(usingReady=true)` 替代 |
| `Connection.S2M()` | `S2MLink(up, down)` | ready 打拍，新增 forgetOne/cancel 条件传播 |
| `Connection.DIRECT()` | `DirectLink(up, down)` | 组合直连，新增 forgetOne/cancel 透传 |
| `Connection.QueueLowLatency(depth)` | — | 新版无内置队列 Link，手动 `Node` + `StreamFifo` 实现 |

#### 事务状态标志映射

| 旧版 API | 新版对应 | 差异说明 |
|----------|----------|----------|
| `stage.isValid` | `node.isValid` | 相同语义 |
| `stage.isReady` | `node.isReady` | 相同语义 |
| `stage.isFiring` | `node.isFiring` | 新版增加 cancel 感知：`isValid && isReady && !isCancel` |
| `stage.isStuck` | — | 用 `isValid && !isReady` 替代 |
| `stage.isChanging` | `node.isMoving` | 语义近似：`isValid && (isReady \|\| isCancel)` |
| `stage.isRemoved` | `node.isCanceling` | 新版：`isValid && isCancel` |
| `stage.isFirstCycle` | — | 用 `isFiring` + 外部 Reg 标志替代 |
| `stage.isFlushed` | — | 新版无 flush 状态标志；用 `isCanceling` 或外部信号替代 |
| `stage.isThrown` | `node.isCanceling` | 近似对应：事务被取消 |
| `stage.isForked` | — | 新版无 fork 状态标志；用 `ctrl.forkStream` 的返回值替代 |
| `stage.isFlushingNext` | — | 新版无对应；用 `forgetOneWhen` 的条件信号替代 |
| `stage.isFlushingRoot` | — | 新版无对应；用 `throwWhen` 的条件信号替代 |
| `stage.isSelfRemoved` | — | 新版无对应；等价于旧版 `isFlushingRoot` |
| — | `node.isCancel` | **新版新增**：cancel 信号只读访问 |
| — | `node.cancel` | **新版新增**：cancel 信号读写（下游驱动） |

#### 冲刷（Flush）机制迁移

**旧版**：每级都有 `flushIt` / `flushNext`，通过全局 flush 信号广播，每级显式检查。

**新版**：无 flush 原语。通过 `throwWhen` / `forgetOneWhen` + `forgetOne` 信号沿 Link **反向传播**实现。

**传播原理**（源码级）：

```
CtrlLink.propagateUp():
  up.ctrl.forgetOneCreate(or(down.ctrl.forgetOne, requests.forgetsOne))
                                ↑ 下游传来的 forgetOne     ↑ 本地 throwWhen 产生的

StageLink.build():
  down.ctrl.forgetOne foreach { cond => down.valid clearWhen (cond) }
                  ↑ 当 down 节点有 forgetOne 时，清除 down.valid
```

**全级冲刷示例**（Stage3 触发，清空 Stage0~3）：

```scala
val pip = new StageCtrlPipeline {
  new ctrl(0).up.Area { /* Stage0 逻辑 */ }
  new ctrl(1).up.Area { /* Stage1 逻辑 */ }
  new ctrl(2).up.Area { /* Stage2 逻辑 */ }
  new ctrl(3).up.Area { /* Stage3 逻辑 */ }

  // ★ Stage3 判断需要冲刷 → 一行代码
  ctrl(3).throwWhen(flushCond)
  // 效果：forgetOne 沿 StageLink 反向传播
  //   Stage3: down.valid := False (terminateWhen)
  //   Stage2: ctrl(2).down.valid clearWhen(flushCond) (forgetOne 传播)
  //   Stage1: ctrl(1).down.valid clearWhen(flushCond) (forgetOne 传播)
  //   Stage0: ctrl(0).down.valid clearWhen(flushCond) (forgetOne 传播)
  // 单周期内全级清空，payload 保留但 valid=0，新数据自然覆盖

  build()
}
```

**局部冲刷示例**（只清 Stage0~1，保留 Stage2~3）：

```scala
// 在 Stage1 触发 forgetOne → 只影响 Stage0~1
ctrl(1).forgetOneWhen(partialFlushCond)
// forgetOne 传播到 Stage0，但不会越过 Stage1 影响 Stage2~3
```

**旧版 vs 新版冲刷对比**：

| 维度 | 旧版 `flushIt` | 新版 `throwWhen` |
|------|----------------|----------------|
| 传播方式 | 全局广播，每级显式检查 | forgetOne 沿 Link 反向逐级传播 |
| 粒度 | 全部清空（不可选择） | 可精确控制：全级/局部/单级 |
| 副作用 | 仅清 valid | 同时通知上游 forget（cancel 语义更完整） |
| 局部冲刷 | 不支持 | `forgetOneWhen(cond)` 只清上游，不清本级 |
| 硬件开销 | 每级需全局 flush 信号线 | 无额外信号线，复用 forgetOne 传播通路 |
