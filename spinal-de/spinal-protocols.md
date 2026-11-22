# SpinalHDL 协议与总线参考

> 从 SpinalHDL lib 源码（558个Scala文件）中提取的协议和总线参考。

---

## A. 核心数据协议

### A1. Stream[T] 协议

**来源**：`lib/src/main/scala/spinal/lib/Stream.scala`（2937行）

#### 接口定义

```scala
class Stream[T <: Data](val payloadType: HardType[T]) extends Bundle with IMasterSlave {
  val valid   = Bool()    // Master 驱动，表示 payload 有效
  val ready   = Bool()    // Slave 驱动，表示可以接收
  val payload = payloadType()  // Master 驱动，数据内容
}
```

#### 握手规则（关键！）

1. **transfer = valid & ready** — 传输仅在两者同时为高时完成
2. **valid 不得组合依赖 ready** — valid 路径必须是寄存器或组合无关的
3. **valid 一旦拉高，直到 ready 响应前不得撤回** — 保证传输完成
4. **ready 可以随时变化** — 包括在 valid 为低时

#### 核心方法速查

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `fire` | valid & ready，传输发生 | Bool |
| `valid` | 数据有效信号 | Bool |
| `ready` | 可接收信号 | Bool |
| `push(that)` | 推送数据（valid := True, payload := that） | Unit |
| `pop()` | 返回 payload，ready := True | T |
| `isStall` | valid && !ready，被阻塞 | Bool |

#### 连接操作符

| 操作符 | 说明 | 延迟 |
|--------|------|------|
| `a << b` | b 连接到 a | 组合 |
| `a >> b` | a 连接到 b | 组合 |
| `a <-< b` | b 通过 M2S 打拍连接到 a | valid/payload 打拍 |
| `a >-> b` | a 通过 M2S 打拍连接到 b | valid/payload 打拍 |
| `a </< b` | b 通过 S2M 打拍连接到 a | ready 打拍 |
| `a >/> b` | a 通过 S2M 打拍连接到 b | ready 打拍 |
| `a <-/< b` | b 通过 FULL 打拍连接到 a | 全部打拍 |
| `a >/-> b` | a 通过 FULL 打拍连接到 b | 全部打拍 |

#### 流水线策略（StreamPipe）

```scala
StreamPipe.NONE   // 组合连接，无延迟
StreamPipe.M2S    // valid/payload 打拍（Master-to-Slave）
StreamPipe.S2M    // ready 打拍（Slave-to-Master）
StreamPipe.FULL   // 全部打拍 = s2mPipe().m2sPipe()（S2M 在前、M2S 在后）
StreamPipe.HALF   // 全部打拍但带宽减半
```

#### 流水线化方法

```scala
stream.m2sPipe()       // valid/payload 寄存器打拍
stream.s2mPipe()       // ready 寄存器打拍
stream.halfPipe()      // 带宽减半的全打拍
stream.combStage()     // 组合级（仅重命名，无逻辑）
stream.pipelined(m2s = true, s2m = true)  // 参数化打拍 = StreamPipe.FULL
```

**双向打拍组合顺序（已核实，spinalhdl-lib 1.11.0）**：同时使用 S2M 与 M2S 时，**S2M 在前（上游侧）、M2S 在后（下游侧）**：

```scala
// ✅ 库标准全切组合（StreamPipe.FULL，Stream.scala:25-27；<-/< 连接符，L155-159）
stream.s2mPipe().m2sPipe()
stream.pipelined(m2s = true, s2m = true)   // = StreamPipe.FULL（L176）
// 多级：S2M×M 在前（原生深度参数 s2mPipe(M)，L414），M2S×N 在后（链式 m2sPipe()）

// ❌ 反序 m2sPipe().s2mPipe()：接口暴露组合逻辑，劣化时序
```

- 理由：s2m 的 `self.ready := rValidN`（寄存器输出）面向上游，m2s 的 `output.valid/payload := rValid/rData`（寄存器输出）面向下游——两侧外部接口均为纯寄存器输出，skid mux/OR 与 collapsBubble OR 全部埋入链内终止于寄存器 D 端
- 反序代价：下游 valid=`rValid||!rValidN`（OR）、payload=Mux，上游 ready=`rValidN||!rValid`（OR）
- 连接符对照（Stream.scala:126-165）：`<-<`/`>->`=m2s（切 valid/payload）；`</<`/`>/>`=s2m（切 ready）；`<-/<`/`>/->`=s2m+m2s（全切）
- 例外：RiscvCore `contextIn.m2sPipe().s2mPipe()` 为 ready 手工驱动（rsp.fire）的特殊场景，非通用范式

