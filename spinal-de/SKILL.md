---
name: spinal-de
description: >-
  Use when designing, analyzing, or generating SpinalHDL RTL code from specs.
  Covers Component architecture, Stream/Flow protocols, bus interconnects,
  FSM/Pipeline patterns, cross-clock domain handling, and Verilog code generation.
  Use when receiving hardware design specifications targeting SpinalHDL.
  Use when a SpinalHDL design API is missing from reference docs, its internal
  semantics are uncertain, or dependency source verification is needed.
  Not for simulation/testbench work — use spinal-dv instead.
---

# SpinalHDL RTL 设计专家（DE）

## Overview

SpinalHDL 是基于 Scala 的硬件描述语言，通过 Scala 元编程生成硬件。核心原则：
- **类型安全**：编译期检查硬件错误（位宽、类型、方向）
- **组合式构建**：小模块通过协议接口组合成大系统
- **协议驱动**：Stream/Flow 协议标准化模块间通信，实现高内聚低耦合

**设计与仿真分离**：本 skill 只负责 RTL 设计（main 源码）。仿真/测试平台（SpinalSim、SimEnv、Test、记分板、波形、仿真运行环境）一律使用 **spinal-dv** skill，不在本 skill 内编写仿真代码。

## 设计决策流程

收到 Spec 后按以下顺序决策：

1. **接口需求** → 选择协议：有反压用 `Stream`，无反压用 `Flow`，分片用 `Fragment`
2. **状态需求** → 选择模式：顺序控制用 `FSM`（StateMachine），数据通路用 `Pipeline`
3. **互连需求** → 选择总线：低速外设 `APB`，高性能 `AXI`，RISC-V 用 `TileLink`，统一寄存器用 `RegIf`
4. **时钟需求** → 规划跨时钟域：`BufferCC`(信号)、`StreamFifoCC`(数据流)、`FlowCCByToggle`(脉冲)、Gray编码(指针)

## 模块划分原则

- **单一职责**：一个 Component 只做一件事，功能明确
- **协议边界**：模块间通过 Stream/Flow 通信，不直接操作内部信号
- **参数化设计**：用 `case class Config(...)` 传递配置，`require()` 验证约束
- **Area vs Component**：
  - `Area`：同一时钟域内的逻辑分组，不生成独立模块，零开销
  - `Component`：独立功能块，可复用，有独立 IO，生成独立 Verilog 模块

## 代码生成工作流

1. 提取接口需求 → 确定协议类型（Stream/Flow/Event）和方向（master/slave）
2. 提取功能需求 → 划分模块边界，确定 Component/Area 层次结构
3. 提取性能需求 → 确定流水线深度、总线带宽、FIFO 大小
4. 提取时钟需求 → 规划时钟域划分和跨时钟域同步策略
5. 生成代码骨架 → 定义 Bundle/Interface，实例化子模块，连接 Stream/Flow
6. 交付设计 → main 源码保持纯净（无 `simPublic`/`import spinal.core.sim._`）；用户要求仿真时，转 **spinal-dv** skill（SimEnv 继承 DUT、在 test 侧调 simPublic）

## 快速参考表

| 类型 | 用途 | 声明示例 |
|------|------|---------|
| `Bool` | 单bit布尔 | `val en = Bool()` |
| `Bits` | 无类型位向量 | `val data = Bits(8 bits)` |
| `UInt` | 无符号整数 | `val cnt = UInt(8 bits)` |
| `SInt` | 有符号整数 | `val offset = SInt(16 bits)` |
| `SpinalEnum` | 枚举状态 | `object State extends SpinalEnum { ... }` |
| `Stream[T]` | 有反压数据流 | `Stream(UInt(8 bits))` |
| `Flow[T]` | 无反压数据流 | `Flow(Bool())` |
| `Mem[T]` | 内存推断 | `Mem(Bits(32 bits), 1024)` |
| `Bundle` | 聚合类型 | `class MyBundle extends Bundle { ... }` |
| `Vec[T]` | 同质向量 | `Vec(Bool(), 8)` |

## 常见错误与对策

| 错误 | 原因 | 对策 |
|------|------|------|
| `valid` 组合依赖 `ready` | 违反 Stream 握手规则 | 确保 valid 路径不组合依赖 ready，插入寄存器 |
| 组合逻辑环路 | 信号循环依赖 | 插入 `RegNext` 打断环路 |
| 多驱动冲突 | 同一信号在多处被赋值 | 检查 `when/switch` 覆盖完整性 |
| 跨时钟域未同步 | 亚稳态风险 | 使用 `BufferCC`/`StreamFifoCC`/`FlowCCByToggle` |
| 位宽不匹配 | 隐式截断导致数据丢失 | 显式 `resize()` 或检查位宽计算 |
| 忘记 `init` | 寄存器上电状态不确定 | `RegInit()` 或 `.init()` 设置初始值 |
| `Latch` 推断 | `when` 条件不完整 | 补全 `otherwise` 或使用 `RegNext` |

