# libext.memext — 内存读加固 API 参考

> 针对 **真实 RAM 读延迟 > 1 拍** 与 **读期间写同地址（write-first）** 场景的 `Mem` 加固扩展。
>
> **来源仓库**：`SpinalHDL-LibTools`，包 `libext.memext`（非 SpinalHDL 官方 `core`/`lib`，属用户扩展库）。
> 本文所有签名均对照源码核验：`MemExpand.scala` / `MemWriteFirst.scala` / `package.scala`。

---

## 0. 为什么需要它

SpinalHDL 官方 `Mem.readSync(addr, en)` 及 `spinal.lib.MemPimped.streamReadSync/flowReadSync`
**一律假设读延迟 = 1 拍**（下一拍即返回数据）。但真实 Block RAM 常带输出寄存器、读延迟 ≥ 2 拍，
且官方 `write-first` 旁路（`MemReadPort.writeFirst`）也只覆盖 1 拍延迟。

`libext.memext` 补齐两块能力：

| 能力 | 官方库 | libext.memext |
|------|--------|---------------|
| 读延迟 = 1 拍 | ✅ `readSync` | ✅ `flowReadSync` / `streamReadSync` |
| 读延迟 = 2 拍 | ❌ | ✅ `...Enhanced` 系列 |
| 读延迟 > 2 拍 | ❌ | ✅ `MemWriteFirst` 组件 |
| write-first（读期间写同地址旁路） | 仅 1 拍（`MemReadPort.writeFirst`） | ✅ 覆盖 1/2/>2 拍全在途窗口 |
| 每命令附加信息随数据对齐返回（linked） | ✅ `ReadRetLinked` | ✅ `...WithLinked...` 系列 |

---

## 1. 引入方式

```scala
import spinal.core._
import spinal.lib._
import libext.memext._   // 引入隐式转换 MemExpand[T]，使 Mem[T] 获得下列方法
```

`package.scala` 定义隐式扩展：

```scala
implicit def MemExpand[T <: Data](mem: Mem[T]): MemExpand[T] = new MemExpand(mem)
```

即：先自行例化 `val mem = Mem(wordType, wordCount)`，随后 `mem.flowRead(...)` / `mem.streamRead(...)` 等
经隐式转换调用 `MemExpand` 的方法。**`MemExpand` 操作已存在的 `Mem[T]`；`MemWriteFirst`（§5）则是自带 `Mem` 的独立 Component。**

> **找不到 `libext` 依赖时**：本 skill 已随附该库源码（见 §8），把附件目录拷进工程 `src/main/scala/` 即可直接使用。

---

## 2. 数据契约类型

### 2.1 `MemoryWriteCmd[T]`（写指令，`libext.memext`）

```scala
case class MemoryWriteCmd[T <: Data](addreseWidth: Int, payloadType: HardType[T]) extends Bundle {
  val address = UInt(addreseWidth bits)
  val wdata   = payloadType()
}
```

| 成员 | 类型 | 说明 |
|------|------|------|
| `address` | `UInt(addreseWidth bits)` | 写地址 |
| `wdata` | `T` | 写数据 |

> ⚠️ **构造参数名源码即为 `addreseWidth`（少一个 s）**，使用具名参数时须照此拼写。
>
> ⚠️ **勿与官方 `spinal.lib.MemWriteCmd` 混淆**：官方为 `MemWriteCmd(dataType, addressWidth, maskWidth)`，字段是 `address` / **`data`** / `mask`；本库是 `MemoryWriteCmd(addreseWidth, payloadType)`，字段是 `address` / **`wdata`**。二者不通用。

`write_cmd` 参数类型为 `Flow[MemoryWriteCmd[T]]`，例：

```scala
val writeCmd = Flow(MemoryWriteCmd(log2Up(wordCount), UInt(32 bits)))
```

### 2.2 `ReadRetLinked[T, T2]`（带附加信息的读返回，来自 `spinal.lib`）

