# SpinalHDL API 参考手册

> 从 SpinalHDL 源码系统性提取的完整 API 索引，按 Class/Object 组织。
> 每个条目包含：构造参数、完整 API 签名、使用场景。

---

## 第一部分：Core 类型系统

### 1. Data — 所有硬件类型基类

**源码**：`core/src/main/scala/spinal/core/Data.scala`

```scala
abstract class Data extends Nameable with ImplicitArea with ContextUser with ScalaLocated with OwnableRef
```

| 方法 | 签名 | 使用场景 |
|------|------|----------|
| `:=` | `(that: T)(implicit loc: Location): Unit` | 标准硬件赋值（VHDL `<=`） |
| `===` | `(that: T): Bool` | 硬件相等比较 |
| `=/=` | `(that: T): Bool` | 硬件不等比较 |
| `=::=` | `(that: T): Bool` | 仿真用相等比较（Scala 层面） |
| `<>` | `(that: T)(implicit loc: Location): Unit` | 自动连接（根据 in/out 方向匹配） |
| `init` | `(that: T): T` | 设置寄存器初始值 |
| `initNull` | `(that: T): T` | 仅当 that 非 null 时初始化 |
| `initZero` | `(): T` | 初始值为 0 |
| `default` | `(that: => T): T` | 设置默认值（when/switch 中） |
| `\=` | `(that: T): T` | 组合逻辑赋值（返回组合值） |
| `copyDirectionOf` | `(that: T): Unit` | 复制方向 |
| `assignDontCare` | `(): this.type` | 赋值为 don't care |
| `isUnknown` | `(): Bool` | 检查是否为未知值 |
| `asBits` | `(): Bits` | 转为 Bits |
| `assignFromBits` | `(value: Bits): T` | 从 Bits 赋值 |
| `isReg` | `(): Boolean` | 是否为寄存器 |
| `isComb` | `(): Boolean` | 是否为组合逻辑 |
| `isIo` | `(): Boolean` | 是否为 IO |
| `getWidth` | `(): Int` | 获取位宽 |
| `flatten` | `(): Seq[BaseType]` | 展平为基础类型序列 |
| `flattenForeach` | `(f: BaseType => Unit): Unit` | 遍历所有基础类型 |
| `getZero` | `(): this.type` | 获取零值 |
| `setAll` | `(): this.type` | 所有位置 1 |
| `clearAll` | `(): this.type` | 所有位置 0 |
| `clone` | `(): this.type` | 克隆类型 |
| `setName` | `(name: String): this.type` | 设置信号名称 |
| `setPartialName` | `(name: String, dupeGuard: Boolean = false): this.type` | 设置部分名称 |
| `addTag` | `(tag: SpinalTag): this.type` | 添加 Tag |
| `addAttribute` | `(attribute: Attribute): this.type` | 添加综合属性 |
| `simPublic` | `(): this.type` | 暴露给仿真访问 |
| `dontSimplifyIt` | `(): this.type` | 禁止编译器优化 |
| `setAsAnalog` | `(): this.type` | 标记为模拟信号 |
| `setAsReg` | `(): this.type` | 标记为寄存器 |
| `allowPruning` | `(): this.type` | 允许编译器剪枝 |
| `randBoot` | `(): this.type` | 仿真随机初始化 |

---

### 2. Bool — 布尔类型

**源码**：`core/src/main/scala/spinal/core/Bool.scala`

```scala
class Bool extends BaseType with DataPrimitives[Bool]
// 构造：Bool(), True, False
```

| 方法 | 签名 | 使用场景 |
|------|------|----------|
| `&&` / `&` | `(b: Bool): Bool` | 逻辑与 |
| `\|\|` / `\|` | `(b: Bool): Bool` | 逻辑或 |
| `!` / `~` | `(): Bool` | 逻辑非 |
| `^` | `(b: Bool): Bool` | 异或 |
| `set` | `(): Unit` | 赋值为 True |
| `clear` | `(): Unit` | 赋值为 False |
| `setWhen` | `(cond: Bool): Bool` | 当 cond=True 时置 True |
| `clearWhen` | `(cond: Bool): Bool` | 当 cond=True 时置 False |
| `riseWhen` | `(cond: Bool): Bool` | 当前=False 且 cond=True 时置 True |
| `fallWhen` | `(cond: Bool): Bool` | 当前=True 且 cond=True 时置 False |
| `toggleWhen` | `(cond: Bool): Bool` | 当 cond=True 时翻转 |
| `rise` | `(initAt: Bool): Bool` | 上升沿检测（带初始值） |
| `fall` | `(initAt: Bool): Bool` | 下降沿检测 |
| `edge` | `(initAt: Bool): Bool` | 任意边沿检测 |
| `edges` | `(initAt: Bool): BoolEdges` | 完整边沿 → `BoolEdges(rise, fall, toggle)` |
| `?` | `[T <: Data](whenTrue: T): MuxBuilder[T]` | 条件选择器（配合 `\|` / `otherwise`） |
| `mux` | `[T <: Data](t: T, f: T): T` | 三元选择器 |
| `asUInt` | `(): UInt` / `(bitCount: BitCount): UInt` | 转为 UInt |
| `asSInt` | `(): SInt` | 转为 SInt |
| `asBits` | `(): Bits` / `(bitCount: BitCount): Bits` | 转为 Bits |
| `#*` | `(count: Int): Bits` | 重复 count 次 |

---

### 3. BitVector — 位向量基类

**源码**：`core/src/main/scala/spinal/core/BitVector.scala`

```scala
abstract class BitVector extends BaseType with DataPrimitives[BitVector]
// Bits / UInt / SInt 的公共基类
```

| 方法 | 签名 | 使用场景 |
|------|------|----------|
| `msb` / `lsb` | `Bool` | 最高/最低位 |
| `high` | `Int` | 最高位索引 |
| `bitsRange` | `Range` | `0 until getWidth` |
| `orR` / `andR` / `xorR` | `(): Bool` | 归约操作 |
| `norR` / `nandR` / `nxorR` | `(): Bool` | 归约操作（取反） |
| `andMask` | `(cond: Bool): this.type` | cond=False 时清零 |
| `orMask` | `(cond: Bool): this.type` | cond=True 时全置 1 |
| `xorMask` | `(cond: Bool): this.type` | cond=True 时取反 |
| `rotateLeft` | `(that: Int): T` / `(that: UInt): T` | 左旋转 |
| `rotateRight` | `(that: Int): T` / `(that: UInt): T` | 右旋转 |
| `resize` | `(width: Int): BitVector` / `(width: BitCount): BitVector` | 调整位宽 |
| `asBools` | `(): Vec[Bool]` | 转为 Vec[Bool] |
| `asBool` | `(): Bool` | 转为 Bool（需 1 位） |
| `take` / `takeLow` | `(n: Int): Bits` | 取最低 n 位 |
| `drop` / `dropLow` | `(n: Int): Bits` | 去掉最低 n 位 |
| `takeHigh` | `(n: Int): Bits` | 取最高 n 位 |
| `dropHigh` | `(n: Int): Bits` | 去掉最高 n 位 |
| `splitAt` | `(n: Int): (Bits, Bits)` | 在 n 处分割 → (高位, 低位) |
| `sliceBy` | `(divisor: Int*): List[Bits]` | 按位宽分割 |
| `subdivideIn` | `(sliceCount: SlicesCount): Vec[T]` | 等分为 n 段 |
| `subdivideIn` | `(sliceWidth: BitCount): Vec[T]` | 按宽度切分 |
| `reversed` | `(): this.type` | 位序反转 |
| `setAllTo` | `(value: Boolean): this.type` / `(value: Bool): this.type` | 所有位设置 |
| `apply` | `(bitId: Int): Bool` | 位选择（固定索引） |
| `apply` | `(bitId: UInt): Bool` | 位选择（动态索引） |
| `apply` | `(offset: Int, bitCount: BitCount): this.type` | 范围选择（固定） |
| `apply` | `(offset: UInt, bitCount: BitCount): this.type` | 范围选择（动态） |
| `apply` | `(range: Range): this.type` | Range 方式选择 |

---

### 4. Bits / UInt / SInt

详见 `spinal-syntax.md` 第1章。核心差异：

| 类型 | 特有操作 |
|------|----------|
| **Bits** | `##`(拼接), `#*`(重复), 完整移位(8种), `toDataType`, `aliasAs`, `resizeLeft` |
| **UInt** | `+^`/`-^`(安全算术), `+\|`/`-\|`(饱和), `@@`(拼接), `@*`(重复), `wrap`(环绕比较), 定点数系列(sat/trim/floor/ceil/round/fixTo), `expand`, `intoSInt`, `twoComplement`, `assignMask`, `clearedLow` |
| **SInt** | `unary_-`(取负), `sign`(符号位), `symmetry`(对称化), `expand`(符号扩展), `@@`(拼接), `twoComplement`, fixTo 额外支持 `sym` 参数 |

---

### 5. SpinalEnum / Bundle / Vec / Mem / BlackBox / Component / Reg / SpinalConfig

详见 `spinal-syntax.md` 第1-9章和第12章。

---

## 第二部分：Stream / Flow / Fragment 协议

### 6. Stream[T] — 握手协议

**源码**：`lib/src/main/scala/spinal/lib/Stream.scala`（2938行）

```scala
class Stream[T <: Data](val payloadType: HardType[T]) extends Bundle with IMasterSlave with DataCarrier[T]
```

**构造**：`Stream(payloadType)`, `Stream(hardType)`, `Stream(=> T)`

**核心信号**：

| 信号 | 类型 | 方向 | 说明 |
|------|------|------|------|
| `valid` | `Bool` | master→slave | 数据有效 |
| `ready` | `Bool` | slave→master | 从机可接收 |
| `payload` | `T` | master→slave | 数据负载 |

#### 状态查询

| 方法 | 返回 | 说明 |
|------|------|------|
| `fire` | `Bool` | `valid && ready`，传输发生 |
| `isStall` | `Bool` | `valid && !ready`，有数据但从机未就绪 |
| `isFree` | `Bool` | `!valid \|\| ready`，总线空闲 |
| `isNew` | `Bool` | 新传输首周期 |

#### 连接操作符

| 操作符 | 语义 | 延迟 | 切断信号 |
|--------|------|------|----------|
| `<<(that)` / `>>(into)` | 直连 | 0 | 无 |
| `<-<(that)` / `>->(into)` | M→S 打拍 | 1 | valid/payload |
| `</<(that)` / `>/>(into)` | S→M 打拍 | 0 | ready |
| `<-/<(that)` / `>/->(into)` | 全打拍 | 2 | 双向 |