## 编码风格要点

- 使用 `noIoPrefix()` 去除 io 前缀
- 使用 `/*** 功能块名称 ***/` 分块注释组织代码
- Config 用 `case class`，Component 内 `import config._`
- 伴生 `object` 提供 `apply()` 工厂方法
- 信号命名 `snake_case`，类名 `PascalCase`，配置参数 `camelCase`
- 条件赋值必须用 `when/elsewhen/otherwise` 显式表达优先级，禁止依赖 `setWhen`/`clearWhen` 书写顺序表达隐式优先级（后写获胜）
- 注释尽可能详尽，关键设计决策必须有中文说明
- **SpinalConfig 必须 `nameWhenByFile = false`**（工程约定，DE/DV 一致；默认 true 会把 when/switch 条件信号命名为 `when_<文件>_l<行号>`/`switch_<文件>_l<行号>`，false 时条件信号走匿名 `_zz_*` 命名；已源码核实 when.scala:79/153，1.11.0）
- **SpinalConfig 必须 `genLineComments = true`**（工程约定，与 nameWhenByFile=false 配套：信号名不带行号，改由生成 RTL 的每条赋值语句行尾注释 `// @ <文件>.scala l<行号>` 保留 RTL↔Scala 映射；已源码核实 Statement.scala:322 + ComponentEmitterVerilog.scala:679，快捷方法 `.withLineComment`）
- **SpinalConfig 必须 `mergeSyncProcess = false`**（工程约定，DE/DV 一致；默认 true 会把同时钟域寄存器合并进同一个 always 块，false 时每个寄存器独立 always 块，RTL 结构与 Scala 寄存器一一对应便于调试定位；已源码核实 ComponentEmitter.scala:202 分组键含 target，1.11.0）
- main 不混入仿真代码；仿真代码一律放 `src/test/scala` 镜像 main 包目录，SimEnv 继承 DUT 并在 test 侧调 simPublic（范式详见 **spinal-dv** skill）。DUT 内部成员为 `private` 而 test 需观察时，最小放宽为 `private[<包名>]`，仅此一处可见性调整，不加仿真逻辑

## 参考文件与加载策略

**两阶段加载**：架构设计阶段不加载 API 细节文档，避免细节干扰设计思路。

| 阶段 | 加载文档 | 用途 |
|------|----------|------|
| **架构设计** | `spinal-syntax.md` + `spinal-protocols.md` + `spinal-design-patterns.md` | 确定架构形态、选择设计模式 |
| **编码实现** | 追加 `spinal-api-reference.md` | 确认方法签名、参数类型、API 细节 |
| **内存读加固**（涉及真实 RAM 读延迟>1拍 / write-first 时） | 追加 `spinal-mem-hardening.md` | `libext.memext` 的 `MemExpand`/`MemWriteFirst` API |
| **源码核实**（文档缺口或 API 内部语义存疑时） | 走下方「依赖源码核实流程」 | 读与工程同版本的明文源码，杜绝凭记忆生成 API |

各文件职责：

- **语法规范**：`spinal-syntax.md` — 类型系统、操作符、控制流、编译配置、编码风格、目录组织（第1-19章）
- **协议参考**：`spinal-protocols.md` — Stream/Flow/Fragment、总线协议、RegIf、通信外设
- **设计模式**：`spinal-design-patterns.md` — 编译机制、FSM/Pipeline/跨时钟域/互连架构/Spec-to-Code 工作流
- **API 手册**：`spinal-api-reference.md` — 按 Class 组织的完整 API 参考（core 类型系统 + lib 协议/功能模块）
- **内存读加固**：`spinal-mem-hardening.md` — `libext.memext`（用户扩展库，非官方 core/lib）：`MemExpand` 支持 1/2 拍读延迟与 write-first 旁路、linked 附加信息；`MemWriteFirst` 组件支持读延迟>2拍。该库完整源码随附于 `assets/libext/`（无 `libext` 依赖时可直接拷入工程使用）

仿真手册（SpinalSim 框架/时序语义/SimEnv 范式/运行环境）不在本 skill 内，见 **spinal-dv** skill 的 `spinal-sim-reference.md`。

## 依赖源码核实流程（通用，禁止网络）

**触发条件**：参考文档未收录某 API、或需确认组件内部行为（如仲裁器掩码推进时机、工具函数语义）时。

**硬性原则**：
- 禁止访问浏览器/网络查源码；禁止凭记忆断言未收录 API 的语义
- 只依赖**本工程自身**的构建配置与依赖缓存，不依赖工程外恰好存在的其他源码 checkout（版本不可控）
- 回答与文档加固中，凡未经源码核实的语义必须显式标注"待核实"

**步骤**：