```scala
case class ReadRetLinked[T <: Data, T2 <: Data](readType: HardType[T], linkedType: HardType[T2]) extends Bundle {
  val value  = readType()    // 读出的内存数据
  val linked = linkedType()  // 随命令携带、与数据对齐返回的附加信息
}
```

`...WithLinked...` 系列方法的返回类型即 `Flow[ReadRetLinked[T, T2]]` / `Stream[ReadRetLinked[T, T2]]`。

---

## 3. API 选择速查

**第一步 — 按读延迟选族：**

| 读延迟 | Flow | Stream |
|--------|------|--------|
| 1 拍 | `flowReadSync` / `flowReadWithLinkedData` | `streamReadSync` / `streamReadWithLinkedData` |
| 2 拍 | `flowReadSyncEnhanced` / `flowReadWithLinkedDataEnhanced` | `streamReadSyncEnhanced` / `streamReadWithLinkedDataEnhanced` |
| 1 或 2（运行期决定） | `flowRead(read_delay)` / `flowReadWithLinked(read_delay)` | `streamRead(read_delay)` |
| > 2 拍 | — 用 `MemWriteFirst` 组件（§5） | — |

**第二步 — 是否需要 write-first：** 需要则 `writeFirst = true` 且 **必须** 传入 `write_cmd`（否则空指针）。

**第三步 — 是否携带每命令附加信息：** 需要则选 `...WithLinked...` 变体并传 `linkedData`。

> `read_delay` 仅接受 `1` 或 `2`，其它值触发 `assert` 失败。
> Stream 侧 **没有** `read_delay` 版的 linked 分派器（只有 `flowReadWithLinked`）；
> 需要「Stream + linked + 可选延迟」时，直接按延迟选 `streamReadWithLinkedData`（1 拍）或 `streamReadWithLinkedDataEnhanced`（2 拍）。

---

## 4. MemExpand 方法全表

以下方法均作用于 `Mem[T]`（经隐式转换）。`writeFirst` 默认 `false`，`write_cmd` 默认 `null`。

### 4.1 Flow 家族

| 方法 | 签名 | 读延迟 |
|------|------|--------|
| `flowReadSync` | `(read_cmd: Flow[UInt], writeFirst: Boolean = false, write_cmd: Flow[MemoryWriteCmd[T]] = null): Flow[T]` | 1 |
| `flowReadWithLinkedData[T2]` | `(read_cmd: Flow[UInt], linkedData: T2, writeFirst: Boolean = false, write_cmd: Flow[MemoryWriteCmd[T]] = null): Flow[ReadRetLinked[T, T2]]` | 1 |
| `flowReadSyncEnhanced` | `(read_cmd: Flow[UInt], writeFirst: Boolean = false, write_cmd: Flow[MemoryWriteCmd[T]] = null): Flow[T]` | 2 |
| `flowReadWithLinkedDataEnhanced[T2]` | `(read_cmd: Flow[UInt], linkedData: T2, writeFirst: Boolean = false, write_cmd: Flow[MemoryWriteCmd[T]] = null): Flow[ReadRetLinked[T, T2]]` | 2 |
| `flowRead` | `(read_cmd: Flow[UInt], read_delay: Int, writeFirst: Boolean = false, write_cmd: Flow[MemoryWriteCmd[T]] = null): Flow[T]` | `read_delay`（1/2） |
| `flowReadWithLinked[T2]` | `(read_cmd: Flow[UInt], linkedData: T2, read_delay: Int, writeFirst: Boolean = false, write_cmd: Flow[MemoryWriteCmd[T]] = null): Flow[ReadRetLinked[T, T2]]` | `read_delay`（1/2） |