#### 流水线阶段

| 方法 | 参数 | 代价 | 延迟 |
|------|------|------|------|
| `combStage()` | — | 0 FF | 0 |
| `stage()` | — | payload+1 FF | 1 |
| `m2sPipe(collapsBubble=true, crossClockData=false, flush=null, holdPayload=false, keep=false, initPayload=null)` | 见参数 | payload+1 FF | 1 |
| `s2mPipe(flush=null, keep=false, savePower=false)` | 见参数 | payload+1 FF + MUX | 0 |
| `s2mPipe(stagesCount: Int)` | 级联数 | N×(payload+1 FF) | 0 |
| `halfPipe(flush=null, keep=false)` | — | payload+2 FF | 1 |
| `validPipe(keep=false)` | — | 1 FF | 1 |
| `pipelined(m2s=false, s2m=false, halfRate=false)` | 布尔参数 | 按参数 | 按参数 |
| `pipelined(pipe: StreamPipe)` | StreamPipe 枚举 | 按 pipe | 按 pipe |
| `delay(cycleCount: Int)` | 周期数 | N×(payload+1) FF | N |

#### 数据操作

| 方法 | 签名 | 说明 |
|------|------|------|
| `map` | `[T2 <: Data](f: T => T2): Stream[T2]` | 函数映射 payload |
| `translateWith` | `[T2 <: Data](that: T2): Stream[T2]` | 替换 payload |
| `transmuteWith` | `[T2 <: Data](hardType: HardType[T2]): Stream[T2]` | 同位宽类型转换 |
| `swapPayload` | `[T2 <: Data](hardType: HardType[T2]): Stream[T2]` | 仅换类型不赋值 |
| `translateFrom` | `[T2 <: Data](that: Stream[T2])(f: (T, T2) => Unit): Stream[T]` | 从另一 Stream 转换 |
| `translateInto` | `[T2 <: Data](into: Stream[T2])(f: (T2, T) => Unit): Stream[T2]` | 转换到另一 Stream |
| `~` | `[T2 <: Data](that: T2): Stream[T2]` | = translateWith |
| `~~` | `[T2 <: Data](f: T => T2): Stream[T2]` | = map |
| `&` | `(cond: Bool): Stream[T]` | = continueWhen |

#### 流控操作

| 方法 | 签名 | 说明 |
|------|------|------|
| `continueWhen` | `(cond: Bool): Stream[T]` | cond=False 时暂停（反压） |
| `haltWhen` | `(cond: Bool): Stream[T]` | cond=True 时暂停 |
| `throwWhen` / `discardWhen` | `(cond: Bool): Stream[T]` | cond=True 时丢弃 |
| `takeWhen` | `(cond: Bool): Stream[T]` | cond=False 时丢弃 |
| `clearValidWhen` | `(cond: Bool): Stream[T]` | cond=True 时清除 valid |
| `repeat` | `(times: Int): (Stream[T], UInt)` | 每个元素重复 N 次 |
| `slowdown` | `(factor: Int): Stream[Vec[T]]` | 降速 factor 倍，位宽扩展 |
| `forkSerial` | `(cond: Bool): Stream[T]` | 条件分叉（串行） |

#### 队列/FIFO

| 方法 | 签名 | 说明 |
|------|------|------|
| `queue` | `(size: Int, latency: Int=2, forFMax: Boolean=false): Stream[T]` | 插入 FIFO |
| `queueOfReg` | `(size: Int, latency: Int=1, forFMax: Boolean=false, initPayload: Option[T]=None): Stream[T]` | 寄存器 FIFO |
| `queue` | `(size: Int, pushClock: ClockDomain, popClock: ClockDomain): Stream[T]` | 跨时钟域 FIFO |
| `queueLowLatency` | `(size: Int, latency: Int=0): Stream[T]` | 低延迟 FIFO |
| `queueWithOccupancy` | `(size: Int, ...): (Stream[T], UInt)` | FIFO + 占用率 |
| `queueWithAvailability` | `(size: Int, ...): (Stream[T], UInt)` | FIFO + 可用空间 |

#### 跨时钟域

| 方法 | 签名 | 说明 |
|------|------|------|
| `ccToggle` | `(pushClock: ClockDomain, popClock: ClockDomain): Stream[T]` | 安全 CDC |
| `ccToggleWithoutBuffer` | `(pushClock, popClock): Stream[T]` | CDC 无输出缓冲 |
| `ccToggleInputWait` | `(pushClock, popClock): Stream[T]` | CDC 带输入等待 |

#### 协议转换

| 方法 | 签名 | 说明 |
|------|------|------|
| `toFlow` | `(): Flow[T]` | 转为 Flow（ready 始终拉高） |
| `toFlowFire` | `(): Flow[T]` | 转为 Flow（valid = fire） |
| `asFlow` | `(): Flow[T]` | 转为 Flow（不驱动 ready） |
| `toEvent` | `(): Event` | 忽略 payload，仅保留握手 |
| `toReg` | `(): T` / `(init: T): T` | 转为寄存器 |
| `addFragmentLast` | `(last: Bool): Stream[Fragment[T]]` | 添加分片 last |
| `addFragmentLast` | `(counter: Counter): Stream[Fragment[T]]` | 计数器自动分片 |
| `fragmentTransaction` | `(bitsWidth: Int): Stream[Fragment[Bits]]` | 拆分为固定位宽 Fragment |

#### 形式化验证

| 方法 | 参数 | 说明 |
|------|------|------|
| `formalAssertsMaster` | `(payloadInvariance: Boolean=true)` | 断言 master 语义 |
| `formalAssumesSlave` | `(payloadInvariance: Boolean=true)` | 假设 slave 行为 |
| `formalCovers` | `(back2BackCycles: Int=1)` | 覆盖性检查 |
| `formalAssertsOrder` | `(dataAhead: T, dataBehind: T)` | 断言传输顺序 |
| `formalAssertsTimeout` | `(maxStallCycles: Int=0)` | 断言最大 stall 周期 |

---

### 7. Flow[T] — 无反压协议

**源码**：`lib/src/main/scala/spinal/lib/Flow.scala`（332行）

```scala
class Flow[T <: Data](val payloadType: HardType[T]) extends Bundle with IMasterSlave with DataCarrier[T]
```

**构造**：`Flow(payloadType)`, `Flow(=> T)`

**核心信号**：`valid: Bool`, `payload: T`

| 方法 | 签名 | 说明 |
|------|------|------|
| `fire` | `Bool` | = valid（无反压，valid 即传输） |
| `push` | `(that: T): Unit` | 设置 valid=True + payload |
| `default` | `(that: T): Unit` | 设置 valid=False + payload |
| `setIdle` | `(): this.type` | valid=False, payload=dontCare |
| `<<` / `>>` | 直连 | Flow 连接 |
| `<-<` / `>->` | m2sPipe 连接 | 打拍连接 |
| `combStage` | `(): Flow[T]` | 组合逻辑隔离 |
| `swapPayload` | `[T2](hardType: HardType[T2]): Flow[T2]` | 换 payload 类型 |
| `toStream` | `(): Stream[T]` | 转为 Stream |
| `toStream` | `(overflow: Bool): Stream[T]` | 转为 Stream + 溢出指示 |
| `toStream` | `(overflow: Bool, fifoSize: Int, overflowAt: Int): Stream[T]` | 转为 Stream + FIFO + 溢出 |
| `toReg` | `(): T` / `(init: T): T` | 转为寄存器 |
| `m2sPipe` | `(holdPayload=false, flush=null, crossClockData=false): Flow[T]` | 打拍 |
| `stage` | `(): Flow[T]` | = m2sPipe |
| `delay` | `(cycleCount: Int): Flow[T]` | 延迟 N 周期 |
| `ccToggle` | `(pushClock, popClock, withOutputBufferedReset=true, withOutputM2sPipe=true): Flow[T]` | 跨时钟域 |
| `takeWhen` / `discardWhen` / `throwWhen` | `(cond: Bool): Flow[T]` | 条件过滤 |
| `translateWith` | `[T2](that: T2): Flow[T2]` | 替换 payload |
| `translateFrom` | `[T2](that: Flow[T2])(f: (T,T2)=>Unit): Flow[T]` | 从另一 Flow 转换 |
| `map` | `[T2](f: T=>T2): Flow[T2]` | 函数映射 |
| `~` / `~~` | 操作符 | = translateWith / map |
| `queueWithOccupancy` | `(size: Int): (Stream[T], UInt)` | 通过 FIFO 转 Stream + 占用率 |
| `queueWithAvailability` | `(size: Int): (Stream[T], UInt)` | 通过 FIFO 转 Stream + 可用空间 |

**Flow 辅助对象：**

| Object | 签名 | 说明 |
|--------|------|------|
| `FlowCCUnsafeByToggle` | `(input: Flow[T], inputClock: ClockDomain, outputClock: ClockDomain, ...): Flow[T]` | 不安全 Flow CDC（发送速率 < 接收速率） |
| `FlowArbiter` | `(inputs: Seq[Flow[T]], output: Flow[T]): Unit` | Flow 仲裁（独热 valid） |
| `ValidFlow` | `(payload: T): Flow[T]` | 始终有效的 Flow |
| `RegFlow` | `(dataType: T): Flow[T]` | 寄存器 Flow |

---

### 8. Fragment[T] — 分片协议

**源码**：`lib/src/main/scala/spinal/lib/Fragment.scala`

```scala
class Fragment[T <: Data](val fragmentType: HardType[T]) extends Bundle
// 核心信号：fragment: T（负载）, last: Bool
```

**分片状态查询（DataCarrierFragmentPimped，对 Stream/Flow[Fragment[T]] 通用）：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `first` | `(): Bool` | 首片标志（寄存器，事务首个 fire 后为 True） |
| `tail` | `(): Bool` | 非首片（`!first`） |
| `isFirst` | `(): Bool` | `valid && first` |
| `isTail` | `(): Bool` | `valid && tail` |
| `isLast` | `(): Bool` | `valid && last`（末片） |
| `firstFire` | `(): Bool` | `fire && first` |
| `lastFire` | `(): Bool` | `fire && last` |

