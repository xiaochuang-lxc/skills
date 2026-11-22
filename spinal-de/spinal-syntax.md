# SpinalHDL 语法规范参考

> 从 SpinalHDL core 源码（39个Scala文件）中提取的完整语法参考。

---

## 1. 基础数据类型

### 1.1 Bool — 布尔类型

```scala
// 声明
val myBool = Bool()
val myBool2 = Bool(true)   // 带初始值

// 常量
True   // 硬件常量 1
False  // 硬件常量 0
```

**逻辑操作符：**

| 操作符 | 说明 | 返回类型 |
|--------|------|----------|
| `&&` / `&` | 逻辑与 | Bool |
| `\|\|` / `\|` | 逻辑或 | Bool |
| `!` / `~` | 逻辑非 | Bool |
| `^` | 异或 | Bool |
| `===` | 相等比较 | Bool |
| `=/=` | 不等比较 | Bool |
| `===` / `=/=` | 与 MaskedBoolean 比较 | Bool |

**赋值与控制方法：**

| 方法 | 说明 | 示例 |
|------|------|------|
| `set()` | 赋值为 True | `myBool.set()` |
| `clear()` | 赋值为 False | `myBool.clear()` |
| `setAll()` | 同 set() | `myBool.setAll()` |
| `clearAll()` | 同 clear() | `myBool.clearAll()` |
| `setWhen(cond)` | 当 cond 为 True 时置 True | `myBool.setWhen(request)` |
| `clearWhen(cond)` | 当 cond 为 True 时置 False | `myBool.clearWhen(done)` |
| `riseWhen(cond)` | 当前为 False 且 cond 为 True 时置 True | `active.riseWhen(req)` |
| `fallWhen(cond)` | 当前为 True 且 cond 为 True 时置 False | `active.fallWhen(ack)` |
| `toggleWhen(cond)` | 当 cond 为 True 时翻转 | `myBool.toggleWhen(en)` |
| `assignDontCare()` | 赋值为 don't care（Verilog `'x`） | `myBool.assignDontCare()` |

> ⚠️ `setWhen`/`clearWhen` 为后写获胜；多条件作用于同一信号时禁止用书写顺序表达优先级，必须用 `when/elsewhen/otherwise`（见 §17 条件赋值优先级）。

**边沿检测方法：**

| 方法 | 说明 | 返回 |
|------|------|------|
| `rise(initAt)` | 上升沿检测（带初始值） | Bool |
| `rise()` | 上升沿检测 | Bool |
| `fall(initAt)` | 下降沿检测（带初始值） | Bool |
| `fall()` | 下降沿检测 | Bool |
| `edge(initAt)` | 任意边沿检测（带初始值） | Bool |
| `edge()` | 任意边沿检测 | Bool |
| `edges(initAt)` | 完整边沿检测 → BoolEdges(rise,fall,toggle) | BoolEdges |
| `edges()` | 完整边沿检测 | BoolEdges |

**类型转换方法：**

| 方法 | 说明 |
|------|------|
| `asUInt` | 转为 UInt（1位） |
| `asUInt(bitCount)` | 转为指定宽度的 UInt |
| `asSInt` | 转为 SInt（1位） |
| `asSInt(bitCount)` | 转为指定宽度的 SInt |
| `asBits` | 转为 Bits（1位） |
| `asBits(bitCount)` | 转为指定宽度的 Bits |
| `#*(count)` | 重复 count 次 → Bits(count bits) |

**条件选择操作符：**

```scala
// 三元选择器（Mux builder）
val result = cond ? valueTrue | valueFalse
val result2 = cond ? valueTrue otherwise valueFalse  // 等价写法

// 直接 mux 方法
val result3 = cond.mux(valueTrue, valueFalse)

// 枚举类型也支持
val state = cond ? stateA | stateB
```

### 1.2 Bits — 无类型位向量

```scala
// 声明
val myBits = Bits(8 bits)
val myBits2 = Bits(widthOf(signal))  // 动态位宽

// 字面量
B"0000_0101"          // 二进制（默认）
B"h1A"                // 十六进制
B"8'h1A"              // 带位宽的十六进制
B"d42"                // 十进制
B"o77"                // 八进制
```

**位访问与提取：**

| 方法 | 说明 | 示例 |
|------|------|------|
| `x(n)` | 位选择（固定索引）→ Bool | `x(3)` |
| `x(uint)` | 位选择（动态索引）→ Bool | `x(idx)` |
| `x(hi downto lo)` | 位范围选择 | `x(7 downto 0)` |
| `x(lo, width bits)` | 从 lo 开始取 width 位 | `x(4, 4 bits)` |
| `x(offset, width bits)` | 动态偏移取位 | `x(idx, 8 bits)` |
| `x(range)` | Range 方式取位 | `x(0 until 8)` |
| `x.msb` | 最高位 → Bool | `x.msb` |
| `x.lsb` | 最低位 → Bool | `x.lsb` |
| `x.high` | 最高位索引 Int | `x.high` |
| `x.bitsRange` | 位范围 Range | `x.bitsRange` |

**位操作符：**

| 操作符 | 说明 | 位宽变化 |
|--------|------|----------|
| `\|` | 按位或 | 不变 |
| `&` | 按位与 | 不变 |
| `^` | 按位异或 | 不变 |
| `~` | 按位取反 | 不变 |
| `##` | 拼接（Bits 专用） | w(a) + w(b) |
| `#*(n)` | 重复 n 次 | n × w(this) |
| `>>` (Int) | 右移（位宽减小） | w - n |
| `<<` (Int) | 左移（位宽增大） | w + n |
| `>>` (UInt) | 动态右移（位宽不变） | w |
| `<<` (UInt) | 动态左移（位宽增大） | w + max(idx) |
| `\|>>` (Int) | 右移（位宽不变） | w |
| `\|<<` (Int) | 左移（位宽不变） | w |
| `\|>>` (UInt) | 动态右移（位宽不变） | w |
| `\|<<` (UInt) | 动态左移（位宽不变） | w |
| `rotateLeft(n)` | 左旋转（Int） | w |
| `rotateRight(n)` | 右旋转（Int） | w |
| `rotateLeft(uint)` | 左旋转（UInt 控制） | w |
| `rotateRight(uint)` | 右旋转（UInt 控制） | w |

**归约操作：**

| 方法 | 说明 |
|------|------|
| `orR` | 所有位或 → Bool |
| `andR` | 所有位与 → Bool |
| `xorR` | 所有位异或 → Bool |
| `norR` | 所有位或非 → Bool |
| `nandR` | 所有位与非 → Bool |
| `nxorR` | 所有位同或 → Bool |

**位片操作：**

| 方法 | 说明 | 示例 |
|------|------|------|
| `take(n)` / `takeLow(n)` | 取最低 n 位 | `x.take(4)` → `x(3 downto 0)` |
| `drop(n)` / `dropLow(n)` | 去掉最低 n 位 | `x.drop(4)` → `x(high downto 4)` |
| `takeHigh(n)` | 取最高 n 位 | `x.takeHigh(4)` |
| `dropHigh(n)` | 去掉最高 n 位 | `x.dropHigh(4)` |
| `splitAt(n)` | 在 n 处分割 → (高位, 低位) | `x.splitAt(4)` |
| `sliceBy(widths*)` | 按位宽分割 → List[Bits] | `x.sliceBy(2, 3, 5)` |
| `subdivideIn(n slices)` | 等分为 n 段 → Vec | `x.subdivideIn(4 slices)` |
| `subdivideIn(n bits)` | 按 n 位切分 → Vec | `x.subdivideIn(8 bits)` |
| `reversed` | 位序反转 | `x.reversed` |

**赋值与状态方法：**

| 方法 | 说明 |
|------|------|
| `:=` (Bits) | 标准赋值 |
| `:=` (String) | 从字符串赋值 |
| `:=` ((Any,Any)*) | 按位范围赋值：`x := (0 -> a, 1 -> b, default -> False)` |
| `resize(n)` | 调整位宽（高位补零） |
| `resizeLeft(n)` | 调整位宽（保持 MSB 位置） |
| `setAll()` | 所有位置 1 |
| `clearAll()` | 所有位置 0 |
| `setAllTo(value: Boolean)` | 按 Boolean 设置所有位 |
| `setAllTo(value: Bool)` | 按 Bool 信号设置所有位 |
| `assignDontCare()` | 赋值为 don't care |
| `andMask(cond)` | 当 cond 为 False 时清零 |
| `orMask(cond)` | 当 cond 为 True 时全置 1 |
| `xorMask(cond)` | 当 cond 为 True 时取反 |

**类型转换：**

| 方法 | 说明 |
|------|------|
| `asUInt` | 转为 UInt |
| `asSInt` | 转为 SInt |
| `asBool` | 转为 Bool（需恰好1位） |
| `asBools` | 转为 Vec[Bool]（每位一个 Bool） |
| `toDataType(dataType)` | 转为指定 Data 类型 |
| `aliasAs(t)` | 以另一类型别名读写（Union 语义） |

### 1.3 UInt — 无符号整数

```scala
val myUInt = UInt(8 bits)
val myUInt2 = U"8'hFF"
val myUInt3 = U(42)             // 从 Scala Int 创建
```

**算术操作符：**

| 操作符 | 说明 | 位宽变化 |
|--------|------|----------|
| `+` | 加法 | max(w(a), w(b)) |
| `-` | 减法 | max(w(a), w(b)) |
| `*` | 乘法 | w(a) + w(b) |
| `/` | 除法 | w(a) |
| `%` | 取模 | w(a) |
| `+^` | 安全加法（扩展1位） | max(w(a), w(b)) + 1 |
| `-^` | 安全减法（扩展1位） | max(w(a), w(b)) + 1 |
| `+\|` | 饱和加法 | max(w(a), w(b)) |
| `-\|` | 饱和减法 | max(w(a), w(b)) |

**比较操作符：** `===`, `=/=`, `>`, `>=`, `<`, `<=`
**比较操作符（MaskedLiteral）：** `===` / `=/=` 与 `M"10--"` 比较

**移位操作符：**

| 操作符 | 说明 | 位宽变化 |
|--------|------|----------|
| `>>` (Int) | 右移（位宽减小） | w - n |
| `<<` (Int) | 左移（位宽增大） | w + n |
| `>>` (UInt) | 动态右移（位宽不变） | w |
| `<<` (UInt) | 动态左移（位宽增大） | w + max(idx) |
| `\|>>` (Int) | 右移（位宽不变） | w |
| `\|<<` (Int) | 左移（位宽不变） | w |
| `\|>>` (UInt) | 动态右移（位宽不变） | w |
| `\|<<` (UInt) | 动态左移（位宽不变） | w |

**拼接操作符：**

| 操作符 | 说明 | 返回类型 |
|--------|------|----------|
| `@@` (UInt) | UInt 拼接 | UInt |
| `@@` (Bool) | UInt 与 Bool 拼接 | UInt |

**位操作符：** `|`, `&`, `^`, `~`（与 Bits 相同）
**归约操作：** `orR`, `andR`, `xorR`, `norR`, `nandR`, `nxorR`
**位访问：** `apply(Int)`, `apply(UInt)`, `apply(Int, BitCount)`, `apply(UInt, BitCount)`, `msb`, `lsb`

**定点数操作（sat/trim/round）：**