- `read_cmd.payload` 为读地址（`UInt`）；返回 `Flow` 的 `valid` 由命令 `valid` 延迟对应拍数得到。
- linked 变体的 `linked` 对齐：1 拍用 `RegNext(linkedData)`，2 拍用 `Delay(linkedData, 2)`。
- `flowRead` / `flowReadWithLinked` 为分派器：`read_delay == 1` → 基础版，`== 2` → `...Enhanced`，其它 `assert` 失败。

### 4.2 Stream 家族（带反压）

| 方法 | 签名 | 读延迟 |
|------|------|--------|
| `streamReadSync` | `(read_cmd: Stream[UInt], writeFirst: Boolean = false, write_cmd: Flow[MemoryWriteCmd[T]] = null): Stream[T]` | 1 |
| `streamReadWithLinkedData[T2]` | `(read_cmd: Stream[UInt], linkedData: T2, writeFirst: Boolean = false, write_cmd: Flow[MemoryWriteCmd[T]] = null): Stream[ReadRetLinked[T, T2]]` | 1 |
| `streamReadSyncEnhanced` | `(read_cmd: Stream[UInt], writeFirst: Boolean = false, write_cmd: Flow[MemoryWriteCmd[T]] = null): Stream[T]` | 2 |
| `streamReadWithLinkedDataEnhanced[T2]` | `(read_cmd: Stream[UInt], linkedData: T2, writeFirst: Boolean = false, write_cmd: Flow[MemoryWriteCmd[T]] = null): Stream[ReadRetLinked[T, T2]]` | 2 |
| `streamRead` | `(read_cmd: Stream[UInt], read_delay: Int, writeFirst: Boolean = false, write_cmd: Flow[MemoryWriteCmd[T]] = null): Stream[T]` | `read_delay`（1/2） |

- 反压：`streamReadSync` 内部 `read_cmd.ready := ret.ready || !ret.valid`，并用 `rvalid` 寄存器保持输出；下游 `ret.ready` 拉低时命令侧自动停发。
- linked 变体用 `RegNextWhen(linkedData, read_cmd.ready)` 对齐，并通过 `arbitrationFrom` 继承握手。
- `...Enhanced` 用 `libext.streamExt.StreamStage`（无条件 payload 打拍，不同于官方 `m2sPipe`）插入第 2 拍。
- `streamRead` 为分派器：`1` → `streamReadSync`，`2` → `streamReadSyncEnhanced`。

### 4.3 write-first 语义（`writeFirst = true`）

`writeFirst` 表示 **写优先/写穿透**：当一次读命令在途期间，对 **同一地址** 发生写，则返回 **最新写入的数据**，而非 RAM 中的旧值。覆盖的「在途写窗口」随读延迟增大：

| 读延迟 | 覆盖的写发生时刻（相对读命令 T0） | 返回时刻 |
|--------|-----------------------------------|----------|
| 1 拍 | T0（与读命令同拍写同地址） | T0+1 |
| 2 拍 | T0（`read_with_write_conflict`）**与** T0+1（`read_before_write_conflict`） | T0+2 |
| > 2 拍 | 由 `MemWriteFirst` 覆盖 T0 … T0+(readLatency-1) 全窗口 | T0+readLatency |

- Flow 1 拍：`conflict = RegNext(read_cmd.valid & write_cmd.valid & (write_cmd.address === read_cmd.payload))`，命中则输出 `RegNext(write_cmd.wdata)`。
- Flow 2 拍：分别检测 T0 写（`wdata_t0_dly`）与 T0+1 写（当拍 `write_cmd.wdata`），按优先级选择后打一拍输出。
- Stream 版以 `read_cmd.ready`（即 fire）替代 `read_cmd.valid` 判定命令是否真正发出；2 拍 Stream 版将冲突标志与 3 份候选数据打包成 `Bits` 经 `StreamStage` 打拍，并在反压停顿时用 `..._hold` 寄存器保持，输出端再选择。

> **约束**：`writeFirst = true` 时 `write_cmd` 不可为 `null`（源码在其上取 `.valid/.address/.wdata`）。