**Stream[Fragment[T]] 扩展方法（StreamFragmentPimped）：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `toStreamOfFragment` | `: Stream[T]` | 提取纯 fragment 的 Stream（丢弃 last） |
| `replaceFragmentLast` | `(last: Bool): Stream[Fragment[T]]` | 用新的 last 信号重建分片流 |
| `reduce` | `[U <: Data](identity: U, accumulator: (U, U, T) => Unit): Stream[U]` | 逐片累加归约（如求和/校验） |
| `insertHeader` | `(header: T): Stream[Fragment[T]]` / `(header: Vec[T])` | 每个包首部插入 header |
| `toFragmentBits` | `(bitsWidth: Int): Stream[Fragment[Bits]]` | 重切分为指定位宽的 Bits 分片 |

**构造**：`Stream Fragment (dataType)` → `Stream[Fragment[T]]`；`Flow Fragment (dataType)` → `Flow[Fragment[T]]`

---

## 第三部分：Stream 组件库

### 9. StreamFork — 数据分叉

**源码**：`Stream.scala:1291-1375`

```scala
class StreamFork[T <: Data](dataType: HardType[T], portCount: Int, synchronous: Boolean = false) extends Component
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `dataType` | `HardType[T]` | payload 类型 |
| `portCount` | `Int` | 输出端口数 |
| `synchronous` | `Boolean` | true=所有输出必须同时 ready；false=可逐个 ready（额外 1FF/输出） |

**IO：** `io.input: Stream[T]`（slave）, `io.outputs: Vec[Stream[T]]`（master, portCount 个）

| Object | 签名 | 说明 |
|--------|------|------|
| `StreamFork(input, portCount, synchronous=false)` | → `Vec[Stream[T]]` | N 路分叉 |
| `StreamFork2(input, synchronous=false)` | → `(Stream[T], Stream[T])` | 2 路分叉 |
| `StreamFork3(input, synchronous=false)` | → `(Stream[T], Stream[T], Stream[T])` | 3 路分叉 |
| `StreamFork2.takes(input, take0: Bool, take1: Bool, synchronous=false)` | → `(Stream[T], Stream[T])` | 条件分叉 |

---

### 10. StreamJoin — 数据汇合

**源码**：`Stream.scala:1390-1437`

| Object | 签名 | 说明 |
|--------|------|------|
| `StreamJoin(s1, s2)` | → `Stream[TupleBundle2[T1,T2]]` | 2 路汇合为元组 |
| `StreamJoin.vec(sources: Seq[Stream[T]])` | → `Stream[Vec[T]]` | N 路汇合为 Vec |
| `StreamJoin(sources: Seq[Stream[_]])` | → `Event` | N 路汇合忽略 payload |
| `StreamJoin.fixedPayload(sources, payload: T)` | → `Stream[T]` | N 路汇合 + 固定 payload |

---

### 11. StreamMux / StreamDemux — 多路选择/分配

**源码**：`Stream.scala:1155-1289`

```scala
class StreamMux[T <: Data](dataType: T, portCount: Int) extends Component
// IO: select: UInt(in), inputs: Vec[Stream[T]](slave, portCount), output: Stream[T](master)

class StreamDemux[T <: Data](dataType: T, portCount: Int) extends Component
// IO: select: UInt(in), input: Stream[T](slave), outputs: Vec[Stream[T]](master, portCount)
```

| Object | 签名 | 说明 |
|--------|------|------|
| `StreamMux(select: UInt, inputs: Seq[Stream[T]])` | → `Stream[T]` | 多路选择 |
| `StreamMux.joinSel(select: Stream[UInt], inputs)` | → `Stream[T]` | 完全同步选择 |
| `StreamMux.regSel(select: Stream[UInt], inputs)` | → `Stream[T]` | 寄存选择 |
| `StreamDemux(input, select: UInt, portCount)` | → `Vec[Stream[T]]` | 多路分配 |
| `StreamDemux.two(input, select)` | → `(Stream[T], Stream[T])` | 2 路分配 |
| `StreamDemux.joinSel(input, select: Stream[UInt], portCount)` | → `Vec[Stream[T]]` | 完全同步分配 |
| `StreamDemuxOh(input, oh: Seq[Bool])` | → `Vec[Stream[T]]` | 独热选择分配 |

---

### 12. StreamFifo — FIFO 队列

**源码**：`Stream.scala:1446-1800`

```scala
class StreamFifo[T <: Data](dataType: HardType[T], depth: Int,
  withAsyncRead: Boolean = false, withBypass: Boolean = false,
  allowExtraMsb: Boolean = true, forFMax: Boolean = false,
  useVec: Boolean = false, initPayload: => Option[T] = None) extends Component
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `dataType` | `HardType[T]` | — | payload 类型 |
| `depth` | `Int` | — | FIFO 深度（≥0） |
| `withAsyncRead` | `Boolean` | `false` | 异步读（分布式 RAM）；false 则加 1 周期延迟 |
| `withBypass` | `Boolean` | `false` | 空 FIFO 时 bypass push→pop（需 withAsyncRead=true） |
| `forFMax` | `Boolean` | `false` | 优化时序以获得最高频率 |
| `useVec` | `Boolean` | `false` | 用 Vec[Reg] 代替 Mem（需 withAsyncRead=true） |
| `initPayload` | `=> Option[T]` | `None` | Vec 模式下寄存器初始值 |

**IO：** `push: Stream[T]`(slave), `pop: Stream[T]`(master), `flush: Bool`(in), `occupancy: UInt`(out), `availability: UInt`(out)

| 便捷构造 | 说明 |
|----------|------|
| `StreamFifo(dataType, depth, latency=2)` | latency: 0(bypass+async) / 1(async) / 2(sync) |

**其他 FIFO 变体：**

| Class | 参数 | 说明 |
|-------|------|------|
| `StreamFifoLowLatency(dataType, depth, latency=0, useVec=false)` | latency: 0/1 | 低延迟 FIFO |
| `StreamFifoCC(dataType, depth, pushClock, popClock)` | — | 跨时钟域 FIFO（格雷指针） |
| `StreamFifoMultiChannelSharedSpace(payloadType, channelCount, depth, withAllocationFifo=false)` | — | 多通道共享空间 FIFO |

---

### 13. StreamCCByToggle — 跨时钟域 Stream

**源码**：`Stream.scala:2048-2100`

```scala
class StreamCCByToggle[T <: Data](dataType: HardType[T], inputClock: ClockDomain, outputClock: ClockDomain,
  withOutputBufferedReset: Boolean = ..., withInputWait: Boolean = false, withOutputBuffer: Boolean = true,
  initPayload: T = null) extends Component
```

**IO：** `input: Stream[T]`(slave, inClock), `output: Stream[T]`(master, outClock)

| Object | 签名 | 说明 |
|--------|------|------|
| `StreamCCByToggle(input, inputClock, outputClock)` | → `Stream[T]` | 安全 Stream CDC |

---

### 14. StreamDelay — 定时延迟

**源码**：`Stream.scala:2911-2938`

```scala
class StreamDelay[T <: Data](payloadType: HardType[T], delay: Int,
  pendingMax: Option[Int] = Option.empty[Int], timestampWidth: Int = 16) extends Component
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `payloadType` | `HardType[T]` | payload 类型 |
| `delay` | `Int` | 延迟周期数 |
| `pendingMax` | `Option[Int]` | 最大等待数（默认 `2^timestampWidth`） |
| `timestampWidth` | `Int` | 时间戳位宽（默认 16） |

**IO：** `push: Stream[T]`(slave), `pop: Stream[T]`(master)

**实现：** delay=0 → bypass；delay=1 → `>->` 打拍；delay≥2 → FIFO + 时间戳

---

### 15. StreamArbiter — 仲裁器

**源码**：`Stream.scala:763-1065`

```scala
class StreamArbiter[T <: Data](dataType: HardType[T], portCount: Int)(
  arbitrationPolicy: StreamArbiter.ArbitrationPolicy, lockPolicy: StreamArbiter.LockPolicy) extends Component