| 方法 | 说明 |
|------|------|
| `sat(m)` | 高位 m 位饱和截断 |
| `trim(m)` | 丢弃高位 m 位 |
| `floor(n)` | 向下截断 n 位 |
| `ceil(n, align)` | 向上取整 n 位 |
| `roundUp(n, align)` | 四舍五入（向上） |
| `roundDown(n, align)` | 四舍五入（向下） |
| `roundToZero(n, align)` | 向零取整 |
| `roundToInf(n, align)` | 向无穷取整 |
| `roundToEven(n, align)` | 向偶数取整 |
| `roundToOdd(n, align)` | 向奇数取整 |
| `round(n, align)` | 默认舍入（= roundToInf） |
| `floorToZero(n)` | 同 floor |
| `ceilToInf(n, align)` | 同 ceil |
| `fixTo(section, roundType)` | 定点数格式化到 Range |
| `fixTo(q, roundType)` | 定点数格式化到 QFormat |

**类型转换：**

| 方法 | 说明 |
|------|------|
| `asBits` | 转为 Bits |
| `asSInt` | 转为 SInt |
| `expand` | 高位扩展1位0（无符号→有符号安全） |
| `intoSInt` | 等价于 `expand.asSInt` |
| `resize(n)` | 调整位宽（高位补零） |
| `reversed` | 位序反转 |
| `twoComplement(enable)` | 2的补码（条件取反加一）→ SInt |
| `assignMask(M"...")` | 按掩码赋值（don't care 位不赋值） |
| `assignDontCare()` | 赋值为 don't care |
| `setAll()` / `clearAll()` | 全部置1/置0 |
| `:=` ((Any,Any)*) | 按位范围赋值 |

**环绕比较（wrap）：**

```scala
// 用于模运算比较（同位宽 UInt 的环绕语义）
x.wrap < y    // 环绕小于
x.wrap > y    // 环绕大于
x.wrap <= y   // 环绕小于等于
x.wrap >= y   // 环绕大于等于
x.wrap.min(y) // 环绕最小值
x.wrap.max(y) // 环绕最大值
```

### 1.4 SInt — 有符号整数

```scala
val mySInt = SInt(16 bits)
val mySInt2 = S"16'hFFFF"  // -1
```

**算术操作符：** 与 UInt 相同（`+`, `-`, `*`, `/`, `%`, `+^`, `-^`, `+|`, `-|`）
**比较操作符：** `===`, `=/=`, `>`, `>=`, `<`, `<=`（有符号语义）
**移位操作符：** 与 UInt 相同（`>>`, `<<`, `|>>`, `|<<`，支持 Int/UInt 参数）
**位操作符：** `|`, `&`, `^`, `~`

**SInt 特有操作：**

| 方法/操作符 | 说明 |
|------------|------|
| `unary_-` | 取负（`-mySInt`） |
| `sign` | 符号位 → Bool（= msb） |
| `symmetry` | 对称化（minValue 映射为 maxValue） |
| `expand` | 符号扩展1位 → SInt(w+1) |
| `@@` (SInt) | SInt 拼接 → SInt |
| `@@` (UInt) | SInt 与 UInt 拼接 → SInt |
| `@@` (Bool) | SInt 与 Bool 拼接 → SInt |
| `@*(count)` | 重复 count 次 |
| `rotateLeft(n)` / `rotateRight(n)` | 左/右旋转 |
| `twoComplement(enable)` | 条件2的补码 |
| `fixTo(section, roundType, sym)` | 定点格式化（可选对称化） |
| `fixTo(q, roundType, sym)` | 定点格式化到 QFormat |

**定点数操作（sat/trim/round）：** 与 UInt 相同接口，语义为有符号：
`sat(m)`, `trim(m)`, `floor(n)`, `ceil(n)`, `roundUp(n)`, `roundDown(n)`,
`roundToZero(n)`, `roundToInf(n)`, `roundToEven(n)`, `roundToOdd(n)`,
`round(n)`, `floorToZero(n)`, `ceilToInf(n)`, `fixTo(...)`

**类型转换：**

| 方法 | 说明 |
|------|------|
| `asBits` | 转为 Bits |
| `asUInt` | 转为 UInt |
| `resize(n)` | 调整位宽（符号扩展） |
| `reversed` | 位序反转 |
| `assignDontCare()` | 赋值为 don't care |
| `setAll()` / `clearAll()` | 全部置1（-1）/ 置0（0） |

### 1.5 字面量语法汇总

```scala
// Bits 字面量
B"1010"           // 二进制 = 10
B"hA"             // 十六进制 = 10
B"8'hA"           // 带位宽
B"1010_0101"      // 下划线分隔

// UInt 字面量
U"1010"           // 二进制
U"hFF"            // 十六进制
U"8'd255"         // 十进制带位宽

// SInt 字面量
S"1010"           // 有符号二进制
S"hFFFF"          // 有符号十六进制

// 掩码字面量
M"1010"           // 掩码（1=care, 0=don't care）
M"hA"
M"10--"           // - 表示 don't care
```

---

## 2. 高级数据类型

### 2.1 SpinalEnum — 枚举类型

```scala
// 定义枚举
object MyEnum extends SpinalEnum {
  val sIDLE, sREAD, sWRITE, sDONE = newElement()
}

// 使用枚举（信号声明）
val state = MyEnum()
val state2 = Reg(MyEnum()) init(MyEnum.sIDLE)

// 比较
state === MyEnum.sIDLE
state =/= MyEnum.sWRITE

// 编码方式
object MyEnum extends SpinalEnum(binarySequential)  // 顺序编码
object MyEnum extends SpinalEnum(binaryOneHot)       // 独热编码
object MyEnum extends SpinalEnum(native)             // 默认（编译器选择）
```

**关键类型关系：**
- `SpinalEnum` — 枚举定义（类型）
- `SpinalEnumElement[T]` — 枚举元素定义（如 `sIDLE`）
- `SpinalEnumCraft[T]` — 枚举信号（硬件实例）

### 2.2 AFix / SFix / UFix — 定点数

```scala
import spinal.core._

// AFix（推荐）——由 amplitude/resolution + signed 或 maxRaw/minRaw + exp 定义
val fp1 = AFix(maxRaw = 255, minRaw = 0, exp = 0 exp)  // 原始范围 + 指数
val fp2 = AFix(4 exp, -3 exp, signed = true)           // AFix(amplitude, resolution, signed)
val fpU  = AFix.U(8 bits)                              // 无符号整数 AFix
val fpS  = AFix.S(8 bits)                              // 有符号整数 AFix
val fpUQ = AFix.UQ(4 bits, 4 bits)                     // 无符号 Q 格式（整数位宽, 小数位宽）
val fpSQ = AFix.SQ(4 bits, 4 bits)                     // 有符号 Q 格式

// SFix / UFix（传统定点，spinal.core 内置工厂）
val s1 = SFix(4 exp, 8 bits)          // SFix(maxExp, bitCount)
val u1 = UFix(4 exp, 8 bits)          // UFix(maxExp, bitCount)

// QFormat（配合 AFix(Q) 使用）
val q = QFormat(width = 16, fraction = 8, signed = true)  // 或 UQ(16, 8) / SQ(16, 8)
val fpQ = AFix(q)
```

**AFix 操作符：** `+`, `-`, `*`, `/`, `===`, `=/=`, `>`, `<`, `>=`, `<=`, `resize()`, `trim()`

### 2.3 Bundle — 标准聚合类型

```scala
// 定义 Bundle
class MyBundle extends Bundle {
  val a = UInt(8 bits)
  val b = Bool()
  val c = Bits(16 bits)
}

// 使用
val myBundle = new MyBundle
myBundle.a := 42
myBundle.b := True

// Bundle 赋值
val bundle2 = new MyBundle
bundle2 := myBundle  // 整体赋值

// 带参数的 Bundle
class ConfigBundle(dataWidth: Int) extends Bundle {
  val data = Bits(dataWidth bits)
  val valid = Bool()
}
```

### 2.4 SpinalStruct — Verilog struct / VHDL record

```scala
// 定义 Struct
class MyStruct extends SpinalStruct {
  val x = UInt(8 bits)
  val y = UInt(8 bits)
  val flag = Bool()
}

// 使用
val myStruct = new MyStruct
myStruct.x := 10
myStruct.y := 20
```

生成 Verilog struct 或 VHDL record 类型。

### 2.5 TupleBundle — 基于 Scala Tuple 的 Bundle

```scala
import spinal.core._

// 使用 TupleBundle 将多个 Data 聚合为无名字段 Bundle（字段固定为 _1/_2/_3...）
val tb = TupleBundle(
  UInt(8 bits),
  Bool(),
  Bits(16 bits)
)

// 访问字段（位置名 _1/_2/_3）
tb._1 := 42
tb._2 := True
```

适用于需要类似 Tuple 的轻量级聚合，不需要定义完整的 Bundle 类。

### 2.6 Union — C 风格联合体

```scala
import spinal.core._

// 定义 Union
val myUnion = new Union {
  val asUInt = newElement(UInt(16 bits))
  val asBytes = newElement(Bits(16 bits))
  val asPair = newElement(new Bundle {
    val lo = UInt(8 bits)
    val hi = UInt(8 bits)
  })
}

// 写入一种表示
myUnion.asUInt := 0x1234

// 读取另一种表示（共享同一 Bits 空间）
val bytes = myUnion.asBytes  // 得到 0x1234 的 Bits 表示
```

### 2.7 HardMap — 键值复合类型

**源码**：`core/src/main/scala/spinal/core/HardMap.scala`

HardMap 是一种**按名称组织的复合数据类型**，与 Bundle 的关键区别在于：Bundle 的字段在编译时固定，而 HardMap 的元素可以在构造时**动态组装**。

#### 与 Bundle 的对比

| 特性 | Bundle | HardMap |
|------|--------|--------|
| 字段定义 | 编译时固定（`val x = UInt(8 bits)`） | 运行时动态组装 |
| 赋值方式 | 按字段名匹配（`:=`） | 按 NamedType 键名匹配 |
| 适用场景 | 固定接口定义 | 参数化/泛型接口、寄存器文件、动态总线 |
| 类型安全 | 编译期检查 | 运行时检查（键不匹配报错） |

#### 使用场景

**场景1：参数化寄存器文件**
```scala
// 寄存器数量由参数决定，无法用 Bundle 预定义
val regA = NamedType(UInt(8 bits))
val regB = NamedType(UInt(16 bits))
val regC = NamedType(Bool())

val regFile = HardMap(Seq(regA, regB, regC))
// regFile 等价于 Bundle { val regA: UInt(8 bits); val regB: UInt(16 bits); val regC: Bool }

// 通过键访问
regFile(regA) := 0x42
regFile(regB) := 0x1234
regFile(regC) := True
```

**场景2：两个 HardMap 按名称自动赋值**
```scala
val src = HardMap(Seq(regA, regB, regC))
val dst = HardMap(Seq(regA, regB, regC))

dst := src  // 按名称匹配：dst(regA) := src(regA), dst(regB) := src(regB), ...
// 如果键不匹配会报错："HardMap must have the same final class"
```

**场景3：动态构建 IO 接口**
```scala
// 根据配置参数动态决定 IO 包含哪些信号
val channels = (0 until channelCount).map(i => NamedType(UInt(dataWidth bits)))
val io_map = HardMap(channels: _*)
// 相当于动态生成 channelCount 个 UInt(dataWidth bits) 信号
```

#### 关键 API