#### FIFO 使用（显式例化）

> **规范**：应显式例化 FIFO 组件，不使用 `.queue()` 方法，以便精确控制 FIFO 参数和架构。

```scala
// 同时钟域 FIFO
val fifo = new StreamFifo(payloadType, depth = 16)
fifo.io.push << inputStream
outputStream << fifo.io.pop
// 可选：fifo.io.flush := flushSignal
// 可选：val fill = fifo.io.occupancy
// 可选：val space = fifo.io.availability

// 低延迟 FIFO（读组合通路，latency=0）
val fifoLL = new StreamFifoLowLatency(payloadType, depth = 8)
fifoLL.io.push << inputStream
outputStream << fifoLL.io.pop

// 跨时钟域 FIFO
val fifoCC = new StreamFifoCC(payloadType, depth = 16, pushClock = clkA, popClock = clkB)
fifoCC.io.push << inputStream
outputStream << fifoCC.io.pop

// FIFO 参数选择指南：
// StreamFifo:
//   withAsyncRead=false (默认) → 同步读，latency=2，使用 BRAM
//   withAsyncRead=true          → 异步读，latency=1，使用分布式 RAM
//   withBypass=true             → 空 FIFO 时 bypass push→pop（需 withAsyncRead=true）
//   forFMax=true                → 优化时序以获得最高频率
//   useVec=true                 → 用 Vec[Reg] 代替 Mem（小深度时面积更优）
```

#### 常用组合器

```scala
// 类型转换
stream.toFlow          // Stream → Flow（ready 始终为高）
stream.toEvent()       // Stream → Event（丢弃 payload）
stream.map(x => y)     // 变换 payload 类型

// 条件控制
stream.continueWhen(cond)   // 仅在 cond 为 True 时传输
stream.takeWhen(cond)       // 仅在 cond 为 True 时接受
stream.throwWhen(cond)      // 丢弃 cond 为 True 的数据

// 仲裁与分发
StreamArbiterFactory().roundRobin.on(streams)  // 轮询仲裁
StreamArbiterFactory().lowerFirst.on(streams)  // 优先级仲裁
StreamDispatcherSequential(stream, count)      // 顺序分发

// 连接辅助
stream.driveFrom(that)     // that 驱动 stream
stream.pipelined(pipe)     // 按 StreamPipe 策略打拍
```

#### 代码示例

```scala
// 基本 Stream 使用
val io = new Bundle {
  val input  = slave(Stream(UInt(8 bits)))
  val output = master(Stream(UInt(8 bits)))
}
noIoPrefix()

// 直接连接
io.output << io.input

// 带 FIFO 的连接（显式例化）
val fifo = new StreamFifo(UInt(8 bits), depth = 16)
fifo.io.push << io.input
io.output << fifo.io.pop

// 带流水线打拍的连接
io.output <-< io.input  // M2S 打拍
```

---

### A2. Flow[T] 协议

**来源**：`lib/src/main/scala/spinal/lib/Flow.scala`（332行）

#### 接口定义

```scala
class Flow[T <: Data](val payloadType: HardType[T]) extends Bundle with IMasterSlave {
  val valid   = Bool()           // 数据有效
  val payload = payloadType()    // 数据内容
  // 注意：没有 ready 信号！
}
```

#### 与 Stream 对比

| 特性 | Stream | Flow |
|------|--------|------|
| 反压 | 有（ready） | 无 |
| 握手 | valid & ready | valid only |
| 数据丢失风险 | 无（背压保护） | 有（接收方可能错过） |
| 适用场景 | 数据传输 | 事件通知、状态广播 |
| fire 含义 | valid & ready | valid |

#### 核心方法