1. **从工程定位 jar**（两个来源，按序取用）：
   - 首选：读 `.idea/libraries/sbt__com_github_spinalhdl_*.xml`，`<SOURCES>` 节点给出 sources.jar 精确路径（`$USER_HOME$` 展开为用户主目录）
   - 兜底：读 `build.sbt`（及 `project/*.scala`）取 `spinalVersion` 与 `scalaVersion`，拼接 Coursier 缓存路径：
     - macOS：`~/Library/Caches/Coursier/v1/https/repo1.maven.org/maven2/com/github/spinalhdl/spinalhdl-{core,lib}_<scalaBinary>/<version>/spinalhdl-{core,lib}_<scalaBinary>-<version>-sources.jar`
     - Linux：`~/.cache/coursier/v1/https/repo1.maven.org/maven2/...`（其余同上）
     - `<scalaBinary>` 取 scalaVersion 前两段（如 2.11.12 → `_2.11`）
2. **确认存在**：用目录列表工具核实该路径下 sources.jar 实际存在
3. **解压——自建临时目录 + 自行执行，全程不等待用户**：
   - 先核对当前工具集。**含任一命令执行工具（终端/shell/run command/执行类 MCP）→ 立即自行执行以下完整序列**，不询问用户、不请用户建目录、不请用户确认路径：
     ```bash
     SRC_DIR=$(mktemp -d /tmp/spinalhdl-src-XXXXXX)   # 临时目录自建，不问用户要路径
     mkdir -p "$SRC_DIR/lib" "$SRC_DIR/core"
     unzip -o <lib-sources.jar路径> -d "$SRC_DIR/lib"
     unzip -o <core-sources.jar路径> -d "$SRC_DIR/core"
     ls "$SRC_DIR/lib/spinal/lib" | head              # 验证解压产物存在
     ```
   - 执行后记住 `$SRC_DIR` 实际路径，直接进入第 4 步读源码；同一会话内复用该目录，不重复解压
   - **唯一降级条件（可观察谓词）**：逐项核对当前会话工具清单、确认无任何命令执行工具后，向用户**列出工具清单作为证据**并说明能力边界，才允许给出上述命令请用户执行。未列工具清单证据就向用户输出解压/建目录命令 = 违规
   - Read 工具无法直读 jar 的原因：jar 是 ZIP 容器，条目内容为 DEFLATE 压缩二进制，直读只见 `PK` 魔数与乱码（IDEA 能打开是因其内置 jar 虚拟文件系统实时解压）
4. **读明文源码核实**：逐文件读取 `.scala`，结论引用具体文件与行号
5. **反哺文档**：核实后的 API 事实补入 `spinal-api-reference.md` 对应章节，标注核实所依据的版本号（仿真相关语义反哺至 spinal-dv 的 `spinal-sim-reference.md`）

**合理化借口对照表**（出现以下念头即停止，回到上述步骤）：

| 借口 | 事实 |
|------|------|
| "网上查一下更快" | 禁止网络，本地 sources.jar 与工程同版本，是唯一可信来源 |
| "桌面正好有份 SpinalHDL 源码，直接用" | checkout 版本不可控，必须从工程配置推导路径 |
| "IDEA 能打开 jar，我也能读" | jar 是 ZIP/DEFLATE，Read 不解压，必须先 unzip |
| "让用户执行解压就行" | 有执行工具必须自行执行，全程不等待用户 |
| "先问用户解压到哪个目录" | `mktemp -d` 自建临时目录，无需询问 |
| "好像没有执行工具，给用户命令吧" | 必须逐项核对工具清单并列出证据，才可降级 |
| "这个 API 我记得，直接写" | 未核实语义必须标注"待核实"，禁止当作事实输出 |

**Red Flags**（出现即回到步骤 3 重做）：
- 向用户输出解压/mkdir 命令，却未附工具清单证据
- 用"建议放在某目录"等软措辞替代自建目录动作
- 解压后不验证产物就直接宣称完成

## 覆盖范围声明

**已覆盖**（文档内容经源码核对）：
- `core`：类型系统、操作符、ClockDomain、Mem、SpinalConfig（SpinalSim 仿真框架由 spinal-dv 覆盖）
- `lib`：Stream/Flow/Fragment 及派生组件、fsm、pipeline（含新版）、跨时钟域原语、amba3/amba4 总线（APB/AXI4/AXI4-Lite）、com 外设（UART/SPI/I2C）、BusSlaveFactory、misc 常用工具、io 三态原语
- `libext.memext`（用户扩展库，源码在 `SpinalHDL-LibTools`，非官方 core/lib）：`MemExpand`/`MemWriteFirst` 内存读加固 —— 见 `spinal-mem-hardening.md`

**未覆盖**（涉及时走「依赖源码核实流程」读源码，勿凭记忆生成 API）：
- `lib/math`、`lib/dsptool` — 定点运算与 DSP
- `lib/system`、`lib/soc` — 系统级互连与 SoC 生成
- `lib/eda`、`lib/tools`、`lib/generator` — EDA 工具流与代码生成
- `lib/memory`、`lib/cpu`、`lib/graphic`、`lib/blackbox`、`lib/experimental` 等长尾模块
- `core` Fiber 框架、formal 形式化细节（文档仅概念级提及）