| 方法 | 说明 |
|------|------|
| `HardMap(content: Seq[NamedType[_ <: Data]])` | 从 NamedType 序列构造 |
| `hm(key: NamedType[T]): T` | `apply` 按键访问元素 |
| `hm(key) := value` | 按键赋值（`update` + `:=`） |
| `dst := src` | 按名称匹配赋值（两个 HardMap 必须是同一子类） |
| `elements` | 获取所有 (name, Data) 对 |

### 2.8 PackedBundle — 位紧凑聚合类型

**源码**：`lib/src/main/scala/spinal/lib/PackedBundle.scala`

PackedBundle 继承自 Bundle，允许将各个字段**按位紧凑排列**到指定的 bit 位置。适用于寄存器映射、协议帧解析等需要精确控制位布局的场景。

```scala
import spinal.lib._

// 定义一个位紧凑的寄存器字
val regWord = new PackedBundle {
  val init   = Bool().packFrom(0)       // 位 0
  val stop   = Bool()                    // 位 1（自动紧接上一字段）
  val mode   = UInt(2 bits)             // 位 3..2（自动紧接）
  val result = Bits(16 bits).packTo(31) // 位 31..16（MSB 在 31）
}
// 总位宽：32 位
// 布局：[31..16: result][3..2: mode][1: stop][0: init]
```

#### pack 定位方法

| 方法 | 说明 | 示例 |
|------|------|------|
| `.packFrom(pos)` | 从 pos 位开始（LSB=pos），使用字段全位宽 | `Bool().packFrom(0)` → 占位 0 |
| `.packTo(pos)` | 到 pos 位结束（MSB=pos），使用字段全位宽 | `Bits(16 bits).packTo(31)` → 占位 16..31 |
| `.pack(range)` | 放置到指定 Range | `UInt(4 bits).pack(7 downto 4)` → 占位 7..4 |
| `.pack(range, endianness)` | 指定字节序对齐 | `.pack(0 to 7, LITTLE)` → 低位对齐 |
| 无定位标记 | 自动紧接上一字段 | `Bool()` → 紧接上一字段的下一位 |
| `skipOver(count)` | 跳过指定位数（下一个自动字段从跳过后的位置开始） | `skipOver(4 bits)` → 跳过 4 位 |

#### 打包/解包 API

| 方法 | 说明 |
|------|------|
| `packed` → `Bits` | 将所有字段打包为连续的 Bits |
| `unpack(bits)` | 从 Bits 解包到各字段 |
| `unpack(bits, hi, lo)` | 从 Bits 的子范围解包 |
| `getPackedWidth` → `Int` | 获取打包后的总位宽 |
| `mappings` → `Seq[(Range, Data)]` | 获取所有字段的位范围映射 |

#### PackedWordBundle — 按字 packing

```scala
// 按字（word）组织的紧凑 Bundle，每个字宽度固定
val wordPacked = new PackedWordBundle(8 bits) {
  val aNumber = UInt(8 bits).inWord(0)  // 字 0：位 7..0
  val bNumber = UInt(8 bits).pack(0 to 7).inWord(1) // 字 1：位 15..8
  val large   = Bits(18 bits).inWord(2) // 字 2-3：位 33..16
  val flag    = Bool()                   // 位 34（自动紧接）
}
```

### 2.9 Vec — 同质向量

```scala
// 声明
val myVec = Vec(Bool(), 8)              // 8个 Bool
val myVec2 = Vec(UInt(8 bits), 4)       // 4个 UInt(8)
val myVec3 = Vec(Reg(UInt(8 bits)), 4)  // 4个寄存器

// 访问
myVec(0) := True
val sum = myVec(3)

// 动态索引访问
myVec(idx) := someValue
val readVal = myVec(idx)
```

**Vec 常用方法：**

| 方法 | 说明 |
|------|------|
| `vec(i)` | 索引访问（固定 Int） |
| `vec(uint)` | 索引访问（动态 UInt） |
| `vec.foreach(f)` | 遍历每个元素 |
| `vec.map(f)` | 映射每个元素 |
| `vec.reduce(f)` | 归约 |
| `vec.zipWithIndex` | 带索引遍历 |
| `vec.asBits` | 转为 Bits |
| `vec.length` | 元素个数 |
| `vec.getWidth` | 总位宽 |
| `vec.apply(range)` | 子范围提取 → Vec |
| `vec.assignDontCare()` | 所有元素赋值为 don't care |

---

## 3. 接口类型

### 3.1 IMasterSlave — Master/Slave 方向切换

```scala
// 定义带方向的接口
class MyInterface extends Bundle with IMasterSlave {
  val valid = Bool()
  val data  = UInt(8 bits)
  val ready = Bool()

  override def asMaster(): Unit = {
    out(valid, data)
    in(ready)
  }
}

// 使用
val io = new Bundle {
  val input  = slave(MyInterface())   // 作为 slave：方向翻转
  val output = master(MyInterface())  // 作为 master：正常方向
}

// 简化写法
val cmd = slave(Stream(UInt(8 bits)))
val rsp = master(Stream(UInt(8 bits)))
```

### 3.2 Interface — SystemVerilog Interface

```scala
// 定义 SV Interface
case class MyIf(width: Int = 8) extends Interface with IMasterSlave {
  val wParam = addGeneric("WIDTH", width, default = "8")
  val a = Bits(width bits)
  tieGeneric(a, wParam)
  val b = Bool()
  val c = SInt(8 bits)

  override def asMaster = mst

  @modport
  def mst = {
    out(a, b, c)
  }

  @modport
  def slv = {
    in(a, b, c)
  }
}
```

生成 SystemVerilog interface + modport 定义。

---

## 4. 信号操作符

### 4.1 赋值操作符

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `:=` | 硬件赋值（等价于 VHDL `<=`） | `sig := value` |
| `:=` (String) | 从字符串赋值 | `myBits := "1010"` |
| `:=` ((Any,Any)*) | 按位范围赋值 | `x := (0 -> a, 1 -> b, default -> False)` |
| `init()` | 寄存器初始值 | `reg.init(value)` |
| `initZero()` | 寄存器初始值为 0 | `reg.initZero()` |
| `initNull(that)` | 仅当 that 非 null 时初始化 | `reg.initNull(v)` |
| `\=` | 变量赋值语义（组合逻辑值） | `sig \= value` |
| `default()` | 设置默认值 | `sig.default(defaultValue)` |
| `assignDontCare()` | 赋值为 don't care | `sig.assignDontCare()` |

### 4.2 比较操作符

| 操作符 | 说明 | 适用类型 |
|--------|------|----------|
| `===` | 硬件相等比较 → Bool | 所有 Data |
| `=/=` | 硬件不等比较 → Bool | 所有 Data |
| `===` / `=/=` | 与 MaskedLiteral 比较 | Bits/UInt/SInt/Bool |
| `=::=` | 仿真用相等比较 | 所有 Data |

### 4.3 自动连接与方向连接

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `<>` | 自动连接（根据 in/out 方向自动匹配） | `io.master <> io.slave` |
| `<<` | 流式连接（Stream/Flow 专用） | `output << input` |

### 4.4 拼接操作

#### 4.4.1 拼接读取（Verilog `{a,b}` → SpinalHDL）

```scala
// Verilog: wire [7:0] combined = {a, b};     // a 在高位，b 在低位
// SpinalHDL:
val combined = a ## b              // Bits 拼接（## 操作符）
val uCombined = u1 @@ u2           // UInt 拼接（@@ 操作符）
val sCombined = s1 @@ s2           // SInt 拼接

// Verilog: wire [11:0] multi = {a, b, c};    // 多个信号拼接
// SpinalHDL:
val multi = Cat(a, b, c, d)       // 多信号拼接 → Bits（a 在最低位，注意顺序与 Verilog 相反）
// 等价于：Cat(d, c, b, a) 在 Verilog 中为 {d, c, b, a}
```

#### 4.4.2 拼接赋值（Verilog `{a,b,c} = dataIn` → SpinalHDL）

```scala
// Verilog: {dataOut0, dataOut1} = dataIn;    // 一个信号拆分到多个目标
// SpinalHDL:
(dataOut0, dataOut1) := dataIn     // 元组赋值：dataIn 的低位给 dataOut0，高位给 dataOut1
// dataOut0 和 dataOut1 的位宽之和必须等于 dataIn 的位宽

// 示例：16 位数据拆分为 8 位 + 8 位
val dataIn  = in Bits(16 bits)
val lowByte = out Bits(8 bits)
val highByte = out Bits(8 bits)
(lowByte, highByte) := dataIn     // lowByte = dataIn[7:0], highByte = dataIn[15:8]

// 也支持 3 个及以上目标
(a, b, c) := wideData             // a 占最低位，c 占最高位
```

#### 4.4.3 多信号到多信号赋值（Verilog `{d,e} = {a,b,c}` → SpinalHDL）

```scala
// Verilog: {d, e} = {a, b, c};    // 拼接后赋值
// SpinalHDL 方式1：元组对元组
(d, e) := (a, b, c)               // 将 a,b,c 拼接后按位分配给 d,e
// 等价于：(d, e) := Cat(c, b, a)  // Cat 参数顺序是低位在前

// SpinalHDL 方式2：先拼接再赋值
(d, e) := a ## b ## c             // 先拼接为 Bits，再拆分赋值

// 示例：
val a = UInt(4 bits)              // 4 位
val b = UInt(4 bits)              // 4 位
val c = UInt(4 bits)              // 4 位
val d = out UInt(6 bits)          // 6 位
val e = out UInt(6 bits)          // 6 位
(d, e) := (a, b, c)               // 12 位 → 6+6 位分配
```

#### 4.4.4 重复拼接（Verilog `b = {n{a}}` → SpinalHDL）

```scala
// Verilog: assign b = {3{a}};    // 将 a 重复 3 次
// SpinalHDL 方式1：B() 字面量工厂（注意：不是 B(a, 3 bits)！）
val a = in Bits(2 bits)
val b = out Bits(6 bits)
b := B(a, 3)                      // B(data, times) — 重复 3 次，结果是 6 位
// ⚠️ 不要与 B(a, 3 bits) 混淆！B(a, 3 bits) 是 resize 到 3 位

// SpinalHDL 方式2：Repeat() 函数
b := Repeat(a, 3)                 // Repeat(data, times) — 等价于 B(a, 3)

// SpinalHDL 方式3：#* 操作符（Bits 专用）
b := a #* 3                       // 等价于 B(a, 3)

// UInt/SInt 重复用 @*
val u = out UInt(6 bits)
u := myUInt @* 3                  // UInt 重复 3 次

// Bool 重复
val flags = out Bits(4 bits)
flags := myBool #* 4              // 单 bit 重复 4 次
```

#### 4.4.5 其他拼接方式

```scala
// 按位范围赋值（拼接赋值的另一种写法）
myBits := (0 -> a, 8 -> b)        // a 占低 8 位，b 占高 8 位
myUInt := (0 -> x, 4 -> y, default -> False)

// 拼接赋值汇总对照表
// ┌──────────────────────┬──────────────────────────────────────┐
// │ Verilog              │ SpinalHDL                            │
// ├──────────────────────┼──────────────────────────────────────┤
// │ {a,b}                │ a ## b  (Bits) / a @@ b  (UInt/SInt) │
// │ {a,b,c}              │ Cat(a,b,c)  注意顺序相反              │
// │ {x,y} = data         │ (x,y) := data                        │
// │ {x,y} = {a,b,c}      │ (x,y) := (a,b,c) 或 (x,y) := a##b##c│
// │ {3{a}}               │ B(a,3) 或 Repeat(a,3) 或 a#*3        │
// └──────────────────────┴──────────────────────────────────────┘
```

