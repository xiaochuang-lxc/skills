---
name: spinalhdl-expert
description: >-
  Use when a SpinalHDL task spans both RTL design and simulation/verification,
  or when it is unclear which side applies, or when explicitly invoked via
  /spinalhdl-expert. Routes to the specialized skills: spinal-de for RTL
  design, spinal-dv for SpinalSim simulation. For pure design or pure
  simulation tasks, prefer invoking spinal-de or spinal-dv directly.
---

# SpinalHDL 专家（路由入口）

本 skill 已按**设计与仿真分离**拆分为两个专业 skill，本文件仅做路由，不承载任何技术内容。

## 路由规则

| 任务性质 | 目标 skill | 覆盖内容 |
|----------|-----------|----------|
| RTL 设计：Spec→架构→代码、Component/Stream/Flow/总线/FSM/Pipeline/跨时钟域、Verilog 生成、设计 API 语义核实 | **spinal-de** | 语法/协议/设计模式/API 手册/内存读加固 + libext 源码 |
| 仿真验证：SpinalSim 测试平台（SimEnv/Test）、驱动/监视/记分板、波形、仿真运行与调试（挂死/FST SIGSEGV/UNACCESSIBLE SIGNAL）、调度公平性测量、仿真 API 语义核实 | **spinal-dv** | SpinalSim 仿真手册（含已核实时序语义 §14、SimEnv 范式 §15、运行环境 §16、测量方法学 §17） |
| 混合任务（设计 + 仿真） | 先 **spinal-de** 完成 RTL，再 **spinal-dv** 编写测试平台 | 两侧文档不互相加载 |

## 执行要求

1. 判定任务性质后，**立即用 Skill 工具加载目标 skill**（spinal-de / spinal-dv），按其内容执行；不要凭本路由文件回答技术问题
2. 纯设计任务禁止加载仿真手册；纯仿真任务禁止加载设计文档——两侧参考文件已分别随各自 skill 分发
3. 两侧共享的「依赖源码核实流程」（禁止网络、本地 sources.jar、自行解压）在两个 skill 内各自完整维护，语义一致
4. 本目录不再存放参考文档；历史版本见 git 提交记录