---

## 5. MemWriteFirst — 读延迟 > 2 拍的独立组件

面向 Block RAM（内部按 2 拍读建模）并支持 **任意 `readLatency > 2`** 的写优先读，自带 `Mem` 例化与完整旁路流水线。

```scala
case class MemWriteFirst[T <: Data](
  wordType:    HardType[T],
  wordCount:   Int,
  readLatency: Int
) extends Component
```

- **约束**：`require(readLatency > 2)`（源码注释：block mem read latency = 2；≤ 2 拍请用 §4 的 `MemExpand`）。
- `noIoPrefix()`；内部 `Mem(wordType, wordCount) simPublic()`（可被仿真读取）。

**IO：**

| 端口 | 方向/类型 | 说明 |
|------|-----------|------|
| `wen` | `in Bool()` | 写使能 |
| `waddr` | `in UInt(log2Up(wordCount) bits)` | 写地址 |
| `wdata` | `in(wordType())` | 写数据 |
| `rcmd` | `slave(Flow(UInt(log2Up(wordCount) bits)))` | 读命令（payload = 读地址） |
| `rdata` | `master(Flow(wordType()))` | 读返回（`valid = Delay(rcmd.valid, readLatency)`） |

**行为**：内部 2 拍读（`mem.readSync` + `RegNext`）；对读地址做 `readLatency-1` 级打拍，逐级与 `waddr`（`wen` 有效时）比较得到各在途拍的读写冲突；用 `wdata` 的多级延迟对每个在途读做写优先旁路，最终 `rdata.payload` 取流水线末级。即：**任何在读流水线在途期间对同地址的写，都会被正确前递到对应读的返回值。**

---

## 6. 用法示例

### 6.1 Flow，2 拍读延迟 + write-first

```scala
import libext.memext._

class MemReader extends Component {
  val io = new Bundle {
    val rcmd = slave(Flow(UInt(10 bits)))
    val wcmd = slave(Flow(MemoryWriteCmd(10, UInt(32 bits))))
    val rdata = master(Flow(UInt(32 bits)))
  }
  noIoPrefix()

  val mem = Mem(UInt(32 bits), wordCount = 1024)
  mem.write(io.wcmd.address, io.wcmd.wdata, io.wcmd.valid)  // 自行驱动写端口

  // 2 拍读延迟 + 写优先：读在途期间对同地址的写会返回最新数据
  io.rdata := mem.flowRead(
    read_cmd   = io.rcmd,
    read_delay = 2,
    writeFirst = true,
    write_cmd  = io.wcmd
  )
}
```

### 6.2 Stream，1 拍读延迟 + 携带 linked 附加信息

```scala
import libext.memext._

val mem = Mem(UInt(32 bits), 1024)
val cmd  = Stream(UInt(10 bits))          // 读地址流
val tag  = UInt(4 bits)                    // 每命令附加信息（如事务 ID）

// 返回 Stream[ReadRetLinked[UInt, UInt]]：.value = 读数据，.linked = 对齐后的 tag
val rsp = mem.streamReadWithLinkedData(cmd, tag)
```

### 6.3 读延迟 > 2 拍（Block RAM）

```scala
import libext.memext._

// readLatency 必须 > 2；内部自带 Mem，直接连 IO
val bram = MemWriteFirst(UInt(32 bits), wordCount = 2048, readLatency = 3)
bram.io.wen   := writeEn
bram.io.waddr := writeAddr
bram.io.wdata := writeData
bram.io.rcmd  := readCmdFlow     // Flow(UInt(11 bits))
readDataFlow := bram.io.rdata    // Flow(UInt(32 bits))，valid 延迟 3 拍
```

---

## 7. 常见错误