### 4.5 位选择与位范围

```scala
// 固定索引位选择
val bit3 = signal(3)               // → Bool
val bitDyn = signal(idx)           // 动态索引 → Bool

// 固定范围位选择
val range = signal(7 downto 0)     // 范围选择
val sub = signal(4, 4 bits)        // 从第4位开始取4位

// 动态范围位选择
val dynRange = signal(idx, 8 bits) // 从动态位置取 8 位

// 位范围赋值
signal(7 downto 0) := someValue    // 部分位赋值
signal(idx, 8 bits) := otherValue  // 动态范围赋值

// 位宽调整
val resized = signal.resize(16)    // 调整到16位
```

### 4.6 条件表达式

```scala
// 三元选择器（Bool 条件）
val result = cond ? valueTrue | valueFalse
val result2 = cond ? valueTrue otherwise valueFalse  // 等价写法

// Mux 函数
val result3 = Mux(cond, valueTrue, valueFalse)

// Bool.mux 方法
val result4 = cond.mux(valueTrue, valueFalse)

// switch/is 多路选择
switch(sel) {
  is(0) { result := valueA }
  is(1) { result := valueB }
  default { result := valueDefault }
}
```

---

## 5. 寄存器与时序逻辑

### 5.1 Reg — 寄存器

```scala
// 基本寄存器
val myReg = Reg(Bool())
val myReg2 = Reg(UInt(8 bits))

// 带初始值的寄存器
val myReg3 = RegInit(False)
val myReg4 = Reg(UInt(8 bits)) init(0)

// 寄存器赋值
myReg := someValue

// 下一拍值
val next = RegNext(currentValue)
val nextWithInit = RegNext(currentValue, init = 0)

// 条件更新
val reg = Reg(UInt(8 bits)) init(0)
when(enable) {
  reg := reg + 1
}

// RegNextWhen — 条件锁存
val latched = RegNextWhen(input, enable)

// RegNextWhen 带初始值
val latchedInit = RegNextWhen(input, enable, init = 0)
```

**寄存器工厂完整列表：**

| 工厂 | 说明 | 示例 |
|------|------|------|
| `Reg(dataType)` | 声明寄存器 | `Reg(UInt(8 bits))` |
| `Reg(dataType, init, next)` | 带初始值和下一拍值 | `Reg(UInt(8 bits), init=0, next=io.x)` |
| `RegInit(init)` | 带复位初始值 | `RegInit(False)` |
| `RegNext(next)` | 下一拍值 | `RegNext(x)` |
| `RegNext(next, init)` | 下一拍值带初始值 | `RegNext(x, init=0)` |
| `RegNextWhen(next, cond)` | 条件锁存 | `RegNextWhen(x, en)` |
| `RegNextWhen(next, cond, init)` | 条件锁存带初始值 | `RegNextWhen(x, en, init=0)` |
| `Reg(enumType)` | 枚举寄存器 | `Reg(MyEnum())` |

**寄存器方法：**

| 方法 | 说明 |
|------|------|
| `reg.init(value)` | 设置初始值 |
| `reg.isReg` | 判断是否为寄存器（返回 Boolean） |
| `reg.setAsReg()` | 将信号标记为寄存器 |
| `initial(value)` | Verilog initial 块赋值（仅仿真） |

### 5.2 Latch — 锁存器

```scala
// 显式 Latch（不推荐，通常应避免）
val latch = Latch(UInt(8 bits))

// LatchWhen — 条件锁存
val latched = LatchWhen(nextValue, condition)
```

> **注意**：FPGA 设计中通常应避免 Latch，使用 Reg 代替。

---

## 6. 控制流

### 6.1 when / elseWhen / otherwise

```scala
// 基本用法
when(condition) {
  // 条件为 True 时执行
  signal := valueA
} elseWhen(otherCondition) {
  signal := valueB
} otherwise {
  signal := valueC
}

// 嵌套
when(cond1) {
  when(cond2) {
    signal := value1
  } otherwise {
    signal := value2
  }
}
```

### 6.2 switch / is / default

```scala
switch(state) {
  is(StateA) {
    output := valueA
  }
  is(StateB) {
    output := valueB
  }
  is(StateC, StateD) {  // 多值匹配
    output := valueCD
  }
  default {
    output := defaultValue
  }
}
```

### 6.3 for 循环展开

```scala
// 硬件展开（编译时展开为并行硬件）
for (i <- 0 until 8) {
  myVec(i) := input(i)
}

// 带条件的展开
for (i <- 0 until 8) yield {
  val result = myVec(i) === target
  result
}

// 注意：for 循环在硬件中是并行展开，不是顺序执行
```

---

## 7. 内存（Mem）

### 7.1 Mem 声明

```scala
// 创建 RAM
val mem = Mem(Bits(32 bits), 1024)           // 1024个32位字
val mem2 = Mem(UInt(8 bits), wordCount = 256) // 256个8位无符号字
val mem3 = Mem.fill(512)(UInt(16 bits))       // fill 语法

// 创建 ROM（只读）
val rom = Mem(UInt(8 bits), 256) init(
  Seq(0, 1, 2, 3, 4, 5)
)

// 从 BigDecimal 初始化 AFix Mem
val fpRom = Mem(AFix(8 exp, -4 exp, signed = true), Seq(0.5, 1.0, -0.25))

// 属性
mem.addressWidth   // 地址位宽
mem.wordCount      // 字数（深度）
mem.width          // 字位宽
mem.byteCount      // 字节数
mem.randBoot()     // 仿真时随机初始化
```

### 7.2 内存端口（core 层）

| 端口方法 | 说明 | 返回值 |
|----------|------|--------|
| `mem.readAsync(addr, readUnderWrite)` | 异步读（组合逻辑） | `T` |
| `mem.readSync(addr, enable, readUnderWrite, clockCrossing)` | 同步读（寄存器输出） | `T` |
| `mem.readSyncMixedWidth(addr, data, enable, ...)` | 同步读（混合位宽，直接驱动 data） | `Unit` |
| `mem.write(addr, data, enable, mask)` | 同步写 | `Unit` |
| `mem.writeMixedWidth(addr, data, enable, mask)` | 同步写（混合位宽） | `Unit` |
| `mem.readWriteSync(addr, data, enable, write, mask, ...)` | 同步读写复用端口 | `T` |
| `mem.readWriteSyncMixedWidth(...)` | 同步读写复用（混合位宽） | `U` |
| `mem.readAsyncWrite(addr, data, write, mask, ...)` | 异步读 + 同步写（共享端口） | `T` |
| `mem.readAsyncWriteMixedWidth(...)` | 异步读 + 同步写（混合位宽） | `U` |
| `mem(addr)` | 读写端口（赋值时写，读取时读） | `T` |

### 7.3 内存端口（lib 层 — Stream/Flow 接口）

| 端口方法 | 说明 | 返回值 |
|----------|------|--------|
| `mem.writePort()` | 写端口 → Flow[MemWriteCmd] | `Flow[MemWriteCmd[T]]` |
| `mem.writePortWithMask(maskWidth)` | 带掩码写端口 | `Flow[MemWriteCmdWithMask[T]]` |
| `mem.readSyncPort(readUnderWrite, clockCrossing)` | 同步读端口 → MemReadPort | `MemReadPort[T]` |
| `mem.readAsyncPort()` | 异步读端口 → MemReadPortAsync | `MemReadPortAsync[T]` |
| `mem.readAsyncPortBySyncReadRevertedClk` | 用反相时钟同步读模拟异步读 | `MemReadPortAsync[T]` |
| `mem.readWriteSyncPort(maskWidth, ...)` | 读写复用端口 → MemReadWritePort | `MemReadWritePort[T]` |
| `mem.readAsyncWritePort(...)` | 异步读+同步写端口 → MemReadAsyncWritePort | `MemReadAsyncWritePort[T]` |

**Stream 接口：**

| 端口方法 | 说明 | 返回值 |
|----------|------|--------|
| `mem.streamReadSync(cmd)` | Stream 驱动同步读 | `Stream[T]` |
| `mem.streamReadSync(cmd, crossClock)` | Stream 驱动同步读（跨时钟域） | `Stream[T]` |
| `mem.streamReadSync(cmd, linkedData, crossClock)` | Stream 同步读 + 附带数据 | `Stream[ReadRetLinked[T,T2]]` |
| `mem.streamReadSyncMultiPort(cmds, crossClock)` | 多 Stream 读端口仲裁 | `Vec[Stream[T]]` |

**Flow 接口：**

| 端口方法 | 说明 | 返回值 |
|----------|------|--------|
| `mem.flowReadSync(cmd)` | Flow 驱动同步读 | `Flow[T]` |
| `mem.flowReadSync(cmd, linkedData)` | Flow 同步读 + 附带数据 | `Flow[ReadRetLinked[T,T2]]` |

```scala
// 写端口（Flow 接口）
val wr = mem.writePort
wr.valid := writeEnable
wr.address := writeAddr
wr.data := writeData

// 同步读端口（Stream 接口）
val cmd = Stream(UInt(log2Up(1024) bits))
val rsp = mem.streamReadSync(cmd)
cmd << io.readCmd
io.readRsp << rsp

// 带附带数据的 Stream 读
val rsp2 = mem.streamReadSync(cmd, linkedData = someTag)
// rsp2.value = 读到的数据
// rsp2.linked = 附带的 tag

// 多端口仲裁
val rsps = mem.streamReadSyncMultiPort(Seq(cmd1, cmd2, cmd3))

// 读写复用端口
val rwPort = mem.readWriteSyncPort(maskWidth = 4)
rwPort.address := addr
rwPort.wdata := writeData
rwPort.enable := enable
rwPort.write := writeEnable
val readData = rwPort.rdata

// 同步读端口（MemReadPort 接口）
val rdPort = mem.readSyncPort(readUnderWrite = writeFirst)
rdPort.cmd.valid := readEnable
rdPort.cmd.payload := readAddr
val data = rdPort.rsp

// MemReadPort 的 writeFirst 旁路
rdPort.writeFirst(writeLast = wrPort)
```

### 7.4 Read-Under-Write 策略

```scala
// 同步读/写端口的 readUnderWrite 参数
writeFirst   // 读写同地址时读到新写入的值
readFirst    // 读写同地址时读到旧值
             // 注意：异步读不支持 readFirst
dontCare     // 读写同地址时值不确定（默认）

// DuringWrite 策略（异步读+同步写端口）
dontRead     // 写时不读
doRead       // 写时同时读
dontCare     // 写时读值不确定
```

### 7.5 内存技术类型

```scala
mem.setTechnology(ramBlock)       // 块 RAM
mem.setTechnology(distributedLut) // 分布式 LUT RAM
mem.setTechnology(registerFile)   // 寄存器堆
mem.setTechnology(auto)           // 自动选择（默认）

// 黑盒策略
mem.generateAsBlackBox()          // 强制翻译为黑盒
mem.preventAsBlackBox()           // 禁止翻译为黑盒
```

---

## 8. 组件模型

### 8.1 Component — 基本组件