| 方法 | 说明 |
|------|------|
| `fire` | = valid（Flow 无 ready，fire 就是 valid） |
| `<<` / `>>` | 连接 |
| `toStream` | 转为 Stream（ready 由外部控制） |
| `toStream(overflow)` | 转为 Stream，溢出指示 |
| `toReg()` | 转为寄存器（锁存最后一次有效值） |
| `toReg(init)` | 带初始值的寄存器 |
| `m2sPipe` | valid/payload 打拍 |
| `combStage()` | 组合级 |

#### 使用场景

```scala
// 事件通知
val interrupt = Flow(Bool())

// 状态广播
val status = Flow(MyStatusBundle())

// Flow → Stream 转换
val stream = flow.toStream()

// Flow → 寄存器（锁存最新值）
val regValue = flow.toReg(initValue)
```

---

### A3. Fragment[T] 协议

**来源**：`lib/src/main/scala/spinal/lib/Fragment.scala`（602行）

#### 接口定义

```scala
class Fragment[T <: Data](val fragmentType: HardType[T]) extends Bundle {
  val last     = Bool()          // 最后一个片段的标志
  val fragment = fragmentType()  // 数据片段
}
// 构造：Fragment(dataType), Stream(Fragment(dataType))
```

#### Stream[Fragment[T]] 完整 API

**来源**：`DataCarrierFragmentPimped`（适用于 Stream/Flow 等所有 DataCarrier）

##### 帧边界检测

| 方法 | 返回 | 说明 |
|------|------|------|
| `first` | `Bool` | 内部寄存器：last 后第一个片段为 True（不含 valid 门控） |
| `tail` | `Bool` | = `!first` |
| `isFirst` | `Bool` | = `valid && first`，当前传输是帧的第一个片段 |
| `isTail` | `Bool` | = `valid && tail`，当前传输是帧的中间/尾部片段 |
| `isLast` | `Bool` | = `valid && last`，当前传输是帧的最后一个片段 |

##### 握手事件

| 方法 | 返回 | 说明 |
|------|------|------|
| `firstFire` | `Bool` | = `fire && first`，帧首片段传输完成 |
| `lastFire` | `Bool` | = `fire && last`，帧末片段传输完成 |

> **firstFire / lastFire 用途**：帧计数器、帧间间隔测量、帧级统计、触发帧级操作（如 DMA 描述符更新）。

##### Stream 专属操作（StreamFragmentPimped）

| 方法 | 签名 | 说明 |
|------|------|------|
| `toStreamOfFragment` | `→ Stream[T]` | 提取纯 payload Stream（去掉 Fragment 包装） |
| `replaceFragmentLast` | `(last: Bool) → Stream[Fragment[T]]` | 替换 last 信号（用于帧重组） |
| `reduce` | `(identity: U, accumulator: (U, U, T) => Unit) → Stream[U]` | 逐步归约（如校验和、奇偶校验） |
| `insertHeader` | `(header: T) → Stream[Fragment[T]]` | 在帧首插入 header（会阻塞上游） |
| `insertHeader` | `(header: Vec[T]) → Stream[Fragment[T]]` | 插入多字 header |
| `toFragmentBits` | `(bitsWidth: Int) → Stream[Fragment[Bits]]` | 拆分为固定位宽的 Fragment[Bits] |

##### Stream[Fragment[Bits]] 专属（StreamFragmentBitsPimped）

| 方法 | 签名 | 说明 |
|------|------|------|
| `toStreamBits` | `(cMagic, cLast) → Stream[Bits]` | 转为 Stream[Bits]（用 magic 字节标记帧边界） |
| `toStreamOf` | `(toDataType: T) → Stream[T]` | 多片段拼接为宽类型（小端拼接） |

##### DataCarrier[Fragment[Bits]] 专属

| 方法 | 签名 | 说明 |
|------|------|------|
| `toRegOf` | `(dataType: T, safeTransition: Boolean=true) → T` | 多片段拼接为寄存器（safeTransition=true 无毛刺） |
| `toFlowOf` | `(dataType: T) → Flow[T]` | 多片段拼接为 Flow（freeRun 模式） |

##### 辅助对象

