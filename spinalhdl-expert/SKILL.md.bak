---
name: spinalhdl-expert
description: >-
  Use when designing, analyzing, or generating SpinalHDL code from specs.
  Covers Component architecture, Stream/Flow protocols, bus interconnects,
  FSM/Pipeline patterns, cross-clock domain handling, and code generation.
  Use when receiving hardware design specifications targeting SpinalHDL.
---

# SpinalHDL 专家

## Overview

SpinalHDL 是基于 Scala 的硬件描述语言，通过 Scala 元编程生成硬件。核心原则：
- **类型安全**：编译期检查硬件错误（位宽、类型、方向）
- **组合式构建**：小模块通过协议接口组合成大系统
- **协议驱动**：Stream/Flow 协议标准化模块间通信，实现高内聚低耦合

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
6. （可选）验证与仿真 → 仅当用户明确要求时，加载 `spinal-sim-reference.md` 编写 SpinalSim 驱动

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
- 注释尽可能详尽，关键设计决策必须有中文说明

## 参考文件与加载策略

**两阶段加载**：架构设计阶段不加载 API 细节文档，避免细节干扰设计思路。

| 阶段 | 加载文档 | 用途 |
|------|----------|------|
| **架构设计** | `spinal-syntax.md` + `spinal-protocols.md` + `spinal-design-patterns.md` | 确定架构形态、选择设计模式 |
| **编码实现** | 追加 `spinal-api-reference.md` | 确认方法签名、参数类型、API 细节 |
| **内存读加固**（涉及真实 RAM 读延迟>1拍 / write-first 时） | 追加 `spinal-mem-hardening.md` | `libext.memext` 的 `MemExpand`/`MemWriteFirst` API |
| **仿真验证**（仅用户明确要求时） | 追加 `spinal-sim-reference.md` | SpinalSim 仿真驱动编写 |

各文件职责：

- **语法规范**：`spinal-syntax.md` — 类型系统、操作符、控制流、编译配置、编码风格、目录组织（第1-19章）
- **协议参考**：`spinal-protocols.md` — Stream/Flow/Fragment、总线协议、RegIf、通信外设
- **设计模式**：`spinal-design-patterns.md` — 编译机制、FSM/Pipeline/跨时钟域/互连架构/Spec-to-Code 工作流
- **API 手册**：`spinal-api-reference.md` — 按 Class 组织的完整 API 参考（core 类型系统 + lib 协议/功能模块）
- **内存读加固**：`spinal-mem-hardening.md` — `libext.memext`（用户扩展库，非官方 core/lib）：`MemExpand` 支持 1/2 拍读延迟与 write-first 旁路、linked 附加信息；`MemWriteFirst` 组件支持读延迟>2拍。该库完整源码随附于 `assets/libext/`（无 `libext` 依赖时可直接拷入工程使用）
- **仿真手册**：`spinal-sim-reference.md` — SpinalSim 框架（后端配置/时钟域 API/Stream 驱动监视/Scoreboard/Phase）

## 覆盖范围声明

**已覆盖**（文档内容经源码核对）：
- `core`：类型系统、操作符、ClockDomain、Mem、SpinalConfig、SpinalSim
- `lib`：Stream/Flow/Fragment 及派生组件、fsm、pipeline（含新版）、跨时钟域原语、amba3/amba4 总线（APB/AXI4/AXI4-Lite）、com 外设（UART/SPI/I2C）、BusSlaveFactory、sim 仿真库、misc 常用工具、io 三态原语
- `libext.memext`（用户扩展库，源码在 `SpinalHDL-LibTools`，非官方 core/lib）：`MemExpand`/`MemWriteFirst` 内存读加固 —— 见 `spinal-mem-hardening.md`

**未覆盖**（涉及时直接阅读源码，勿凭记忆生成 API）：
- `lib/math`、`lib/dsptool` — 定点运算与 DSP
- `lib/system`、`lib/soc` — 系统级互连与 SoC 生成
- `lib/eda`、`lib/tools`、`lib/generator` — EDA 工具流与代码生成
- `lib/memory`、`lib/cpu`、`lib/graphic`、`lib/blackbox`、`lib/experimental` 等长尾模块
- `core` Fiber 框架、formal 形式化细节（文档仅概念级提及）