```scala
class MyComponent extends Component {
  val io = new Bundle {
    val a = in Bool()
    val b = in Bool()
    val result = out Bool()
  }
  io.result := io.a & io.b
}

// 带参数的组件
class Adder(width: Int) extends Component {
  val io = new Bundle {
    val a = in UInt(width bits)
    val b = in UInt(width bits)
    val sum = out UInt(width + 1 bits)
  }
  io.sum := io.a +^ io.b
}

// 实例化子组件
val adder = new Adder(8)
adder.io.a := inputA
adder.io.b := inputB
val result = adder.io.sum
```

**Component 常用 API：**

| 方法 | 说明 |
|------|------|
| `setDefinitionName(name)` | 设置模块定义名称 |
| `noIoPrefix()` | 去除 io_ 前缀 |
| `rework { ... }` | 在父组件中重新打开子组件修改 |
| `Component.current` | 获取当前 Component |
| `Component.push(c)` / `pop()` | 手动管理组件上下文 |
| `parent` | 父组件引用 |
| `getAllIo` | 获取所有 IO 信号 |
| `isInBlackBoxTree` | 是否在黑盒树中 |

### 8.2 Area — 逻辑分组

```scala
// Area 不生成独立模块，仅用于逻辑组织
val logicArea = new Area {
  val counter = Reg(UInt(8 bits)) init(0)
  counter := counter + 1
}
logicArea.counter := 0  // 从外部访问
```

### 8.3 BlackBox — 黑盒集成

```scala
class PLLBlackBox extends BlackBox {
  // 方式一：通过 Generic 类定义参数
  val generic = new Generic {
    val WIDTH = 8
    val DEPTH = 16
  }

  val io = new Bundle {
    val clk_in = in Bool()
    val clk_out = out Bool()
    val locked = out Bool()
  }

  // 方式二：通过 addGeneric 方法添加参数
  addGeneric("WIDTH", 8)
  addGeneric("DEPTH", 16)
  addGeneric("NAME", "my_module")  // String 参数
  addGeneric("RATIO", 1.5)         // Double 参数
  addGeneric("ENABLE", true)       // Boolean 参数
  addGenerics("A" -> 1, "B" -> 2)  // 批量添加

  // 映射时钟域
  mapClockDomain(clock = io.clk_in)  // 映射时钟和复位
  // 或
  mapCurrentClockDomain(clock = io.clk_in, reset = io.rst)

  // 设置黑盒名称
  setBlackBoxName("my_pll")

  // 添加 RTL 文件路径
  addRTLPath("/path/to/pll.v")
}
```

**BlackBox 完整 API：**

| 方法 | 说明 |
|------|------|
| `addGeneric(name, value)` | 添加泛型参数（支持 Int/String/Double/Boolean/BaseType/TimeNumber/VerilogValues） |
| `addGenerics((name, value)*)` | 批量添加泛型参数 |
| `mapClockDomain(cd, clock, reset, enable, resetActiveLevel, enableActiveLevel)` | 映射时钟域信号到 ClockDomain |
| `mapCurrentClockDomain(clock, reset, enable, ...)` | 映射当前时钟域 |
| `setIoCd(cd)` | 设置所有 IO 的时钟域标签 |
| `setBlackBoxName(name)` | 设置黑盒定义名称 |
| `addRTLPath(path)` | 添加 RTL 文件路径 |
| `setInline(impl)` | 设置内联实现（BlackBoxImpl） |
| `setInlineVerilog(str)` | 设置内联 Verilog 代码 |
| `setInlineVhdl(str)` | 设置内联 VHDL 代码 |
| `spinalSimWhiteBox()` | 标记为 SpinalSim 白盒 |
| `replaceStdLogicByStdULogic()` | 将 std_logic 替换为 std_ulogic |
| `isUsingULogic` | 是否使用 std_ulogic |
| `isUsingNoNumericType` | 是否使用 noNumericType |
| `isDefaultGenericValue` | 是否有默认泛型值 |

**BlackBox 变体：**

```scala
// BlackBoxULogic：所有 std_logic 自动替换为 std_ulogic
class MyULogicBB extends BlackBoxULogic {
  // ...
}

// 常用 Tag
noNumericType     // 将 unsigned/signed 转为 std_logic_vector
uLogic            // std_logic → std_ulogic
addDefaultGenericValue // VHDL 中添加泛型默认值
```

### 8.4 命名控制

```scala
mySignal.setName("custom_name")
mySignal.dontName()
derived.setCompositeName(base, "plus1")  // 生成 "base_plus1"
noIoPrefix()  // 去除 io_ 前缀
```

---

## 9. 时钟域

```scala
// 声明时钟域
val coreClockDomain = ClockDomain(io.clk, io.reset)

// 自定义配置
val myClockDomain = ClockDomain(
  clock = io.clk, reset = io.reset,
  config = ClockDomainConfig(
    clockEdge = RISING, resetKind = ASYNC, resetActiveLevel = HIGH
  )
)

// 子时钟域
val slowArea = myClockDomain.apply(clock = slowClk, reset = slowReset)

// 复位配置
ClockDomainConfig(
  clockEdge = RISING,       // RISING / FALLING
  resetKind = ASYNC,        // ASYNC / SYNC
  resetActiveLevel = HIGH   // HIGH / LOW
)
```

---

## 10. 工具函数

```scala
// 位宽计算
log2Up(16)          // = 4，编码16个状态需要4位
log2Up(0)           // = 0
log2Up(1)           // = 0

// Gray 编码
Gray.encode(binary) // 二进制 → Gray 编码
Gray.decode(gray)   // Gray → 二进制

// 2的幂检查
isPow2(16)          // = true
isPow2(15)          // = false
isPow2(16, 32, 64)  // = true（多个检查）

// 向上取整
roundUp(10, 4)      // = 12（10向上取到4的倍数）

// 类型克隆
cloneOf(signal)     // 相同类型和位宽的新信号
cloneOf(HardType)   // 从 HardType 创建
weakCloneOf(signal) // 相同类型但位宽未固定

// 位宽查询
widthOf(signal)     // 返回位宽 Int
widthOf(HardType)   // HardType 位宽
widthOf(MaskedLit)  // MaskedLiteral 位宽

// 拼接
Cat(a, b, c)        // 拼接多个信号 → Bits（a 在最低位）

// Mux
Mux(cond, t, f)     // 三元选择器

// 信号缓存
signalCache(key) { ... }  // 组件级信号缓存（避免重复创建）
globalCache(key) { ... }  // 全局缓存

// HardType
HardType(UInt(8 bits))    // 延迟构造类型工厂
NamedType(UInt(8 bits))   // 带名称的 HardType
```

---

## 11. 单位系统

```scala
// 时间单位：hr, mn, sec, ms, us, ns, ps, fs
val t1 = 100 ns
val t2 = 1.5 us

// 位宽单位
val w1 = 8 bit
val w2 = 32 bits

// 周期
val c1 = 100 cycles

// 频率
val f1 = 100 MHz
```

---

## 12. 编译配置

### 12.1 SpinalConfig 完整参数

#### 基本配置

| 参数 | 类型 | 默认值 | 应用场景 | 效果 |
|------|------|--------|----------|------|
| `mode` | `SpinalMode` | `null` | 选择目标 HDL 语言 | 决定生成 VHDL、Verilog 或 SystemVerilog。通常不需要手动设置，通过 `SpinalVerilog`/`SpinalVHDL`/`SpinalSystemVerilog` 快捷方法自动设置 |
| `targetDirectory` | `String` | `"."` | 指定 RTL 输出目录，CI/CD 或多项目构建时隔离输出 | 所有生成的 RTL 文件写入该目录。也可用环境变量 `SPINAL_TARGET_DIR` 设置，适合 Makefile 统一管理输出路径 |
| `netlistFileName` | `String` | `null` | 自定义输出文件名，如统一命名为 `top_level` 或与芯片型号关联 | 生成的主 RTL 文件名（不含扩展名）。默认使用顶层组件名。设为 `"chip_top"` 则输出 `chip_top.v` |
| `device` | `Device` | `Device()` | 指定目标 FPGA/ASIC 厂商，影响复位策略和综合属性 | 影响：①`Device.XILINX` 允许 BOOT 复位，自动为异步 RAM 添加 `ram_style=distributed` 属性避免 Vivado 误推断；②`Device.ASIC` 禁止 BOOT 复位（`supportBootResetKind=false`）；③影响 VHDL 生成的 `ram_style`/`rom_style` 属性 |

#### 时钟域配置

| 参数 | 类型 | 默认值 | 应用场景 | 效果 |
|------|------|--------|----------|------|
| `defaultConfigForClockDomains` | `ClockDomainConfig` | `ClockDomainConfig()` | 统一全芯片的复位策略。ASIC 设计通常设为同步复位 `ClockDomainConfig(resetKind=SYNC)`；FPGA 设计通常用异步复位 `ClockDomainConfig(resetKind=ASYNC)` | 所有未显式配置的 ClockDomain 使用此配置。例如设为 `resetKind=SYNC, resetActiveLevel=LOW` 后，全芯片默认使用低电平同步复位，无需每个 ClockDomain 单独配置 |
| `defaultClockDomainFrequency` | `IClockDomainFrequency` | `UnknownFrequency()` | 指定默认时钟频率（如 `FixedFrequency(100 MHz)`），用于跨时钟域 CDC 检查和时序约束生成 | 设为具体频率后：①`StreamCCByToggle` 等 CDC 模块可自动计算握手超时；②`crossClockMaxDelay` Tag 可据此约束路径延迟；③生成 XDC/SDC 时序约束文件时包含频率信息 |

#### 信号/命名控制

| 参数 | 类型 | 默认值 | 应用场景 | 效果 |
|------|------|--------|----------|------|
| `globalPrefix` | `String` | `""` | 多 IP 集成到 SoC 时避免信号名冲突。如将 IP 命名为 `"i2c_"` 前缀 | 所有信号名加上指定前缀。`clk` → `i2c_clk`，`io_data` → `i2c_io_data`。在 Verilog 中添加到每个信号名上 |
| `anonymSignalPrefix` | `String` | `null`（内部默认 `"_T"`） | 自定义匿名信号前缀，使生成的 RTL 更易读。设为 `"_w"` 让中间信号看起来像 wire | 编译器自动生成的中间信号使用此前缀。`_T_32` → `_w_32`。在调试综合结果时，有意义的前缀更容易识别信号类型 |
| `privateNamespace` | `Boolean` | `false` | 多个相同组件实例集成时避免信号名冲突（如 4 个相同的 UART 模块） | Verilog 中为每个组件实例包裹在 `generate` 块中，创建独立命名空间。效果：两个 `MyModule` 实例的信号分别变为 `gen_uart0.signal` 和 `gen_uart1.signal`，避免扁平化后同名冲突 |
| `anonymSignalUniqueness` | `Boolean` | `false` | 大型 SoC 设计中确保匿名信号全局唯一，避免不同组件中 `_T_0` 重名 | 当多个组件生成相同匿名信号名时，自动添加组件名后缀。如两个组件中的 `_T_0` 变为 `_T_0_uart` 和 `_T_0_spi` |
| `nameWhenByFile` | `Boolean` | `true` | 调试时快速定位信号来源。根据 Scala 文件名和行号自动为 when/switch 块产生的条件信号命名 | 信号名包含源码位置信息，如 `when_UartTx_scala_42`、`switch_<文件>_l<行号>`（when.scala:79/153，1.11.0 已核实）。设为 false 则条件信号不命名，后续走匿名 `_zz_*` 前缀命名。**工程约定：必须设为 false**（DE/DV 一致，见 spinal-de SKILL.md 编码风格要点） |
| `normalizeComponentClockDomainName` | `Boolean` | `false` | 多个组件使用相同命名的时钟域时，确保生成一致的域名 | 将组件内的时钟域名称统一格式化（去除组件名前缀），避免 `uart_clk_domain` 和 `spi_clk_domain` 被当作不同时钟域 |
| `enumPrefixEnable` | `Boolean` | `true` | 设计中存在多个枚举类型且有同名枚举值时（如多个状态机都有 `sIDLE`） | 枚举值生成时带上类型名前缀：`State_sIDLE` 而非 `sIDLE`。防止不同枚举的相同值名在 Verilog 中产生 `localparam` 重定义错误 |
| `enumGlobalEnable` | `Boolean` | `false` | 大型设计中多个组件使用同一枚举类型，减少重复定义 | VHDL 中所有组件共用一个 package 中的枚举定义，而非每个组件各自定义。减少 VHDL 编译时间和代码量 |
| `_withEnumString` | `Boolean` | `true` | 仿真调试时需要波形中显示可读的枚举名（如 `sIDLE`）而非数字（如 `0`） | 为枚举值生成对应的字符串常量。仿真波形中可直接看到状态名。通过 `config.withoutEnumString()` 关闭，可减少 ROM 面积 |