| 对象 | 签名 | 说明 |
|------|------|------|
| `StreamFragmentArbiter` | `(dataType)(inputs: Seq[Stream[Fragment[T]]]) → Stream[Fragment[T]]` | Fragment 感知仲裁（TransactionLock） |
| `StreamFragmentGenerator` | `(event, packetData: Vec[T], dataType) → Stream[Fragment[T]]` | 从事件+数据向量生成 Fragment 流 |
| `StreamToStreamFragmentBits` | `(dataType, bitsWidth) → Component` | 将宽数据拆分为固定位宽 Fragment[Bits] |
| `StreamFragmentArbiterAndHeaderAdder` | `(dataType)(inputs: Seq[(Stream[Fragment[T]], T)])` | 仲裁 + 自动插入 header |

#### 典型用法

```scala
// 分片传输
val packetStream = Stream(Fragment(UInt(8 bits)))

// 发送多片段数据
packetStream.valid := True
packetStream.fragment := dataByte
packetStream.last := isLastByte

// 帧边界检测
val frameStart = packetStream.firstFire   // 帧首传输完成
val frameEnd   = packetStream.lastFire    // 帧末传输完成
val frameCount = Counter(1024)
when(frameEnd) { frameCount.increment() }

// 帧归约（计算校验和）
val checksum = packetStream.reduce[SInt](S(0), (acc, prev, data) => {
  acc := prev + data.asSInt
})
// checksum 仅在 lastFire 时输出有效值

// 多片段拼接为宽类型
val word32 = packetBits.toStreamOf(UInt(32 bits))
```

#### 应用场景

- **数据包分割/重组**：大数据包拆分为固定宽度片段
- **AXI-Stream TLAST**：`last` 对应 TLAST 信号
- **帧边界检测**：`firstFire`/`lastFire` 标识帧起止
- **帧级统计**：用 `firstFire` 清零计数器，`lastFire` 锁存结果
- **帧归约运算**：`reduce` 计算校验和、奇偶校验等

---

### A4. Event 协议

```scala
// Event = Stream[NoData] — 纯握手事件
val event = Event
event.valid := someCondition
event.ready := downstreamReady

// 无反压的纯事件通知
val pulse = Flow(Bool())  // 无反压的单 bit 事件
```

---

### A5. 协议选择决策表

| 场景 | 推荐协议 | 理由 |
|------|---------|------|
| 有反压的数据传输 | `Stream[T]` | ready 保证数据不丢失 |
| 无反压的数据/通知 | `Flow[T]` | 简单，无背压开销 |
| 分片/包传输 | `Stream[Fragment[T]]` | last 标识帧边界 |
| 纯事件/握手 | `Event` | 无 payload 开销 |
| 跨时钟域数据 | `Stream` + `StreamFifoCC` | 安全跨时钟域 |
| 状态广播 | `Flow[T]` | 多消费者，无需反压 |
| 寄存器锁存 | `Flow[T]` + `toReg()` | 自动锁存最新值 |

---

## B. 总线协议

### B6. AMBA 系列

#### APB3/APB4 — 低速外设总线

```scala
// APB3 接口（真实类名 Apb3 / Apb3Config，源码 APB3.scala）
case class Apb3(config: Apb3Config) extends Bundle with IMasterSlave {
  val PADDR     = UInt(config.addressWidth bits)
  val PSEL      = Bits(config.selWidth bits)   // 注意：Bits，非 Bool
  val PENABLE   = Bool()
  val PREADY    = Bool()
  val PWRITE    = Bool()
  val PWDATA    = Bits(config.dataWidth bits)
  val PRDATA    = Bits(config.dataWidth bits)
  val PSLVERROR = if(config.useSlaveError) Bool() else null  // 可选
}

// APB3 SlaveFactory — 寄存器映射
val factory = Apb3SlaveFactory(apb3Bus, selId = 0)
factory.read(statusReg, address = 0x00)
factory.write(controlReg, address = 0x04)
// 注：BusSlaveFactory 无 multiCycleWrite，只有 read / write（读写共用地址即分别调 read+write）
```

#### AXI4 — 高性能总线