```

**仲裁策略（ArbitrationPolicy）：**

| 策略 | 说明 |
|------|------|
| `LowerFirst` | 低索引优先 |
| `HigherFirst` | 高索引优先 |
| `RoundRobin` | 轮询仲裁 |
| `Sequence` | 顺序（一个事务完成后才切换） |
| `NoLock` | 无锁定（逐拍仲裁） |

**锁定策略（LockPolicy）：**

| 策略 | 说明 |
|------|------|
| `Lock` | 一个事务期间锁定输入 |
| `Transaction` | 一个事务完成后释放 |
| `None` | 无锁定 |

---

### 16. 其他 Stream 组件

| 组件 | 签名 | 说明 |
|------|------|------|
| `StreamDispatcherSequencial(gen, n)` | `Component` | 顺序分发（1 输入轮流到 N 输出） |
| `StreamCombinerSequential(gen, n)` | `Component` | 顺序合并（N 输入合并到 1 输出） |
| `StreamFlowArbiter(dataType)` | `Area` | Stream + Flow 仲裁（Flow 优先） |
| `StreamToStreamFragmentBits(dataType, bitsWidth)` | `Component` | Stream → 固定位宽 Fragment |
| `Event` / `EventEmitter(on: Event)` | `object` / `case class` | 无 payload 事件 |
| `NoData` | `class extends Bundle` | 空 payload 类型 |
| `StreamPipe` | `trait` | 流水线配置（NONE/M2S/S2M/FULL/HALF） |

---

## 第四部分：工具函数与原语

### 17. Delay — 信号延迟

**源码**：`Utils.scala:1092`

```scala
object Delay {
  def apply[T <: Data](that: T, cycleCount: Int,
    when: Bool = null, init: T = null.asInstanceOf[T],
    onEachReg: T => Unit = null): T
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `that` | `T <: Data` | 要延迟的信号 |
| `cycleCount` | `Int` | 延迟周期数（≥0） |
| `when` | `Bool` | 条件延迟（仅 when=True 时移位） |
| `init` | `T` | 寄存器初始值 |
| `onEachReg` | `T => Unit` | 对每级寄存器施加操作（如添加 Tag） |

---

### 18. History — 信号历史

**源码**：`Utils.scala:1117`

```scala
object History {
  def apply[T <: Data](that: T, length: Int, when: Bool = null, init: T = null): Vec[T]
  def apply[T <: Data](that: T, range: Range, when: Bool, init: T): Vec[T]
  def apply[T <: Data](that: T, range: Range, init: T): Vec[T]
  def apply[T <: Data](that: T, range: Range): Vec[T]
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `that` | `T <: Data` | 要记录历史的信号 |
| `length` | `Int` | 历史深度 |
| `range` | `Range` | 子范围提取 |
| `when` | `Bool` | 条件记录 |
| `init` | `T` | 初始值 |

**返回**：`Vec[T]`，index 0 = 当前值，index 1 = 上一拍，...

---

### 19. Counter — 计数器

**源码**：`Counter.scala`（762行）

```scala
// 类构造（计数范围 [start, end] 含端点）
class Counter(start: BigInt, end: BigInt, direction: CounterDirection = Up,
  upper: BoundaryPolicy = Wrap, lower: BoundaryPolicy = Wrap)

// 常用工厂 object Counter
Counter(stateCount: BigInt)            // [0, stateCount-1]
Counter(start: BigInt, end: BigInt)    // [start, end]
Counter(bitCount: BitCount)            // [0, 2^n-1]
Counter(stateCount: BigInt, inc: Bool) // 带递增使能
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `start` / `end` | `BigInt` | 计数范围（含端点） |
| `stateCount` | `BigInt` | 工厂参数：状态总数 → `[0, stateCount-1]` |
| `inc` | `Bool` | 递增使能（工厂可选） |
| `direction` | `CounterDirection` | `Up` / `Down` / `Both` |
| `upper` | `BoundaryPolicy` | 上界策略：`Wrap`/`Saturate`/`Freeze` |
| `lower` | `BoundaryPolicy` | 下界策略 |

**CounterLike 通用接口：**

| 方法 | 返回 | 说明 |
|------|------|------|
| `value` | `T` | 当前寄存器值 |
| `valueNext` | `T` | 组合下一值 |
| `willClear` / `willLoad` / `willAdvance` / `willComplete` | `Bool` | 状态脉冲 |
| `willIncrement` / `willDecrement` | `Bool` | 递增/递减请求 |
| `willOverflowIfInc` / `willUnderflowIfDec` | `Bool` | 溢出/下溢预测 |
| `willOverflow` / `willUnderflow` | `Bool` | 实际溢出/下溢 |
| `clear()` | `Unit` | 复位到初始值 |
| `load(raw: T)` | `Unit` | 加载外部值 |
| `increment()` / `decrement()` | `Unit` | 递增/递减 |
| `freeRun()` | `Unit` | 自由运行 |
| `toFlow()` | `Flow[T]` | 转为 Flow |
| `stateCount` | `BigInt` | 总状态数 |

**计数器变体：**

| Class | 额外参数 | 说明 |
|-------|----------|------|
| `CounterFreeRun(stateCount)` | — | 始终递增 |
| `CounterUpDown(stateCount, incWhen, decWhen)` | incWhen/decWhen Bool | 加/减计数器 |
| `DownCounter(stateCount)` | — | 递减计数器 |
| `OneHotCounter(stateCount)` | — | 独热编码 |
| `JohnsonCounter(width)` | — | Johnson（扭环）编码 |
| `GrayCounter(width)` | — | Gray 编码计数器 |

---

### 20. 跨时钟域原语

**源码**：`CrossClock.scala`

| 原语 | 签名 | 说明 |
|------|------|------|
| `BufferCC` | `(input: T, init: => T = null, bufferDepth: Option[Int] = None, randBoot: Boolean = false): T` | 寄存器链（最基础 CDC） |
| `PulseCCByToggle` | `(input: Bool, clockIn: ClockDomain, clockOut: ClockDomain): Bool` | 脉冲 CDC |
| `StreamCCByToggle` | `(input: Stream[T], inputClock: ClockDomain, outputClock: ClockDomain): Stream[T]` | 安全 Stream CDC |
| `FlowCCUnsafeByToggle` | `(input: Flow[T], inputClock: ClockDomain, outputClock: ClockDomain, ...): Flow[T]` | 不安全 Flow CDC |
| `DataCc` | `(from: T, fromCd: ClockDomain, toCd: ClockDomain)(initValue: => T): T`；`DataCc(to, from)(initValue): Unit` | 单值数据 CDC（基于 StreamCCByToggle） |
| `toGray` | `(uint: UInt): Bits` | 二进制→Gray 编码（CDC 指针） |
| `fromGray` | `(gray: Bits): UInt` | Gray→二进制解码 |

---

### 21. 编码与位操作工具

**源码**：`Utils.scala`

| Object | 签名 | 说明 |
|--------|------|------|
| `UIntToOh` | `(value: UInt, width: Int): Bits` | 二进制 → 独热 |
| `OHToUInt` | `(oh: Bits): UInt` | 独热 → 二进制 |
| `MuxOH` | `(oh: Bits, inputs: Seq[T]): T` | 独热多路选择 |
| `OHMux.or` | `(oh: Seq[Bool], inputs: Seq[T], fast: Boolean): T` | 独热 MUX |
| `OHMasking.first` | `(bits: Bits): Bits` | 保留最低位 1 |
| `OHMasking.next` | `(bits: Bits): Bits` | 保留次低位 1 |
| `CountOne` | `(bits: Bits): UInt` | 计算 1 的个数 |
| `SetFromFirstOne` | `(bits: Bits): Bits` | 从第一个 1 后全置 1 |
| `Napot` | `(bits: Bits): Bits` | NAPOT 检测 |
| `Min` / `Max` | `(a: T, b: T): T` | 最小/最大 |
| `Clamp` | `(value: T, min: T, max: T): T` | 钳位 |
| `Log2` | `(value: UInt): UInt` | 硬件 log2 |
| `Delay` | `(that: T, cycleCount: Int, ...): T` | 信号延迟 |
| `History` | `(that: T, length: Int, ...): Vec[T]` | 信号历史 |
| `Repeat` | `(value: T, times: Int): T` | 重复（= `value #* times`） |

---

## 第五部分：总线协议

### 22. BusSlaveFactory — 寄存器映射框架（核心 trait）

**源码**：`lib/src/main/scala/spinal/lib/bus/misc/BusSlaveFactory.scala`（1117行）

```scala
trait BusSlaveFactory extends Area
trait BusSlaveFactoryDelayed extends BusSlaveFactory  // 延迟构建基类
```

所有总线从机工厂（Apb3SlaveFactory、Axi4SlaveFactory 等）均实现此 trait，提供统一的寄存器映射 API。

#### 基础读写

| 方法 | 签名 | 说明 |
|------|------|------|
| `read` | `(that: T, address: BigInt, bitOffset: Int=0, doc: String=null): T` | 读 address 时返回 that 的值（放置于 bitOffset） |
| `write` | `(that: T, address: BigInt, bitOffset: Int=0, doc: String=null): T` | 写 address 时用总线数据赋值 that |
| `readAndWrite` | `(that: Data, address: BigInt, bitOffset: Int=0, doc: String=null): Unit` | 同地址读写 |
| `nonStopWrite` | `(that: T, bitOffset: Int=0, doc: String=null): T` | 始终用总线写数据驱动 that |
| `onWrite` | `(address: BigInt, doc: String=null)(doThat: => Unit): Unit` | 写 address 时执行回调 |
| `onRead` | `(address: BigInt, doc: String=null)(doThat: => Unit): Unit` | 读 address 时执行回调 |
| `isWriting` | `(address: BigInt): Bool` | 返回写 address 时为 True 的脉冲 |
| `isReading` | `(address: BigInt): Bool` | 返回读 address 时为 True 的脉冲 |
| `readHalt` | `(): Unit` | 暂停读事务（拉低 PREADY） |
| `writeHalt` | `(): Unit` | 暂停写事务 |
| `readAddress` | `(): UInt` | 当前读地址 |
| `writeAddress` | `(): UInt` | 当前写地址 |
| `busDataWidth` | `: Int` | 总线数据位宽 |
| `wordAddressInc` | `: Int` | 多字寄存器地址增量（= busDataWidth/8） |

#### 寄存器创建

| 方法 | 签名 | 说明 |
|------|------|------|
| `createWriteOnly` | `(dataType: T, address: BigInt, bitOffset: Int=0): T` | 创建只写寄存器（Reg + write） |
| `createReadOnly` | `(dataType: T, address: BigInt, bitOffset: Int=0): T` | 创建只读寄存器（Reg + read） |
| `createReadAndWrite` | `(dataType: T, address: BigInt, bitOffset: Int=0): T` | 创建读写寄存器 |
| `createAndDriveFlow` | `(dataType: T, address: BigInt, bitOffset: Int=0): Flow[T]` | 创建 Flow，写 address 时触发 |
| `createAndDriveStream` | `(dataType: T, address: BigInt, bitOffset: Int=0): Stream[T]` | 创建 Stream，写 address 时触发（阻塞直到 ready） |

#### 驱动与多字操作

| 方法 | 签名 | 说明 |
|------|------|------|
| `drive` | `(that: T, address: BigInt, bitOffset: Int=0): T` | 创建 Reg 写入并驱动 that |
| `driveAndRead` | `(that: T, address: BigInt, bitOffset: Int=0): T` | drive + 可读 |
| `driveMultiWord` | `(that: T, address: BigInt): T` | 驱动超宽信号（跨多个地址） |
| `driveAndReadMultiWord` | `(that: T, address: BigInt): T` | driveMultiWord + 可读 |
| `readMultiWord` | `(that: Data, address: BigInt): Unit` | 读超宽寄存器 |
| `writeMultiWord` | `(that: Data, address: BigInt): Unit` | 写超宽寄存器 |

#### 位操作寄存器

| 方法 | 签名 | 说明 |
|------|------|------|
| `clearOnSet` | `(that: T, address: BigInt, bitOffset: Int=0): T` | 写 1 清零对应位 |
| `setOnSet` | `(that: T, address: BigInt, bitOffset: Int=0): T` | 写 1 置位对应位 |
| `clearOnClear` | `(that: T, address: BigInt, bitOffset: Int=0): T` | 写 0 清零对应位 |
| `setOnClear` | `(that: T, address: BigInt, bitOffset: Int=0): T` | 写 0 置位对应位 |
| `readAndClearOnSet` | `(that: T, address: BigInt, bitOffset: Int=0): T` | clearOnSet + 可读 |
| `readAndSetOnSet` | `(that: T, address: BigInt, bitOffset: Int=0): T` | setOnSet + 可读 |
| `createReadAndClearOnSet` | `(dataType: T, address: BigInt, bitOffset: Int=0): T` | 创建 Reg + readAndClearOnSet |
| `createReadAndSetOnSet` | `(dataType: T, address: BigInt, bitOffset: Int=0): T` | 创建 Reg + readAndSetOnSet |

#### Stream/Flow/Mem 映射

| 方法 | 签名 | 说明 |
|------|------|------|
| `driveFlow` | `(that: Flow[T], address: BigInt, bitOffset: Int=0): Unit` | 写 address 时触发 Flow 事务 |
| `driveStream` | `(that: Stream[T], address: BigInt, bitOffset: Int=0): Unit` | 写 address 时触发 Stream（阻塞） |
| `readStreamNonBlocking` | `(that: Stream[T], address: BigInt): Unit` | 读 address 时消费 Stream（非阻塞） |
| `readSyncMemWordAligned` | `(mem: Mem[T], addressOffset: BigInt, bitOffset: Int=0): Mem[T]` | 同步读 Mem 映射 |
| `readSyncMemMultiWord` | `(mem: Mem[T], addressOffset: BigInt): Mem[T]` | 超宽 Mem 读映射 |
| `writeMemWordAligned` | `(mem: Mem[T], addressOffset: BigInt, bitOffset: Int=0): Mem[T]` | Mem 写映射 |
| `writeMemMultiWord` | `(mem: Mem[T], addressOffset: BigInt): Mem[T]` | 超宽 Mem 写映射 |
| `doBitsAccumulationAndClearOnRead` | `(that: Bits, address: BigInt, bitOffset: Int=0): Unit` | 位累积 + 读时清零 |

#### 配置与工具

| 方法 | 签名 | 说明 |
|------|------|------|
| `getConfig` | `: BusSlaveFactoryConfig` | 获取配置（含 wordEndianness） |
| `setConfig` | `(value: BusSlaveFactoryConfig): this.type` | 设置配置 |
| `withOffset` | `(offset: BigInt): BusSlaveFactory` | 地址偏移包装器 |
| `printDataModel` | `(): Unit` | 打印寄存器映射表 |

---

### 23. APB3 / APB4

**源码**：`lib/src/main/scala/spinal/lib/bus/amba3/apb/APB3.scala`（115行）

#### Apb3Config

```scala
case class Apb3Config(
  addressWidth  : Int,
  dataWidth     : Int,
  selWidth      : Int = 1,
  useSlaveError : Boolean = true,
  useStrb       : Boolean = false,
  useProt       : Boolean = false
)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `addressWidth` | `Int` | — | 地址位宽 |
| `dataWidth` | `Int` | — | 数据位宽（8/16/32/64） |
| `selWidth` | `Int` | `1` | PSEL 位宽（多从机时 >1） |
| `useSlaveError` | `Boolean` | `true` | 是否生成 PSLVERROR |
| `useStrb` | `Boolean` | `false` | 是否生成 PSTRB（写选通） |
| `useProt` | `Boolean` | `false` | 是否生成 PPROT（保护类型） |

#### Apb3 Bundle IO 信号

```scala
case class Apb3(config: Apb3Config) extends Bundle with IMasterSlave
```

| 信号 | 类型 | Master→Slave | 说明 |
|------|------|:---:|------|
| `PADDR` | `UInt(addressWidth bits)` | out | 地址 |
| `PSEL` | `Bits(selWidth bits)` | out | 从机选择 |
| `PENABLE` | `Bool` | out | 传输使能 |
| `PWRITE` | `Bool` | out | 写方向 |
| `PWDATA` | `Bits(dataWidth bits)` | out | 写数据 |
| `PSTRB` | `Bits(dataBytes bits)` | out | 写选通（可选） |
| `PPROT` | `Bits(3 bits)` | out | 保护类型（可选） |
| `PREADY` | `Bool` | in | 从机就绪 |
| `PRDATA` | `Bits(dataWidth bits)` | in | 读数据 |
| `PSLVERROR` | `Bool` | in | 从机错误（可选） |

**Apb3 方法：** `<<(sink)`, `>>(sink)`, `m2sPipe()`, `crossClockDomainToggle(inClk, outClk)`

#### Apb4Config / Apb4

```scala
case class Apb4Config(
  addressWidth  : Int,
  dataWidth     : Int,
  selWidth      : Int = 1,
  useStrb       : Boolean = true,   // APB4 默认开启
  useSlaveError : Boolean = true
)
```

Apb4 与 Apb3 区别：PSTRB 和 PPROT 始终存在。

#### Apb3SlaveFactory

```scala
object Apb3SlaveFactory {
  def apply(bus: Apb3, selId: Int = 0, dontCareReadData: Boolean = false): Apb3SlaveFactory
}
```

| 参数 | 说明 |
|------|------|
| `bus` | APB3 总线实例 |
| `selId` | PSEL 索引（多从机时选择） |
| `dontCareReadData` | true 时读数据为 don't care（优化面积） |

继承 BusSlaveFactory 全部方法（见第 22 节）。

#### 其他 APB 组件

| 组件 | 说明 |
|------|------|
| `Apb3Decoder(master, slaves: Seq[(Apb3SlaveFactory, SizeMapping)])` | 地址译码器 |
| `Apb3Gpio(gpioWidth: Int)` | GPIO 控制器 |
| `Apb3ToBmb` | APB3 → Bmb 桥 |
| `Apb3Router` | 地址路由 |
| `Apb3CC(config, inputClock, outputClock)` | 跨时钟域 APB3 |

---

### 24. AXI4

**源码**：`lib/src/main/scala/spinal/lib/bus/amba4/axi/Axi4.scala`

#### Axi4Config

```scala
case class Axi4Config(
  addressWidth : Int,
  dataWidth    : Int,
  idWidth      : Int = -1,
  useId        : Boolean = true,
  withAxi3     : Boolean = false,
  useRegion    : Boolean = true,
  useBurst     : Boolean = true,
  useLock      : Boolean = true,
  useCache     : Boolean = true,
  useSize      : Boolean = true,
  useQos       : Boolean = true,
  useLen       : Boolean = true,
  useLast      : Boolean = true,
  useResp      : Boolean = true,
  useProt      : Boolean = true,
  useStrb      : Boolean = true,
  useAllStrb   : Boolean = false,
  arUserWidth  : Int = -1,
  awUserWidth  : Int = -1,
  rUserWidth   : Int = -1,
  wUserWidth   : Int = -1,
  bUserWidth   : Int = -1,
  readIssuingCapability  : Int = -1,
  writeIssuingCapability : Int = -1
)
```

| 参数分类 | 关键参数 | 说明 |
|----------|----------|------|
| 基础 | `addressWidth`, `dataWidth`, `idWidth` | 地址/数据/ID 位宽 |
| 通道裁剪 | `useXxx: Boolean` | 控制各信号是否生成（false 则不生成该信号，节省面积） |
| User 信号 | `arUserWidth`, `awUserWidth` 等 | User 自定义信号位宽（-1=不生成） |
| AXI3 兼容 | `withAxi3` | 使用 AXI3 协议变体 |

#### AXI4 变体

| Class | 说明 |
|-------|------|
| `Axi4(config)` | 完整 AXI4（AR+AW+R+W+B 五通道） |
| `Axi4ReadOnly(config)` | 仅 AR+R 通道 |
| `Axi4WriteOnly(config)` | 仅 AW+W+B 通道 |
| `Axi4Shared(config)` | 共享地址通道（AR/AW 合并为 ARW） |

#### AXI4 组件

| 组件 | 说明 |
|------|------|
| `Axi4SlaveFactory(bus: Axi4)` | 寄存器映射工厂（继承 BusSlaveFactory 全部方法） |
| `Axi4CrossbarFactory()` | 交叉开关工厂（`addSlave`/`addConnection`/`addPipelining`/`build`，详见 design-patterns B14） |
| `Axi4ReadOnlyArbiter(outputConfig, inputsCount)` | 读方向仲裁器（AXI4 无统一 Arbiter，按方向分别使用） |
| `Axi4WriteOnlyArbiter(outputConfig, inputsCount)` | 写方向仲裁器 |
| `Axi4SharedArbiter(...)` | 共享总线仲裁器 |
| `Axi4ReadOnlyDecoder` / `Axi4WriteOnlyDecoder` | 地址译码（按方向分别使用） |
| `Axi4ReadOnlyUpsizer(inputConfig, outputConfig, pendingQueueSize)` / `Axi4WriteOnlyUpsizer` | 数据位宽增大 |
| `Axi4ReadOnlyDownsizer(inputConfig, outputConfig)` / `Axi4WriteOnlyDownsizer` | 数据位宽减小 |
| `Axi4CC(axiConfig, pushCd, popCd)` | 跨时钟域（另有 ReadOnly/WriteOnly 变体） |
| `Axi4ReadOnlyAligner` / `Axi4WriteOnlyAligner` | 对齐器 |
| `Axi4ReadOnlyCompactor` / `Axi4WriteOnlyCompactor` | 写数据压缩 |
| `Axi4ReadOnlyUnburster` / `Axi4WriteOnlyUnburster` | 突发拆分 |
| `Axi4SharedToApb3Bridge(addressWidth, dataWidth, idWidth)` | AXI4 → APB3 桥（接三个位宽参数，非 config） |

### 25. AXI4-Lite / AXI4-Stream

| Class | 构造参数 | 说明 |
|-------|----------|------|
| `AxiLite4(config)` | `AxiLite4Config(addressWidth, dataWidth)` | AXI4-Lite（无突发） |
| `AxiLite4SlaveFactory(bus)` | — | 寄存器映射（继承 BusSlaveFactory） |
| `Axi4Stream(config)` | `Axi4StreamConfig(dataWidth, idWidth, destWidth, userWidth, useStrb, useKeep, useLast, useId, ...)` | AXI4-Stream |
| `Axi4StreamWidthAdapter(input, output)` | — | 位宽适配 |

### 26. 其他总线

| 总线 | 主要 Class | 说明 |
|------|-----------|------|
| Avalon | `AvalonMM(config)`, `AvalonST(config)` | Intel FPGA 总线 |
| Wishbone | `Wishbone(config)` | 开源 SoC 总线 |
| Bmb | `Bmb(parameter: BmbParameter)` | SpinalHDL 内部高性能总线（Crossbar/Decoder/Arbiter） |
| TileLink | TileLink 系列 | RISC-V SoC 总线（U/W 两种模式） |

---

## 第六部分：通信外设

### 27. UART

**源码**：`lib/src/main/scala/spinal/lib/com/uart/`

#### Uart 信号

```scala
case class Uart(ctsGen: Boolean = false, rtsGen: Boolean = false) extends Bundle with IMasterSlave
```

| 信号 | 方向 | 说明 |
|------|------|------|
| `txd` | out | 发送数据 |
| `rxd` | in | 接收数据 |
| `cts` | in | 清除发送（可选，ctsGen=true） |
| `rts` | out | 请求发送（可选，rtsGen=true） |

#### UartCtrlGenerics

```scala
case class UartCtrlGenerics(
  dataWidthMax: Int = 8,
  clockDividerWidth: Int = 20,
  preSamplingSize: Int = 1,
  samplingSize: Int = 5,
  postSamplingSize: Int = 2,
  ctsGen: Boolean = false,
  rtsGen: Boolean = false
)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `dataWidthMax` | 8 | 最大数据位宽（5-8 位可选） |
| `clockDividerWidth` | 20 | 波特率分频器位宽。baudrate = Fclk / (rxSamplePerBit × divider) |
| `preSamplingSize` | 1 | 起始位采样点数 |
| `samplingSize` | 5 | 数据位采样点数（建议奇数，用于多数表决） |
| `postSamplingSize` | 2 | 停止位采样点数 |
| `ctsGen` / `rtsGen` | false | 是否生成硬件流控信号 |

**rxSamplePerBit** = preSamplingSize + samplingSize + postSamplingSize（默认 8）

#### UartCtrlConfig

```scala
case class UartCtrlConfig(g: UartCtrlGenerics) extends Bundle
// 信号：frame: UartCtrlFrameConfig(dataLength, stop, parity), clockDivider: UInt
// 方法：setClockDivider(baudrate, clkFrequency) — 自动计算分频值
```

#### UartCtrl 组件

```scala
class UartCtrl(g: UartCtrlGenerics = UartCtrlGenerics()) extends Component
// IO：config(in), write(Stream slave), read(Stream master), uart(Uart), readError(Bool)
```

| 集成版本 | 构造参数 | 说明 |
|----------|----------|------|
| `Apb3UartCtrl` | `UartCtrlMemoryMappedConfig` | APB3 总线 UART（自动寄存器映射） |
| `BmbUartCtrl` | `(UartCtrlMemoryMappedConfig, BmbParameter)` | Bmb 总线 UART |

### 28. SPI

**源码**：`lib/src/main/scala/spinal/lib/com/spi/`

#### SpiMasterCtrlGenerics

```scala
case class SpiMasterCtrlGenerics(
  ssWidth: Int,
  timerWidth: Int,
  dataWidth: Int = 8,
  sampleReset: Boolean = false
)
```

| 参数 | 说明 |
|------|------|
| `ssWidth` | 片选信号位宽（0=不生成 SS） |
| `timerWidth` | 定时器/分频器位宽（控制 SCLK 频率） |
| `dataWidth` | 数据位宽（默认 8） |
| `sampleReset` | 采样复位模式 |

#### SpiXdrParameter（双边沿 SPI）

```scala
case class SpiXdrParameter(
  dataWidth: Int,
  ioRate: Int,       // IO 倍频率（1=SDR, 2=DDR, 4=QDR）
  ssWidth: Int,
  inLatency: Int = 1,
  outLatency: Int = 1
)
```

| SPI 组件 | 说明 |
|----------|------|
| `SpiMaster(ssWidth)` | SPI 主机信号 Bundle |
| `SpiSlave(useSclk)` | SPI 从机信号 Bundle |
| `SpiMasterCtrl(generics)` | SPI 主机控制器 |
| `SpiSlaveCtrl(generics)` | SPI 从机控制器 |
| `SpiXdrMasterCtrl(p: SpiXdrParameter)` | XDR（双边沿/多倍速）SPI 主机 |
| `Apb3SpiMasterCtrl(generics)` | APB3 SPI 主机 |

### 29. I2C

**源码**：`lib/src/main/scala/spinal/lib/com/i2c/`

| Class | 说明 |
|-------|------|
| `I2c()` | I2C 信号 Bundle（sda/scl 为 InOut） |
| `I2cSlave(g: I2cSlaveGenerics)` | I2C 从机控制器（class，需 `new I2cSlave(...)`） |
| `Apb3I2cCtrl(generics: I2cSlaveMemoryMappedGenerics)` | APB3 I2C 主控 |

### 30. JTAG

| Class | 说明 |
|-------|------|
| `Jtag` | JTAG 信号 Bundle（tck, tms, tdi, tdo, tdoEnable） |
| `JtagTap` | JTAG TAP 控制器 |
| `Bscane2BmbMaster(usedId: Int, ignoreWidth: Int)` | Xilinx BSCANE2 → Bmb 桥 |
| `VJtag2BmbMaster(ignoreWidth: Int)` | Intel Virtual JTAG → Bmb 桥 |

---

## 第七部分：功能模块

### 31. FSM — 状态机

**源码**：`lib/src/main/scala/spinal/lib/fsm/StateMachine.scala`（469行）+ `State.scala`（429行）

#### StateMachine 完整 API

```scala
class StateMachine extends Area with StateMachineAccessor with ScalaLocated
```

| 方法 | 签名 | 说明 |
|------|------|------|
| `always` | `(doThat: => Unit): this.type` | 每个周期都执行（优先级高于状态内逻辑） |
| `goto` | `(state: State): Unit` | 跳转到指定状态（下一周期生效） |
| `forceGoto` | `(state: State): Unit` | 强制跳转（忽略 transitionCond） |
| `isActive` | `(state: State): Bool` | 当前是否在指定状态 |
| `isEntering` | `(state: State): Bool` | 下一周期是否进入该状态 |
| `isExiting` | `(state: State): Bool` | 当前周期是否离开该状态 |
| `setEntry` | `(state: State): Unit` | 设置入口状态 |
| `getEntry` | `(): State` | 获取入口状态 |
| `setEncoding` | `(encoding: SpinalEnumEncoding): Unit` | 设置状态编码（binarySequential/oneHot/custom） |
| `setEncoding` | `(spec: (State, BigInt)*): Unit` | 自定义编码映射 |
| `setTransitionCondition` | `(condition: Bool): Unit` | 条件跳转门控 |
| `startFsm` | `(): Unit` | 启动状态机 |
| `exitFsm` / `exit` | `(): Unit` | 退出状态机（回到 boot 状态） |
| `killFsm` | `(): Unit` | 强制终止状态机 |
| `disableAutoStart` | `(): Unit` | 禁止自动启动 |
| `makeInstantEntry` | `(): State` | 立即进入入口状态（跳过 boot） |
| `postBuild` | `(body: => Unit): Unit` | 构建后执行（可访问 stateReg） |
| `onStart` | `(body: => Unit): Unit` | 启动时执行 |
| `isStarted` / `isRunning` | `: Bool` | 是否已启动 |
| `isStopped` | `: Bool` | 是否停止 |
| `inCorruptedState` | `(): Bool` | 状态机是否进入非法状态 |

#### State 完整 API

```scala
class State(implicit stateMachineAccessor: StateMachineAccessor) extends Area with ScalaLocated
```

| 方法 | 签名 | 说明 |
|------|------|------|
| `onEntry` | `(doThat: => Unit): this.type` | 进入状态时执行一次 |
| `onExit` | `(doThat: => Unit): this.type` | 离开状态时执行一次 |
| `whenIsActive` | `(doThat: => Unit): this.type` | 在状态中时每周期执行 |
| `whenIsInactive` | `(doThat: => Unit): this.type` | 不在该状态时执行 |
| `whenIsNext` | `(doThat: => Unit): this.type` | 下一周期将进入该状态时执行 |
| `goto` | `(state: State): Unit` | 跳转到另一状态 |
| `exit` | `(): Unit` | 退出状态机 |
| `whenIsActiveWithPriority` | `(priority: Int)(doThat: => Unit): this.type` | 带优先级的 whenIsActive |

#### 特殊状态类型

| Class | 构造参数 | 说明 |
|-------|----------|------|
| `StateEntryPoint` | — | = `new State with EntryPoint`（入口状态语法糖） |
| `StateFsm(fsm: StateMachine)` | 嵌套状态机 | 嵌套 FSM 作为状态；`whenCompleted{...}` 在子 FSM 退出时执行 |
| `StateParallelFsm(fsms: StateMachine*)` | 多个嵌套 FSM | 并行嵌套 FSM；所有子 FSM 退出后才执行 `whenCompleted` |
| `StateDelay(cyclesCount)` | BigInt/Int/UInt/TimeNumber/CyclesCount | 等待固定周期数后执行 `whenCompleted` |

---

### 32. Pipeline 新版框架（spinal.lib.misc.pipeline）

**源码**：`lib/src/main/scala/spinal/lib/misc/pipeline/`

> **注意**：旧版 `spinal.lib.pipeline`（Pipeline/Stage/Stageable）已废弃，新设计应使用本框架。

#### Payload — 流水线数据类型定义

```scala
type Payload[T <: Data] = NamedType[T]  // 类型别名
val Payload = NamedType                  // 伴生对象
```

| 方法 | 签名 | 说明 |
|------|------|------|
| `apply` | `(gen: => T): Payload[T]` | 创建 Payload 定义（如 `Payload(UInt(8 bits))`） |

**用法**：`Payload` 是流水线中传输数据的类型标签，在各级 Node 间共享同一 Payload 名的信号自动传播。

#### Node — 流水线节点

```scala
class Node(defaultKey: Any = null) extends Area with NodeApi
object Node {
  def apply(): Node
  def apply(defaultKey: Any): Node
}
```

**NodeApi — 握手信号（可读写，用于驱动）：**

| 信号 | 类型 | 说明 |
|------|------|------|
| `valid` | `Bool` | 事务存在指示（上游驱动；不得依赖 ready） |
| `ready` | `Bool` | 可向下游传输（下游驱动反压） |
| `cancel` | `Bool` | 事务被取消（下游驱动） |

**NodeApi — 事务状态（只读，按需创建）：**

| 方法 | 返回 | 说明 |
|------|------|------|
| `isValid` | `Bool` | = `valid`（无 valid 信号时默认 True） |
| `isReady` | `Bool` | = `ready`（无 ready 信号时默认 True） |
| `isCancel` | `Bool` | = `cancel`（无 cancel 信号时默认 False） |
| `isFiring` | `Bool` | `isValid && isReady && !isCancel`，事务成功向前传输 |
| `isMoving` | `Bool` | `isValid && (isReady \|\| isCancel)`，事务即将离开本节点 |
| `isCanceling` | `Bool` | `isValid && isCancel`，事务正在被清理 |

**NodeApi — Payload 访问：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `apply` | `(key: Payload[T]): T` | 获取 Payload 在本节点的硬件信号 |
| `apply` | `(key: Payload[T], subKey: Any): T` | 带子键访问（用于多通道/多 lane 设计） |
| `apply` | `(subKeys: Seq[Any]): OffsetApi` | 批量子键访问，如 `node(1 to 2)(MY_PAYLOAD)` |
| `insert` | `(that: T): Payload[T]` | 创建新 Payload 并连接到给定组合信号 |

**NodeApi — Stream/Flow 接口：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `driveFrom` | `(stream: Stream[T])(con: (Node, T) => Unit): Unit` | 从 Stream 驱动节点（握手 + payload 回调） |
| `driveFrom` | `(flow: Flow[T])(con: (Node, T) => Unit): Unit` | 从 Flow 驱动节点 |
| `arbitrateFrom` | `(stream: Stream[T]): Unit` | 仅连接 Stream 握手（valid/ready），需手动赋值 payload |
| `arbitrateFrom` | `(flow: Flow[T]): Unit` | 仅连接 Flow 握手（valid） |
| `arbitrateTo` | `(stream: Stream[T]): Unit` | 仅输出 Stream 握手 |
| `arbitrateTo` | `(flow: Flow[T]): Unit` | 仅输出 Flow 握手 |
| `driveTo` | `(stream: Stream[T])(con: (T, Node) => Unit): Unit` | 输出到 Stream（握手 + payload 回调） |
| `driveTo` | `(flow: Flow[T])(con: (T, Node) => Unit): Unit` | 输出到 Flow |
| `toStream` | `(con: Node => T): Stream[T]` | 创建新 Stream 输出（自动连接握手） |
| `toFlow` | `(con: Node => T): Flow[T]` | 创建新 Flow 输出 |

**Node 其他：**

| 方法/成员 | 说明 |
|-----------|------|
| `implicit def stageablePiped2` | 隐式转换：`Payload[T]` → `T`（自动调用 `node(payload)`） |
| `class Area(defaultKey)` | 创建共享本 Node 的 NodeApi 区域 |
| `keyToData` | `LinkedHashMap[NamedTypeKey, Data]`，本节点已创建的 Payload 信号映射 |

#### Builder — 构建器

```scala
object Builder {
  def apply(head: Link, tail: Link*): Unit
  def apply(connectors: Seq[Link]): Unit
}
```

**构建流程**：`nodeSetup()` → `propagateUp()` → `propagateDown()` → `build()` → 各 Node `build()`

- `propagateDown`：从上游向下游传播 Payload 集合和 valid 信号需求
- `propagateUp`：从下游向上游传播 ready/cancel 信号需求和 forgetOne 传播
- `build`：每个 Link 生成实际硬件（寄存器、MUX、握手逻辑）

#### StagePipeline — 自动打拍流水线

```scala
class StagePipeline(defaultKey: Any = null) extends Area
```

| 方法 | 签名 | 说明 |
|------|------|------|
| `node` / `apply` | `(i: Int): Node` | 获取或创建第 i 级 Node |
| `first` | `: Node` | 第一级 Node（`nodes.keys.min`） |
| `last` | `: Node` | 最后一级 Node（`nodes.keys.max`） |
| `build` | `(withoutCollapse: Boolean = false): Unit` | 构建（自动在相邻 node 间插入 StageLink） |
| `class Area(i: Int)` | — | 创建 NodeMirror 区域，可在其中直接访问 node(i) 的 API |

**build 行为**：在 `min` 到 `max` 之间每对相邻 node 自动插入 `StageLink`，`withoutCollapse=true` 禁止气泡折叠。

#### StageCtrlPipeline — 带流控的自动流水线

```scala
class StageCtrlPipeline(defaultKey: Any = null) extends Area
```

| 方法 | 签名 | 说明 |
|------|------|------|
| `ctrl` | `(i: Int): CtrlLink` | 获取或创建第 i 级 CtrlLink |
| `first` | `: CtrlLink` | 第一级 CtrlLink |
| `last` | `: CtrlLink` | 最后一级 CtrlLink |
| `build` | `(): Unit` | 构建（CtrlLink 间自动插入 StageLink） |
| `class Ctrl(i: Int)` | — | 创建 CtrlLinkMirror 区域 |
| `class InsertArea` | — | 基于 `ctrl(0).up` 的 Area |

**build 行为**：在 `ctrl(min)` 到 `ctrl(max)` 之间，每对相邻 CtrlLink 的 `down→up` 自动插入 `StageLink`。

#### CtrlLink — 流控连接

```scala
class CtrlLink(up: Node, down: Node) extends Link with CtrlApi
object CtrlLink {
  def apply(up: Node, down: Node): CtrlLink
  def apply(defaultKey: Any = null): CtrlLink  // 自动创建 up/down Node
}
```

**CtrlApi — 流控方法：**

| 方法 | 签名 | 硬件效果 |
|------|------|----------|
| `haltWhen` | `(cond: Bool): Bool` | `down.valid:=False; up.ready:=False` |
| `haltIt` | `(): Unit` | = `haltWhen(True)`（用于 when 块内） |
| `throwWhen` | `(cond: Bool, usingReady: Boolean = false): Unit` | 取消事务：`terminate + forgetOne`（或 `ignoreReady`） |
| `throwIt` | `(usingReady: Boolean = false): Unit` | = `throwWhen(True)` |
| `terminateWhen` | `(cond: Bool): Bool` | `down.valid:=False`（仅隐藏下游） |
| `terminateIt` | `(): Unit` | = `terminateWhen(True)` |
| `duplicateWhen` | `(cond: Bool): Bool` | `up.ready:=False`（事务不前进但下游可见） |
| `duplicateIt` | `(): Unit` | = `duplicateWhen(True)` |
| `forgetOneWhen` | `(cond: Bool): Bool` | 通知上游忘记事务（不影响 down.valid） |
| `forgetOneNow` | `(): Unit` | = `forgetOneWhen(True)` |
| `ignoreReadyWhen` | `(cond: Bool): Bool` | `up.ready:=True`（忽略下游 ready） |
| `ignoreReadyNow` | `(): Unit` | = `ignoreReadyWhen(True)` |
| `bypass` | `(payload: Payload[T]): T` | 条件覆盖 payload（用于数据前递 forwarding） |
| `bypass` | `(payload: Payload[T], subKey: Any): T` | 带子键 bypass |
| `forkStream` | `(forceSpawn: Option[Bool], enabled: Bool = True): Stream[NoData]` | 分叉 Stream（阻塞直到 ready） |
| `forkFlow` | `(enabled: Bool = True): Flow[NoData]` | 分叉 Flow（不阻塞） |

**CtrlApi — 节点访问：**

| 方法 | 说明 |
|------|------|
| `up` | 上游 Node（NodeApi） |
| `down` | 下游 Node（NodeApi） |
| `isValid` | = `up.isValid` |
| `isReady` | = `down.isReady` |
| `apply(key: Payload[T]): T` | = `down(key)`，读取下游侧 Payload 信号 |
| `insert(that: T): Payload[T]` | = `down.insert(that)` |

#### StageLink — M2S 打拍连接

```scala
class StageLink(up: Node, down: Node) extends Link
object StageLink { def apply(up: Node, down: Node): StageLink }
```

| 配置方法 | 说明 |
|----------|------|
| `withoutCollapse(): this.type` | 禁止气泡折叠（默认 `collapseBubble=true`，ready 在下游空闲时提前拉高） |
| `withPayloadHold(): this.type` | 仅在 `valid && ready` 时更新 payload（默认仅 `ready` 时更新） |

**硬件行为**：valid/payload 寄存（M2S），ready 直连（带气泡折叠优化）。上游无 ready 需求时退化为纯寄存。

#### DirectLink — 组合连接

```scala
class DirectLink(up: Node, down: Node) extends Link
object DirectLink { def apply(up: Node, down: Node): DirectLink }
```

**硬件行为**：所有信号（valid/ready/cancel/payload）组合直连，零延迟零容量。支持 forgetOne 和 cancel 透传。

#### S2MLink — ready 打拍连接

```scala
class S2MLink(up: Node, down: Node) extends Link
object S2MLink { def apply(up: Node, down: Node): S2MLink }
```

**硬件行为**：ready 信号寄存（`rValid`），valid/payload 组合选择（上游或缓冲）。切断 ready→valid 组合路径，延迟 0 周期。支持 forgetOne 和 cancel 条件传播。

#### ForkLink — 一分多连接

```scala
class ForkLink(up: Node, downs: Seq[Node], synchronous: Boolean = false) extends Link
object ForkLink { def apply(up: Node, downs: Seq[Node], synchronous: Boolean = false): ForkLink }
```

| 参数 | 说明 |
|------|------|
| `synchronous=false` | 各输出独立 ready（每输出额外 1FF `linkEnable`）；先到达的输出先采样 |
| `synchronous=true` | 所有输出必须同时 ready；不支持 forgetOne |

**硬件行为**：`synchronous=false` 时，每个输出有独立使能寄存器，输出采样后标记完成，全部完成后 `up.ready` 拉高并复位所有寄存器。

#### JoinLink — 多合一连接

```scala
class JoinLink(ups: Seq[Node], down: Node) extends Link
object JoinLink { def apply(ups: Seq[Node], down: Node): JoinLink }
```

**硬件行为**：`down.valid = ups.map(_.isValid).andR`；所有 `up.ready = down.isValid && down.isReady`。Payload 从唯一提供它的上游传递给下游。不支持 forgetOne。

#### Link 类型对比

| Link | 延迟 | 容量 | valid 路径 | ready 路径 | forgetOne | cancel |
|------|------|------|-----------|-----------|-----------|--------|
| `StageLink` | 1 | 1 | M2S 寄存 | 直连(+折叠) | ✓ | — |
| `DirectLink` | 0 | 0 | 组合 | 组合 | 透传 | 透传 |
| `S2MLink` | 0 | 1 | 组合选择 | S2M 寄存 | 条件传播 | 条件传播 |
| `CtrlLink` | 0 | 0 | 条件组合 | 条件组合 | ✓ | ✓ |
| `ForkLink` | 0/1 | N×1FF | 组合 | 独立/同步 | ✓(async) | — |
| `JoinLink` | 0 | 0 | AND 组合 | 广播 | ✗ | — |

#### 旧版→新版 API 映射

> 旧版 `spinal.lib.pipeline` 已废弃，以下为迁移对照表。

**流控操作映射：**

| 旧版 API | 新版对应 | 差异说明 |
|----------|----------|----------|
| `stage.haltIt(cond)` | `ctrl.haltWhen(cond)` | 需 CtrlLink（StageLink 无流控） |
| `stage.throwIt(cond, root=true)` | `ctrl.throwWhen(cond)` | 语义更完整：terminate + forgetOne |
| **`stage.flushIt(cond, root=true)`** | **`ctrl.throwWhen(cond)`** | **全局冲刷 → 单点触发 + forgetOne 反向传播** |
| **`stage.flushNext(cond)`** | **`ctrl.forgetOneWhen(cond)`** | **冲刷下级 → 仅通知上游忘记，不清本级** |
| `stage.forkIt(cond)` | `ctrl.duplicateWhen(cond)` | 复制事务：`up.ready:=False`，下游仍可见 |
| `stage.spawnIt(cond)` | `node.valid := True`（手动） | 生成新事务；新版无专用原语 |
| `stage.forkStream(cond)` | `ctrl.forkStream(enabled=cond)` | CtrlLink 方法 |
| `stage.forkFlow(cond)` | `ctrl.forkFlow(enabled=cond)` | CtrlLink 方法，不阻塞 |
| `stage.toStream()` | `node.toStream { n => payload }` | 需显式提供 payload 构造闭包 |
| `stage.driveFrom(stream)` | `node.driveFrom(stream) { (n,p) => }` | 需显式提供 payload 回调 |
| `stage.driveFrom(stage, cond, values)` | Link 自动传播 Payload | 旧版手动指定值列表，新版自动匹配同名 Payload |

**数据类型与结构映射：**

| 旧版 API | 新版对应 | 差异说明 |
|----------|----------|----------|
| `Stageable[T](gen)` | `Payload[T](gen)` | 类型别名从 `HardType` 变为 `NamedType` |
| `new Pipeline` | `new StagePipeline` | 自动创建 StageLink 级联 |
| `new Stage` | `Node()` 或 `pip.node(i)` | 独立 Node 或编号节点 |
| `stage(KEY)` | `node(PAYLOAD)` | 访问 Payload 在本级的硬件信号 |
| `stage(KEY, subKey)` | `node(PAYLOAD, subKey)` | 带子键访问（多通道/多 lane） |
| `stage.insert(v)` | `node.insert(v)` | 创建新 Payload 并连接组合信号 |
| `stage.overloaded(key)` | — | 用 `node(PAYLOAD, subKey)` 替代 |
| `stage.resulting(key)` | — | 用 `node.insert()` 创建本地结果 |
| `stage.terminal(key)` | — | Payload 传播由 Link 自动管理 |
| `Connection.M2S(collapse, holdPayload, flushPreserveInput)` | `StageLink(up, down)` | 新增 `withoutCollapse`/`withPayloadHold`；`flushPreserveInput` 由 `throwWhen(usingReady=true)` 替代 |
| `Connection.S2M()` | `S2MLink(up, down)` | 新增 forgetOne/cancel 条件传播 |
| `Connection.DIRECT()` | `DirectLink(up, down)` | 新增 forgetOne/cancel 透传 |
| `Connection.QueueLowLatency(depth)` | — | 手动 `Node` + `StreamFifo` 实现 |

**事务状态标志映射：**

| 旧版 API | 新版对应 | 差异说明 |
|----------|----------|----------|
| `stage.isValid` | `node.isValid` | 相同语义 |
| `stage.isReady` | `node.isReady` | 相同语义 |
| `stage.isFiring` | `node.isFiring` | 新版增加 cancel 感知 |
| `stage.isStuck` | — | 用 `isValid && !isReady` 替代 |
| `stage.isChanging` | `node.isMoving` | 语义近似 |
| `stage.isRemoved` | `node.isCanceling` | 新版：`isValid && isCancel` |
| `stage.isFirstCycle` | — | 用 `isFiring` + 外部 Reg 替代 |
| `stage.isFlushed` | — | 用 `isCanceling` 或外部信号替代 |
| `stage.isThrown` | `node.isCanceling` | 近似对应：事务被取消 |
| `stage.isForked` | — | 用 `ctrl.forkStream` 返回值替代 |
| `stage.isFlushingNext` | — | 用 `forgetOneWhen` 条件信号替代 |
| `stage.isFlushingRoot` | — | 用 `throwWhen` 条件信号替代 |
| `stage.isSelfRemoved` | — | 等价于旧版 `isFlushingRoot` |
| — | `node.isCancel` / `node.cancel` | **新版新增**：cancel 信号 |

**冲刷机制差异详解**：

旧版通过全局 `flush` 信号广播，每级显式检查。新版无 flush 原语，通过 `forgetOne` 信号沿 Link 反向传播实现：

```
CtrlLink.propagateUp():
  up.ctrl.forgetOneCreate(or(down.ctrl.forgetOne, requests.forgetsOne))

StageLink.build():
  down.ctrl.forgetOne foreach { cond => down.valid clearWhen (cond) }
```

- `throwWhen(cond)` = `terminateWhen` + `forgetOneWhen`：清空本级 + 反向传播清空所有上游级
- `forgetOneWhen(cond)`：仅反向传播清空上游级，不清本级（局部冲刷）
- 传播经过每个 StageLink 时自动清除该级的 `valid` 寄存器，payload 保留但 valid=0，新数据自然覆盖

---

### 33. Timer / InterruptCtrl

**源码**：`lib/src/main/scala/spinal/lib/misc/Timer.scala`, `InterruptCtrl.scala`

#### Timer

```scala
case class Timer(width: Int) extends Component
```

| IO 信号 | 方向 | 类型 | 说明 |
|---------|------|------|------|
| `tick` | in | `Bool` | 计数使能脉冲 |
| `clear` | in | `Bool` | 清零计数器 |
| `limit` | in | `UInt(width bits)` | 比较上限值 |
| `full` | out | `Bool` | counter === limit |
| `value` | out | `UInt(width bits)` | 当前计数值 |

**行为**：`tick` 时 counter 递增；`clear` 时清零；`full` 在 counter 达到 limit 时拉高。

#### InterruptCtrl

```scala
case class InterruptCtrl(width: Int) extends Component
```

| IO 信号 | 方向 | 类型 | 说明 |
|---------|------|------|------|
| `inputs` | in | `Bits(width bits)` | 中断请求输入（电平触发） |
| `clears` | in | `Bits(width bits)` | 清除位（写 1 清除） |
| `masks` | in | `Bits(width bits)` | 中断屏蔽（1=允许） |
| `pendings` | out | `Bits(width bits)` | 挂起中断（= pendings_reg & masks） |

**行为**：`pendings_reg := (pendings_reg & ~clears) | inputs`；输出 `= pendings_reg & masks`。

---

## 第八部分：PackedBundle / IO / BlackBox

### 34. PackedBundle — 位紧凑 Bundle

**源码**：`lib/src/main/scala/spinal/lib/PackedBundle.scala`（267行）

```scala
class PackedBundle extends Bundle
class PackedWordBundle(wordWidth: BitCount) extends PackedBundle
```

**pack 定位方法（DataPositionEnrich 隐式类）：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `packFrom` | `(pos: Int): T` | LSB=pos，使用字段全位宽 |
| `packTo` | `(pos: Int): T` | MSB=pos，使用字段全位宽 |
| `pack` | `(range: Range): T` | 放置到指定 Range |
| `pack` | `(range: Range, endianness: Endianness=LITTLE): T` | 指定字节序对齐 |
| `skipOver` | `(count: BitCount): Unit` | 跳过指定位数 |

**打包/解包 API：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `packed` | `(): Bits` | 所有字段打包为 Bits |
| `unpack` | `(bits: Bits): Unit` | 从 Bits 解包到各字段 |
| `unpack` | `(bits: Bits, hi: Int, lo: Int): Unit` | 从子范围解包 |
| `getPackedWidth` | `(): Int` | 打包后总位宽 |
| `mappings` | `(): Seq[(Range, Data)]` | 位范围映射 |

**PackedWordBundle 扩展：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `inWord` | `(index: Int): T` | 放置到第 index 个字（基于 wordWidth 计算位偏移） |

### 35. IO 原语

| Class | 参数 | IO 信号 | 说明 |
|-------|------|---------|------|
| `TriState[T <: Data](dataType: HardType[T])` | — | `write: T`, `writeEnable: Bool`, `read: T` | 三态总线（read/write/enable 分离） |
| `ReadableOpenDrain[T <: Data](dataType: HardType[T])` | — | `write: T`, `read: T` | 可读开漏 IO（无 writeEnable） |
| `InOutWrapper[T <: Component](component: T)` | — | 自动替换 InOut → 分离信号 | 将 InOut 端口转为 read/write/enable |

### 36. BlackBox 厂商原语

| 厂商 | 模块 | 说明 |
|------|------|------|
| Xilinx | `MMCME`, `EHXPLLL` | MMCM/PLL 时钟管理 |
| Xilinx | `Bscane2(deviceId)` | BSCANE2 调试桥 |
| Altera | `VJtag` | Virtual JTAG |
| Lattice | ECP5 PLL/IO, iCE40 BlackBox | Lattice 厂商原语 |

---

## 第九部分：Misc

### 37. 杂项工具

| Object/Class | 签名 | 说明 |
|--------------|------|------|
| `Min` / `Max` | `(a: T, b: T): T` | 硬件最小/最大值 |
| `Clamp` | `(value: T, min: T, max: T): T` | 硬件钳位 |
| `Log2` | `(value: UInt): UInt` | 硬件 log2 |
| `SetFromFirstOne` | `(bits: Bits): Bits` | 从第一个 1 后全置 1 |
| `Napot` | `(bits: Bits): Bits` | NAPOT（Next Address Power Of Two）检测 |

---

> **参考索引：**
> - `spinal-syntax.md` — 完整语法规范（含 PackedBundle 用法示例）
> - `spinal-protocols.md` — Stream/Flow 协议详细用法与设计模式
> - `spinal-design-patterns.md` — 设计模式与实战指南
> - `SKILL.md` — 设计方法学核心