#### 输出控制

| 参数 | 类型 | 默认值 | 应用场景 | 效果 |
|------|------|--------|----------|------|
| `oneFilePerComponent` | `Boolean` | `false` | 大型设计（>50 个组件）分文件管理，便于 Git 版本控制和团队分工审查 | 每个 Component 生成独立的 RTL 文件。如 `Uart.v`、`Spi.v`、`Top.v` 各自独立。缺点是文件数量多，综合工具需要 filelist |
| `keepAll` | `Boolean` | `false` | 调试阶段保留所有内部信号，便于ILA/仿真观察。发布版本应设为 false | 禁止编译器剪枝任何信号，即使未被使用也保留。效果：①寄存器数量增加（未被使用的寄存器也保留）；②面积增大；③可在仿真/ILA 中观察所有内部信号 |
| `onlyStdLogicVectorAtTopLevelIo` | `Boolean` | `false` | VHDL 顶层与第三方 IP 集成时，对方使用 `std_logic_vector` 而非 `unsigned` | 顶层 IO 全部使用 `std_logic_vector` 类型。内部仍使用 `UInt`/`SInt`，仅在顶层边界做类型转换。避免手动做 `std_logic_vector(unsigned_val)` 类型转换 |
| `genVhdlPkg` | `Boolean` | `true` | VHDL 设计中包含枚举或自定义类型时需要包文件。设为 false 仅在无枚举的简单设计中 | 生成 VHDL 包文件（`.vhd`），包含枚举定义、类型定义、常量等。所有使用枚举的 VHDL 文件需要 `use` 此包 |
| `genLineComments` | `Boolean` | `false` | 人工审查生成的 RTL 时，需要追溯信号对应的 Scala 源码位置 | 在生成的 RTL 每条赋值语句行尾添加源码位置注释，实际格式 `// @ <文件>.scala l<行号>`（Statement.scala:322 + ComponentEmitterVerilog.scala:679，1.11.0 已核实；VHDL 为 `-- @ ...`）。可用 `config.withLineComment` 启用。**工程约定：必须设为 true**，与 nameWhenByFile=false 配套保留 RTL↔Scala 映射（见 spinal-de SKILL.md 编码风格要点） |
| `inlineConditionalExpression` | `Boolean` | `false` | 生成更简洁可读的 Verilog 代码，减少 `if/else` 嵌套层级 | 将 `when/otherwise` 生成的条件赋值内联为三元表达式。`when c then a else b` → `assign out = c ? a : b;`，而非生成 `always` 块 |
| `mergeAsyncProcess` | `Boolean` | `false` | 减少 Verilog 中组合逻辑 `always @(*)` 块的数量。某些 Lint 工具对大量小 process 报警告 | 将同一组件中多个组合逻辑赋值合并为一个 `always @(*)` 块。效果：减少 process 数量，但单个 process 变大。某些综合工具对大 process 优化更好 |
| `mergeSyncProcess` | `Boolean` | `true` | 减少 Verilog 中时序逻辑 `always @(posedge clk)` 块的数量。默认启用 | 将同一时钟域的所有寄存器合并到一个 `always @(posedge clk)` 块。效果：一个组件一个时钟域只有一个时序 process，代码更整洁。设为 false 则每个寄存器独立 always 块（分组键含寄存器自身，ComponentEmitter.scala:202，1.11.0 已核实），RTL 结构与 Scala 寄存器一一对应。**工程约定：必须设为 false**（DE/DV 一致，便于波形调试定位，见 spinal-de SKILL.md 编码风格要点） |
| `asyncResetCombSensitivity` | `Boolean` | `false` | 某些旧版综合工具（如旧版 Synplify）要求组合逻辑敏感列表包含异步复位信号 | 在组合逻辑的敏感列表中添加异步复位信号。`always @(a or b or rst)` 而非 `always @(a or b)`。大多数现代工具不需要此设置 |
| `inlineRom` | `Boolean` | `false` | 小 ROM（<64 字）在 FPGA 上用查找表实现时，case 语句比数组初始化推断效果更好 | 将 ROM 生成为 `case` 语句而非数组初始化。效果：Xilinx 工具更容易推断为 LUT 而非 BRAM。适合小常量表（如正弦表、CRC 表） |
| `caseRom` | `Boolean` | `false` | 强制所有 ROM 用 case 语句实现，即使是大 ROM。与 `inlineRom` 类似但更激进，不区分 ROM 大小 | 所有 ROM 强制使用 case 语句生成。效果：大 ROM 也会生成巨大的 case 块，综合时间长但某些工具推断更准确 |
| `romReuse` | `Boolean` | `false` | 多个组件使用相同初始化内容的 ROM 时（如多个通道共用同一查找表），减少面积 | 检测内容相同的 ROM 并复用同一实例。效果：减少 BRAM/LUT 使用，但所有使用方共享同一物理 ROM，可能增加布线延迟 |
| `cutLongExpressions` | `Boolean` | `true` | 避免综合工具（特别是旧版 Vivado、Quartus）对超长表达式处理崩溃或耗时过长 | 将超过一定长度的逻辑表达式拆分为多级中间信号。如 `a & b & c & d & ...`（50 项）拆分为 `w0 = a & b & ... & z; w1 = w0 & ...`。默认启用，建议保持 |
| `withTimescale` | `Boolean` | `true` | Verilog 仿真需要时间精度声明。综合时可设为 false 减少文件头信息 | 在 Verilog 文件头添加 `` `timescale 1ns/1ps ``。仿真器据此确定时间单位。纯综合流程可关闭 |
| `svInterface` | `Boolean` | `false` | SystemVerilog 设计中使用标准 SV `interface` 定义总线接口，提高代码复用性 | 生成 SystemVerilog `interface` 和 `modport` 定义。需要组件实现 `Interface` trait。效果：总线接口可用 `interface` 实例化而非离散信号 |

#### 仿真/调试

| 参数 | 类型 | 默认值 | 应用场景 | 效果 |
|------|------|--------|----------|------|
| `dumpWave` | `DumpWaveConfig` | `null` | 仿真时记录波形，用于调试时序问题。通过 `config.dumpWave(depth=0, vcdPath="wave.vcd")` 设置 | 配置 VCD 波形转储。`depth=0` 表示全深度记录所有信号。设置后仿真时自动生成 VCD 文件，可用 GTKWave/Surfer 查看 |
| `verbose` | `Boolean` | `false` | 排查编译错误或了解编译流程各阶段耗时 | 输出详细的编译日志：每个 Phase 名称、执行时间、中间网表统计（信号数/寄存器数等）。用于定位编译慢的阶段或排查内部错误 |
| `formalAsserts` | `Boolean` | `false` | 形式化验证（SymbiYosys/JasperGold），在 RTL 中插入性质检查 | 在 RTL 中生成形式化属性：`assert`（必须成立）、`assume`（环境约束）、`cover`（可达性检查）。通常配合 `config.includeFormal` 使用 |
| `noAssert` | `Boolean` | `false` | 最终流片/发布版本去除所有断言，减少面积和仿真开销 | 禁止生成所有 `assert` 语句。效果：RTL 中不包含任何断言，减少仿真时间和综合面积。也可用 `config.withoutAssert` 快捷设置 |
| `noAssertAtTimeZero` | `Boolean` | `false` | 仿真开始时复位尚未生效，assert 在时间 0 误触发。典型场景：复位释放后立即检查 FIFO 非空 | 禁止在仿真时间零点触发 assert。效果：第一个时钟上升沿之后的 assert 正常工作，时间 0 的 assert 被跳过 |
| `noRandBoot` | `Boolean` | `false` | 需要确定性仿真结果时（如回归测试），所有寄存器上电为 0 | 禁止寄存器随机初始化，所有寄存器仿真开始时为 0。效果：每次仿真结果完全一致。默认 false 表示寄存器随机初始化，有助于暴露未初始化 bug |
| `randBootFixValue` | `Boolean` | `true` | 需要可重复的随机初始化仿真（如 CI 回归测试），确保每次随机种子相同 | 随机初始化使用固定种子。效果：每次仿真的随机初始值序列相同，结果可重复。设为 false 则每次仿真使用不同随机种子 |

#### 报告/元数据

| 参数 | 类型 | 默认值 | 应用场景 | 效果 |
|------|------|--------|----------|------|
| `headerWithDate` | `Boolean` | `false` | 需要在 RTL 文件中追踪生成时间，区分不同版本的输出 | 在生成的 RTL 文件头添加生成日期注释。效果：每次生成文件内容不同（即使源码未变），导致 Git diff 有变化。发布版本建议开启 |
| `headerWithRepoHash` | `Boolean` | `true` | 将生成的 RTL 与 Git 仓库特定提交关联，便于问题追踪和版本审计 | 在文件头添加 Git commit hash 注释。效果：可以从 RTL 文件反查对应的源码版本。离线环境（无 Git）时自动跳过 |
| `removePruned` | `Boolean` | `false` | 大型设计中剪枝信号报告过多，减少报告文件大小 | 从 SpinalReport 中移除被剪枝的信号信息。效果：`report.prunedSignals` 为空，减少内存占用和报告大小，但丢失剪枝调试信息 |
| `allowOutOfRangeLiterals` | `Boolean` | `false` | 兼容旧代码中枚举字面量超出定义范围的情况（如 SpinalHDL 早期版本） | 允许枚举字面量的值超出枚举定义的范围。默认 false 会在检测到时立即报错。仅在迁移旧项目时临时开启 |
| `dontCareGenAsZero` | `Boolean` | `false` | Verilator 仿真不支持 `'x`（不定态），需要将 dontCare 生成为确定值 0 | 将 `assignDontCare()` 生成为 `0` 而非 `'x`。效果：Verilator/iverilog 等二值仿真器可正确处理。Vivado/ModelSim 等多值仿真器可保持默认的 `'x` |
| `reportIncludeSourceLocation` | `Boolean` | `false` | 编译出错时需要快速定位到 Scala 源码的具体文件和行号 | 在编译报告和错误信息中包含 Scala 源码位置。效果：错误信息从 `signal xxx` 变为 `signal xxx (MyFile.scala:42)`，大幅提升调试效率 |
| `reportSourceLocationFormat` | `String` | `"$SEVERITY($FILE:$LINE) "` | 与 IDE 的错误格式匹配（如 VSCode 的终端跳转），或适配 CI 系统的错误解析 | 自定义源码位置输出格式。支持变量：`$SEVERITY`（错误级别）、`$FILE`（文件名）、`$LINE`（行号）。也可用环境变量 `SPINAL_REPORT_SOURCE_LOCATION_FORMAT` 设置 |
| `printFilelist` | `Boolean` | `true` | Makefile/CMake 构建系统需要自动获取生成的 RTL 文件列表 | 生成 `.f` 格式的 filelist 文件，列出所有生成的 RTL 路径。综合工具可用 `read_filelist` 或 `-f filelist.f` 直接读取 |
| `emitFullComponentBindings` | `Boolean` | `true` | VHDL 组件实例化时生成完整端口映射。设为 false 可简化代码但某些工具可能要求完整绑定 | VHDL 中生成完整的 component 声明和端口绑定。设为 false 时省略未连接的端口（使用默认值），代码更简洁 |