```scala
// AXI4 接口（源码：spinal/lib/bus/amba4/axi/Axi4.scala）
case class Axi4(config: Axi4Config) extends Bundle with IMasterSlave {
  val aw = Stream(Axi4Aw(config))   // 写地址通道（注意：Axi4Aw，非 Axi4AW）
  val w  = Stream(Axi4W(config))    // 写数据通道
  val b  = Stream(Axi4B(config))    // 写响应通道
  val ar = Stream(Axi4Ar(config))   // 读地址通道（注意：Axi4Ar，非 Axi4AR）
  val r  = Stream(Axi4R(config))    // 读数据通道
}

// AXI4 SlaveFactory
val factory = Axi4SlaveFactory(axi4Bus)
factory.read(statusReg, address = 0x00)
factory.write(controlReg, address = 0x04)
```

#### AXI4-Lite

```scala
// 独立的 AxiLite4 类型（源码：spinal/lib/bus/amba4/axilite/AxiLite4.scala）
// 注意：aw 与 ar 共用同一 payload 类型 AxiLite4Ax
case class AxiLite4(config: AxiLite4Config) extends Bundle with IMasterSlave {
  val aw = Stream(AxiLite4Ax(config))  // 写地址（也是读地址类型）
  val w  = Stream(AxiLite4W(config))
  val b  = Stream(AxiLite4B(config))
  val ar = Stream(AxiLite4Ax(config))  // 读地址，与 aw 同类型
  val r  = Stream(AxiLite4R(config))
}
```

---

### B7. 其他总线

| 总线 | 特点 | 典型应用 |
|------|------|---------|
| Wishbone | 开源标准，简单 | RISC-V SoC |
| Avalon | Intel/Altera 生态 | Intel FPGA |
| TileLink | RISC-V 一致性总线 | RISC-V 多核 |
| BMB | SpinalHDL 内部高效总线 | SpinalHDL SoC |
| BRAM | 块存储接口 | FPGA BRAM |
| BSB | 字节流总线 | 流数据处理 |

---

### B8. RegIf 寄存器接口框架

**来源**：`lib/src/main/scala/spinal/lib/bus/regif/`（48文件）

#### 核心概念

RegIf 提供统一的寄存器定义抽象，一套定义适配多种总线。

```scala
// 创建 BusIf
val busIf = Apb3BusInterface(apb3, selId = 0)
// 或
val busIf = AxiLite4BusInterface(axi, selId = 0)
// 或
val busIf = AhbLite3BusInterface(ahb)
// 或
val busIf = WishboneBusInterface(wb)
```

#### 支持的总线适配器

- `Apb3BusInterface` — APB3
- `Apb4BusInterface` — APB4
- `AhbLite3BusInterface` — AHB-Lite
- `AxiLite4BusInterface` — AXI4-Lite
- `WishboneBusInterface` — Wishbone
- `BRAMBusInterface` — BRAM
- `MemBusInterface` — 通用内存总线
- `MinBusInterface` — 最小总线

#### 寄存器定义

```scala
val busIf = Apb3BusInterface(io.bus, selId = 0)

// 基本寄存器（newReg/field 的名字由 val 名通过 SymbolName 宏自动捕获）
val reg0 = busIf.newReg(doc = "控制寄存器0")
val field1 = reg0.field(UInt(8 bits), AccessType.RW, doc = "字段1")
val field2 = reg0.field(Bool(), AccessType.RW, doc = "使能位")

// 只读寄存器（无 fieldRO，只读用 AccessType.RO）
val reg1 = busIf.newRegAt(0x10, doc = "状态寄存器")
val status = reg1.field(UInt(16 bits), AccessType.RO, doc = "状态")

// 写1清零寄存器
val reg2 = busIf.newReg(doc = "中断清除")
val clearBits = reg2.field(UInt(8 bits), AccessType.W1C)
```

#### 访问类型

| 类型 | 说明 |
|------|------|
| `RW` | 读写 |
| `RO` | 只读 |
| `WO` | 只写 |
| `W1C` | 写1清零 |
| `RS` | 读置位 |
| `RC` | 读清零 |
| `WRC` | 写后清零 |
| `W1S` | 写1置位 |

#### 寄存器实例类型

| 类型 | 说明 |
|------|------|
| `RegInst` | 普通寄存器 |
| `FifoInst` | FIFO 寄存器 |
| `RamInst` | RAM 寄存器 |
| `RdFifoInst` | 读FIFO（只读） |
| `WrFifoInst` | 写FIFO（只写） |
| `VirtualRegInst` | 虚拟寄存器（自定义读写逻辑） |