| 错误 | 原因 | 对策 |
|------|------|------|
| `writeFirst = true` 却未传 `write_cmd` | 源码在 `write_cmd` 上取 `.valid/.address/.wdata` | 使能 write-first 时 **必须** 传 `Flow[MemoryWriteCmd[T]]` |
| `flowRead(..., read_delay = 3)` 报 assert | 分派器仅支持 1/2 | >2 拍改用 `MemWriteFirst` 组件 |
| 误用官方 `spinal.lib.MemWriteCmd` 作 `write_cmd` | 二者字段不同（`data` vs `wdata`，参数名不同） | 用 `libext.memext.MemoryWriteCmd(addreseWidth, payloadType)` |
| 具名构造 `MemoryWriteCmd(addressWidth = ...)` 编译失败 | 源码参数名为 `addreseWidth`（拼写如此） | 照源码拼写 `addreseWidth`，或用位置参数 |
| 找不到 `streamReadWithLinked(read_delay)` | Stream 侧无该分派器 | 按延迟直接选 `streamReadWithLinkedData`(1) / `streamReadWithLinkedDataEnhanced`(2) |
| 未 `import libext.memext._` 却调用 `mem.flowRead` | 方法来自隐式扩展 `MemExpand` | 补上 import |
| 对 `MemWriteFirst` 传 `readLatency = 2` | `require(readLatency > 2)` | ≤2 拍用 `MemExpand`；该组件专用于 >2 拍 |
| 假设返回 `valid` 与命令同拍 | 读有延迟，`valid` 相应延后 | Flow 延迟 = `read_delay`；`MemWriteFirst` 延迟 = `readLatency` |

---

## 8. 附件源码（无 `libext` 时直接使用）

本 skill 随附 `libext.memext` 及其唯一内部依赖的 **完整源码**，与上游 `SpinalHDL-LibTools` 逐字节一致。
当工程无法引用到 `libext` 库时，直接把附件目录拷入即可编译使用。

**位置**（相对本文件）：`assets/libext/`

```
assets/libext/
├── memext/
│   ├── package.scala        # 隐式转换 MemExpand[T]（5 行）
│   ├── MemExpand.scala      # Mem[T] 读加固扩展：11 个方法（319 行）
│   └── MemWriteFirst.scala  # 读延迟>2拍 write-first 组件（48 行）
└── streamExt/
    └── StreamStage.scala    # MemExpand 依赖的无条件打拍（43 行）
```

| 附件文件 | package | 作用 |
|----------|---------|------|
| `memext/package.scala` | `libext.memext` | `implicit def MemExpand[T](mem: Mem[T])` |
| `memext/MemExpand.scala` | `libext.memext` | §4 全部 Flow/Stream 读方法 + `MemoryWriteCmd` |
| `memext/MemWriteFirst.scala` | `libext.memext` | §5 组件 |
| `streamExt/StreamStage.scala` | `libext.streamExt` | `...Enhanced` 系列第 2 拍打拍，被 `MemExpand` 引用 |

**依赖闭包**：附件之间自洽（`MemExpand` → `streamExt.StreamStage` 已随附）；对外仅依赖 **官方 SpinalHDL** `spinal.core._` / `spinal.lib._`（`ReadRetLinked` 来自官方 `spinal.lib.Mem`，`MemWriteFirst` 另用 `spinal.core.sim._` 的 `simPublic`）。**无需其它 `libext` 模块。**

**使用步骤**：

1. 将 `assets/libext/` 整个目录拷入工程源码根（如 `src/main/scala/`），保持 `libext/memext`、`libext/streamExt` 的包路径不变（package 声明与目录一致）；
2. 确保工程已依赖官方 SpinalHDL（`core` + `lib`）；
3. 在使用处 `import libext.memext._`，即可对任意 `Mem[T]` 调用 §4 方法，或例化 §5 的 `MemWriteFirst`。

> **真源提示**：附件是便于自包含使用的快照，权威来源仍是 `SpinalHDL-LibTools/src/main/scala/libext/`。若上游更新，以仓库为准并同步刷新本附件。