#### 混淆（IP 保护）

| 参数 | 类型 | 默认值 | 应用场景 | 效果 |
|------|------|--------|----------|------|
| `obfuscateNames` | `Boolean` | `false` | 交付 IP 给客户时保护设计意图，使 RTL 无法被轻易理解或逆向 | 混淆所有信号和模块名称为无意义的短名称。效果：`io_axi4_aw_addr` → `o_3`，使 RTL 几乎不可读。调试困难，仅用于最终交付 |
| `obfuscate` | `ObfuscateConfig` | `ObfuscateConfig()` | 需要选择性混淆：保留时钟/复位名以便集成，但混淆内部信号 | 精细控制混淆策略：`keepClkResetNames=true` 保留时钟复位名便于集成；`hierarchyKeepLevel=1` 保留顶层模块名；`prefix="enc_"` 设置混淆前缀 |

#### 定点数与位宽

| 参数 | 类型 | 默认值 | 应用场景 | 效果 |
|------|------|--------|----------|------|
| `fixToWithWrap` | `Boolean` | `true` | DSP 设计中大量使用定点数格式化，将格式化逻辑封装为独立模块便于综合优化 | `fixTo` 操作生成独立的 Wrap 组件（而非内联到父模块）。效果：格式化逻辑可被综合工具独立优化和复用，RTL 结构更清晰 |
| `bitVectorWidthMax` | `Int` | `4096` | 防止意外创建超大位宽信号（如错误地将 32 位信号移位 5000 位） | 限制 BitVector 的最大位宽。超过此值编译报错。4096 已足够大多数设计。超大位宽通常是代码 bug |

#### 顶层与结构

| 参数 | 类型 | 默认值 | 应用场景 | 效果 |
|------|------|--------|----------|------|
| `singleTopLevel` | `Boolean` | `true` | 标准芯片/FPGA 设计只有一个顶层。多芯片（如 chiplet）设计需要生成多个独立顶层 | 要求设计只有一个顶层组件。设为 false 允许同时生成多个独立顶层组件各自的 RTL，适用于多芯片封装 |
| `devicePhaseHandler` | `PhaseDeviceHandler` | `PhaseDeviceDefault` | 自定义厂商特定的综合优化行为。如替换 Xilinx 默认的 `ram_style` 策略 | 控制厂商特定的网表处理：①`onMemReadAsync`：异步 RAM 读的综合属性（默认对 Xilinx 添加 `ram_style=distributed`）；②`onCrossClockBuffer`：跨时钟域缓冲的约束；③`onCrossClockMaxDelay`：跨时钟域最大延迟约束 |

#### 扩展机制

| 参数 | 类型 | 默认值 | 应用场景 | 效果 |
|------|------|--------|----------|------|
| `phasesInserters` | `ArrayBuffer[(ArrayBuffer[Phase]) => Unit]` | 空 | 在编译流程的特定位置插入自定义检查或优化（如添加 DFT 插入、功耗分析） | 接收编译 Phase 列表的回调函数，可在任意位置插入自定义 Phase。高级用法，通常不需要 |
| `transformationPhases` | `ArrayBuffer[Phase]` | 空 | 添加自定义网表变换（如将特定 pattern 替换为优化实现、添加自定义扫描链） | 在标准编译流程后执行自定义变换 Phase。可访问完整网表并修改。用 `config.addTransformationPhase(phase)` 添加 |
| `memBlackBoxers` | `ArrayBuffer[Phase]` | 空 | 自定义内存黑盒策略。如使用 `blackboxAllWhatsYouCan` 让综合工具用 BRAM 原语替换所有可替换的 RAM | 决定哪些 Mem 被替换为黑盒（由综合工具推断）。默认 `blackboxOnlyIfRequested` 仅黑盒用户标记的 Mem。用 `config.addStandardMemBlackboxing(policy)` 添加 |
| `scopeProperties` | `LinkedHashMap[ScopeProperty[_], Any]` | 空 | 全局设置跨时钟域缓冲行为等库模块参数。如设置 `crossClockBufferPushToPopResetGen=false` 改变 CDC 缓冲的复位生成策略 | 设置全局的 ScopeProperty 值，影响所有使用这些属性的库模块。用 `config.setScopeProperty(key, value)` 设置 |
| `rtlHeader` | `String` | `null` | 在生成的 RTL 文件头添加版权声明、许可证或公司信息 | 在 RTL 文件最开头插入指定的字符串内容。如设为版权文本，所有生成文件的头部都包含此内容 |
| `debugComponents` | `HashSet[Class[_]]` | 空 | 定位特定组件的编译错误源码位置。将出问题的组件 Class 加入此集合 | 启用指定组件的 Scala 位置追踪（`scalaLocatedEnable`）。编译错误时显示该组件中信号的精确 Scala 源码位置 |
| `flags` | `HashSet[Any]` | 空 | 条件生成：综合时包含 DFT 逻辑、形式化验证时添加 assert、仿真时添加调试逻辑 | 设置生成标志，配合 `GenerationFlags` 在 Scala 代码中实现条件编译。通过 `config.includeSynthesis`/`includeFormal`/`includeSimulation` 设置 |

#### SpinalConfig 便捷方法

```scala
// 生成快捷方法
config.generateVerilog(new MyComponent)    // 等价于 config.copy(mode=Verilog).generate(...)
config.generateVhdl(new MyComponent)       // 等价于 config.copy(mode=VHDL).generate(...)
config.generateSystemVerilog(new MyComponent)

// 波形转储
config.dumpWave(depth = 0, vcdPath = "wave.vcd")  // 返回新的 SpinalConfig

// 标志设置（链式调用）
config.includeSynthesis      // 添加 synthesis 标志，flags 中启用 GenerationFlags.synthesis
config.includeFormal         // 添加 formal 标志 + 自动启用 formalAsserts=true
config.includeSimulation     // 添加 simulation 标志

// 命名与输出控制
config.withPrivateNamespace  // 等价于 privateNamespace=true
config.withLineComment       // 等价于 genLineComments=true
config.withoutLineComment    // 等价于 genLineComments=false
config.withGlobalEnum        // 等价于 enumGlobalEnable=true
config.withoutEnumString()   // 等价于 _withEnumString=false
config.withoutAssert         // 等价于 noAssert=true

// 内存与变换
config.addStandardMemBlackboxing(policy)  // 添加内存黑盒策略
config.addTransformationPhase(phase)      // 添加自定义变换阶段

// ScopeProperty
config.setScopeProperty(scopeProperty, value)  // 设置全局 ScopeProperty
```

### 12.2 ClockDomainConfig 参数

```scala
ClockDomainConfig(
  clockEdge           : EdgeKind = RISING,      // RISING / FALLING
  resetKind           : ResetKind = ASYNC,      // ASYNC / SYNC / BOOT / NO_RESET
  resetActiveLevel    : Polarity = HIGH,         // HIGH / LOW
  softResetActiveLevel : Polarity = HIGH,        // HIGH / LOW
  clockEnableActiveLevel : Polarity = HIGH       // HIGH / LOW
)
```

### 12.3 Device 预设

```scala
Device.XILINX    // Xilinx FPGA
Device.ALTERA    // Altera/Intel FPGA
Device.LATTICE   // Lattice FPGA
Device.ACTEL     // Microsemi/Actel FPGA
Device.EFINIX    // Efinix FPGA
Device.ASIC      // ASIC（不支持 boot reset）
Device.NONE      // 无特定器件
```

### 12.4 DumpWaveConfig

```scala
DumpWaveConfig(
  depth   : Int = 0,           // 波形转储深度（0=全深度）
  vcdPath : String = "wave.vcd" // VCD 文件路径
)

// 快捷方法
config.dumpWave(depth = 0, vcdPath = "wave.vcd")
```

### 12.5 ObfuscateConfig

```scala
ObfuscateConfig(
  keepDefinitionNames : Boolean = false,   // 保留模块定义名
  keepInstanceNames   : Boolean = false,   // 保留实例名
  keepClkResetNames   : Boolean = false,   // 保留时钟/复位名
  prefix              : String = "oo_",    // 混淆前缀
  hierarchyKeepLevel  : Int = 0            // 保持层级深度
)
```

### 12.6 内存黑盒策略

```scala
// 策略类型
blackboxAllWhatsYouCan           // 尽可能黑盒化所有可替换的内存
blackboxAll                      // 黑盒化所有内存（不可黑盒时报错）
blackboxRequestedAndUninferable  // 黑盒用户指定 + 不可推断的内存
blackboxOnlyIfRequested          // 仅黑盒用户指定的内存（默认）
blackboxByteEnables              // 黑盒使用字节掩码的内存

// 使用方式
config.addStandardMemBlackboxing(blackboxAllWhatsYouCan)
```

### 12.7 生成命令

```scala
// 快捷生成
SpinalVerilog(new MyComponent)
SpinalVHDL(new MyComponent)
SpinalSystemVerilog(new MyComponent)

// 配置生成
config.generateVerilog(new MyComponent)
config.generateVhdl(new MyComponent)
config.generateSystemVerilog(new MyComponent)

// 条件生成标志
config.includeSynthesis    // 包含 synthesis 标志
config.includeFormal       // 包含 formal 标志
config.includeSimulation   // 包含 simulation 标志

// 使用 GenerationFlags
if (GenerationFlags.synthesis) { /* 仅综合时执行 */ }
if (GenerationFlags.formal) { /* 仅形式化验证时执行 */ }

// 全局枚举
config.withGlobalEnum      // 所有组件共享枚举定义

// 注释控制
config.withLineComment     // 生成行内注释
config.withoutLineComment  // 禁止行内注释
```

### 12.8 SpinalReport — 生成结果

```scala
val report = SpinalVerilog(new MyComponent)

report.toplevel              // 顶层组件实例
report.toplevelName          // 顶层名称
report.globalData            // 全局数据
report.prunedSignals         // 被剪枝的信号集
report.unusedSignals         // 未使用的信号集
report.counterRegister       // 寄存器计数
report.generatedSourcesPaths // 生成的源文件路径
report.blackboxesSourcesPaths // 黑盒源文件路径
report.blackboxesIncludeDir  // 黑盒包含目录
report.rtlSourcesPaths       // 所有 RTL 源文件路径
report.rtlIncludeDirs        // 所有 RTL 包含目录

// 报告方法
report.printPruned()         // 打印被剪枝的信号
report.printUnused()         // 打印未使用的信号
report.printPrunedIo()       // 打印被剪枝的 IO
report.printRtl()            // 打印生成的 RTL
report.printZeroWidth()      // 打印零宽度信号
```