#### 中断控制器

```scala
// 中断工厂：regNamePre 前缀 + 触发信号(Bool*)，返回汇聚后的 IRQ 输出
// 内部自动生成 Enable / Mask / Status 寄存器（RFMS4 方案）
val irq = busIf.interruptFactory("uart", io.rxReady, io.txDone)
```

支持的中断方案：S1, MS2, MMS3, OMS3, RFMS4, IntrRFMMS5 等。

#### 文档自动生成

```scala
// 生成文档：输出文件名（不含扩展）传给构造，BusIf 传给 generate
// 输出路径 = busIf.docPath/<name>.<suffix>
DocHtml("reg_doc").generate(busIf)         // → <docPath>/reg_doc.html
DocJson("reg_doc").generate(busIf)         // → <docPath>/reg_doc.json
DocCHeader("regs").generate(busIf)         // → <docPath>/regs.h
DocSystemRdl("regs").generate(busIf)       // → <docPath>/regs.rdl
```

---

### B9. 总线互连模式

```scala
// Decoder — 地址解码（源码：Apb3Decoder.scala）
// 参数：master 总线 + (slave, 地址映射) 序列
val decoder = Apb3Decoder(
  master = apb3Master,
  slaves = Seq(
    slaveA -> SizeMapping(0x0000, 256),
    slaveB -> SizeMapping(0x1000, 256)
  )
)

// Arbiter — 仲裁器（源码：Axi4Arbiter.scala）
// AXI4 无统一 Arbiter，按方向分别使用：
val readArb  = Axi4ReadOnlyArbiter(outputConfig = axiConfig, inputsCount = 2)
val writeArb = Axi4WriteOnlyArbiter(outputConfig = axiConfig, inputsCount = 2)
// APB3 无 Arbiter，需用 Crossbar 或手动仲裁

// Crossbar — 交叉开关（源码：Axi4Crossbar.scala）
// 使用工厂模式：addSlave 注册地址映射 + addConnection 注册连接 + build 生成
val xbar = Axi4CrossbarFactory()
xbar.addSlave(slaveA, SizeMapping(0x0000, 0x10000))
xbar.addSlave(slaveB, SizeMapping(0x1000_0000L, 0x10000))
xbar.addConnection(masterA, Seq(slaveA, slaveB))
xbar.addConnection(masterB, Seq(slaveA))
xbar.build()
// 详细用法见 spinal-design-patterns.md B14

// 桥接
val bridge = new Apb3ToBmb(apb3Config)                                  // 单参数 class，无伴生 apply
val bridge2 = Axi4SharedToApb3Bridge(addressWidth = 32, dataWidth = 32, idWidth = 4)  // 三个 Int
```

---

## C. 通信外设

### C10. 通信外设概览

| 外设 | Controller | 总线适配 |
|------|-----------|---------|
| UART | `UartCtrl` | `Apb3UartCtrl`, `BmbUartCtrl` |
| SPI Master | `SpiMasterCtrl` | `Apb3SpiMasterCtrl`, `BmbSpiXdrMasterCtrl` |
| SPI Slave | `SpiSlaveCtrl` | `Apb3SpiSlaveCtrl`, `WishboneSpiSlaveCtrl` |
| I2C | `I2cSlave` | `Apb3I2cCtrl`, `BmbI2cCtrl` |
| JTAG | `JtagTap` | `JtagTapFactory` |
| Ethernet | `MacEth` | `BmbMacEth` |
| USB | `UsbDeviceCtrl` | - |
| SWD | `SwdDp` | - |

```scala
// 示例：APB3 UART 控制器（源码：com/uart/Apb3UartCtrl.scala）
// 注意：配置类是 UartCtrlMemoryMappedConfig，非 UartCtrlConfig
val uartCtrl = new Apb3UartCtrl(UartCtrlMemoryMappedConfig(
  uartCtrlConfig = UartCtrlGenerics(),
  initConfig = UartCtrlInitConfig(
    baudrate = 115200,
    dataLength = 7,          // 数据位宽
    parity = UartParityType.NONE,
    stop = UartStopType.ONE
  )
))
uartCtrl.io.apb <> apb3Bus
uartCtrl.io.uart <> io.uart
```