### 12.9 常用配置模板

```scala
// Xilinx FPGA 综合
val xilinxConfig = SpinalConfig(
  targetDirectory = "rtl",
  device = Device.XILINX,
  defaultConfigForClockDomains = ClockDomainConfig(
    clockEdge = RISING, resetKind = ASYNC, resetActiveLevel = HIGH
  ),
  dumpWave = DumpWaveConfig(depth = 0, vcdPath = "wave.vcd")
)
xilinxConfig.addStandardMemBlackboxing(blackboxAllWhatsYouCan)

// ASIC 设计
val asicConfig = SpinalConfig(
  targetDirectory = "rtl",
  device = Device.ASIC,
  defaultConfigForClockDomains = ClockDomainConfig(
    clockEdge = RISING, resetKind = SYNC, resetActiveLevel = LOW
  ),
  mergeAsyncProcess = true,
  dontCareGenAsZero = false
)

// 仿真配置
val simConfig = SpinalConfig(
  targetDirectory = "sim_rtl",
  defaultConfigForClockDomains = ClockDomainConfig(
    clockEdge = RISING, resetKind = ASYNC, resetActiveLevel = HIGH
  ),
  dumpWave = DumpWaveConfig(depth = 5, vcdPath = "sim.vcd")
)
```

---

## 13. 形式化验证

```scala
import spinal.core.formal._

// 任意值生成
val anySeq = anyseq(UInt(8 bits))     // 任意序列值（每拍可变）
val anyConst = anyconst(UInt(8 bits)) // 任意常量（整个验证期间不变）

// 形式化配置
FormalConfig().withBMC(10).doVerify(new Component { ... })    // 有界模型检查
FormalConfig().withProve(10).doVerify(new Component { ... })  // 证明

// Mem 形式化方法
mem.formalContains(word)              // 检查 Mem 是否包含某个字
mem.formalContains(cond)              // 检查是否存在满足条件的字
```

---

## 14. Tag 与属性

```scala
// 常用 Tag
signal.addTag(crossClockDomain)   // 跨时钟域信号
signal.addTag(noLatchCheck)       // 禁止 Latch 检查
signal.simPublic()                // 暴露给仿真
signal.addTag(randomBoot)         // 仿真时随机初始化
signal.dontSimplifyIt()           // 禁止编译器优化
signal.setAsAnalog()              // 标记为模拟信号
signal.isReg                      // 查询是否为寄存器

// Verilog/VHDL 属性
signal.addAttribute("mark_debug", "true")
signal.addAttribute("ASYNC_REG", "TRUE")
signal.addAttribute("DONT_TOUCH", "TRUE")

// 命名 Tag
signal.setName("custom_name")     // 设置信号名称
signal.dontName()                 // 禁止自动命名
signal.setCompositeName(base, "suffix")  // 组合名称

// 跨时钟域 Tag
crossClockDomain                // 跨时钟域标记
crossClockMaxDelay(1, true)     // 跨时钟域最大延迟
```

---

## 15. Data 通用操作

所有 Data 类型共享的操作：

| 方法 | 说明 |
|------|------|
| `x := y` | 硬件赋值 |
| `x === y` | 相等比较 → Bool |
| `x =/= y` | 不等比较 → Bool |
| `x <> y` | 自动连接（根据方向） |
| `x.init(v)` | 设置初始值 |
| `x.default(v)` | 设置默认值 |
| `x \ y` | 变量赋值语义（返回组合值） |
| `x.assignDontCare()` | 赋值为 don't care |
| `x.isUnknown` | 检查是否为未知值 → Bool |
| `x.setName(name)` | 设置名称 |
| `x.addTag(tag)` | 添加 Tag |
| `x.addAttribute(attr)` | 添加属性 |
| `x.asBits` | 转为 Bits |
| `x.isReg` | 是否为寄存器 |
| `x.isComb` | 是否为组合逻辑 |
| `x.isIo` | 是否为 IO |
| `x.getWidth` | 获取位宽 |
| `x.flatten` | 展平为 Seq[BaseType] |
| `x.clone()` | 克隆 |
| `x.getZero` | 获取零值 |

---

## 16. 编码约定与反模式

**推荐**：信号 `snake_case`，类 `PascalCase`，配置 `camelCase`
**推荐**：一文件一 Component + 伴生 object 工厂
**推荐**：`case class Config` + `require()` 验证
**推荐**：`noIoPrefix()` + 分块注释 `/*** ... ***/`

| 反模式 | 正确做法 |
|---------|----------|
| 大杂烩 Component | 拆分为多个小组件 |
| 直接信号连接 | 使用 Stream/Flow 协议 |
| 硬编码参数 | case class Config |
| valid 依赖 ready | valid 独立于 ready |
| 不完整 when | 补全 otherwise |

---

## 17. 代码风格规范

### Config 模式
```scala
case class CacheConfig(userAddrWidth: Int, userDataWidth: Int, ...) {
  require(isPow2(userDataWidth))
  val cacheSizePerWay = cacheSize / wayNum  // 派生参数
}
```

### Component 结构模板
```scala
/** 模块功能说明 */
class MyModule(config: MyConfig) extends Component {
  import config._
  val io = new Bundle {
    val input  = slave(Stream(DataType))
    val output = master(Stream(DataType))
  }
  noIoPrefix()
  /**** 功能块1 ***/
  // ...
  /**** 端口赋值 ***/
  io.output << someStream
}
object MyModule {
  def apply(input: Stream[T]): Stream[T] = {
    val m = new MyModule(defaultConfig)
    m.io.input << input; m.io.output
  }
}
```

### 注释规范
- 每个 Component 必须有 Scaladoc
- 每个 Config 必须说明参数
- 分块注释 `/*** ... ***/` 划分功能区域
- 关键设计决策必须有中文行内注释
- 状态机/流水线阶段必须有功能说明

### 条件赋值优先级（显式 when/elsewhen）

多条件作用于同一寄存器时，**必须用 `when/elsewhen/otherwise` 显式表达优先级链**，禁止依赖 `setWhen`/`clearWhen` 的书写顺序表达隐式优先级（SpinalHDL 后写获胜，优先级隐藏在语句顺序中，修改时极易出错）：

```scala
// ❌ BAD：优先级依赖书写顺序（setWhen 后写→置位获胜），意图不可见
round_loaded clearWhen (need_refill)
round_loaded setWhen (settle_fire)

// ✅ GOOD：优先级链显式——结算 fire 置位优先，其次 refill 清零，否则保持
when(settle_fire) {
  round_loaded := True
} elsewhen(need_refill) {
  round_loaded := False
}
```

- 寄存器无 `otherwise` 时隐式保持原值，不推断锁存器；组合信号必须补全 `otherwise`
- `setWhen`/`clearWhen` 仅允许单条件场景（无优先级冲突）；多条件一律 when/elsewhen
- 库组件内部实现（如 StreamArbiter 的 locked）不受此约束，但本仓库生成代码一律遵守

---

## 18. SpinalHDL 官方 lib 风格特征

```scala
// IMasterSlave + Bundle 定义接口
class MyBus extends Bundle with IMasterSlave {
  val addr = UInt(32 bits)
  val data = Bits(32 bits)
  override def asMaster(): Unit = { out(addr, data) }
}

// slave/master 设置方向
val cmd = slave(Stream(UInt(8 bits)))
val rsp = master(Stream(UInt(8 bits)))

// << 连接，<> 双向
output << input
output <> input

// noIoPrefix() 去除 io 前缀
// setCompositeName() 控制命名
// simPublic() 暴露信号用于仿真
// addPrePopTask() 后处理
```

---

## 19. 目录组织规范

### 19.1 树形结构原则

SpinalHDL 项目应采用树形目录结构，每个功能模块对应一个独立目录，模块内部按职责分层组织。

```
project/
├── top/                     # 顶层模块
│   ├── TopModule.scala
│   └── pkgintf/             # 顶层数据结构与接口定义（所有子模块可引用）
│       └── TopIntf.scala
│
├── submodule_a/             # 子模块 A
│   ├── ModuleA.scala        # 功能实现
│   ├── SubUnitA1.scala
│   └── pkgintf/             # 子模块 A 的数据结构定义（仅 A 内部使用）
│       └── ModuleAIntf.scala
│
└── submodule_b/             # 子模块 B
    ├── ModuleB.scala
    └── pkgintf/
        └── ModuleBIntf.scala

# 规则：如果 submodule_a 和 submodule_b 都需要某数据类型，
#       应将其放在 top/pkgintf/ 中，而非某个子模块的 pkgintf/ 中
```

### 19.2 pkgintf 目录规范

每个子模块目录下应建立 `pkgintf` 目录，专门放置：

| 内容 | 说明 | 示例 |
|------|------|------|
| **数据结构定义** | Bundle、SpinalEnum、case class 配置 | `class AxiWriteCmd extends Bundle` |
| **接口定义** | 模块 IO Bundle、IMasterSlave 接口 | `class ModuleAIO extends Bundle` |
| **类型别名** | 常用的 Payload、Stageable 定义 | `val MY_PAYLOAD = Payload(UInt(8 bits))` |

**规则**：`pkgintf` 中的文件应只包含数据结构和接口定义，不包含功能实现逻辑。

### 19.3 依赖方向规则

> **核心原则**：子模块仅可引用父级目录中定义的数据结构。父级不得引用子目录，同级子模块之间不得互相引用。如果多个子模块都需要同一数据结构，说明它应放在它们的公共父级 `pkgintf` 中。

```
✅ 允许的依赖方向：
  submodule_a/ModuleA.scala  → 引用  top/pkgintf/TopIntf.scala              （子引父）
  submodule_a/ModuleA.scala  → 引用  submodule_a/pkgintf/ModuleAIntf.scala  （子引自己的 pkgintf）

✘ 禁止的依赖方向：
  top/TopModule.scala        → 引用  submodule_a/pkgintf/ModuleAIntf.scala  （父引子）
  submodule_a/ModuleA.scala  → 引用  submodule_b/pkgintf/ModuleBIntf.scala  （同级互引）
```

> **判断标准**：如果一个数据结构被多个子模块使用，它就不属于任何单一子模块，而应提升到它们的公共父级 `pkgintf`。

**依赖图**：

```
           top/pkgintf/          ← 顶层数据结构（所有子模块可引用）
          /            \
  submodule_a        submodule_b
  pkgintf/           pkgintf/
     ↑                  ↑
  submodule_a        submodule_b          ← 各自引用自己的 pkgintf
```

- `top/pkgintf/` 中的类型可被 `submodule_a` 和 `submodule_b` 引用
- `submodule_a` 和 `submodule_b` 之间不得互相引用
- 如果两者都需要某类型，该类型应放在 `top/pkgintf/`

### 19.4 实践指南

| 场景 | 做法 |
|------|------|
| 多个子模块共享的数据类型 | 提升到公共父级 `pkgintf/` |
| 仅本模块使用的配置 | 放在本模块的 `pkgintf/` |
| 模块的 IO 接口定义 | 放在本模块的 `pkgintf/`，方便上层引用 |
| 顶层需要子模块的内部类型 | 将该类型提升到父级 `pkgintf/`，而非直接引用子目录 |
| 两个子模块都需要某类型 | 说明它不属于任何单一子模块，应提升到公共父级 `pkgintf/` |
