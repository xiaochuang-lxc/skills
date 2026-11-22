---
name: spinal-dv
description: >-
  Use when writing, running, or debugging SpinalHDL simulation code with
  SpinalSim — SimEnv/Test testbenches, StreamDriver/StreamMonitor, scoreboards,
  waveform capture, clock/reset stimulus. Use when simulation fails or
  misbehaves: hangs, UNACCESSIBLE SIGNAL, Verilator FST SIGSEGV, scoreboard
  mismatches, same-edge race doubts, scheduler fairness/byte-ratio measurement.
  Use when SpinalSim thread/wakeup/write timing semantics are uncertain.
  Not for RTL design or Verilog generation — use spinal-de instead.
---

# SpinalHDL 仿真验证专家（DV）

## Overview

本 skill 只负责 SpinalHDL 仿真验证（test 侧）：SpinalSim 测试平台编写、运行、调试与测量方法学。**设计与仿真分离**：RTL 设计（main 源码、Component/协议/总线/流水线架构、Verilog 生成）一律使用 **spinal-de** skill，不在本 skill 内做 RTL 架构设计。

核心纪律：
- **main 保持纯净**：不在 main 写 `simPublic`/`import spinal.core.sim._`；仿真代码一律放 `src/test/scala` 镜像 main 包目录
- **问题定位次序（先归属后排查）**：① 先区分可疑代码是自研（工程 src/main）还是 SpinalHDL 自带 lib；② 对官方 lib 先按黑盒只看输入输出是否符合协议契约，不查内部；③ 重点排查自研代码（典型首刀：lib 边界比对自研送入值 vs 原始输入）；④ 仅当自研全部排除且 lib 输入合契约而输出违约时，才查 lib 内部/读 lib 源码（走源码核实流程）。波形定位场景的完整执行见 spinal-wawk-debug skill
- **已核实语义直接采用**：`spinal-sim-reference.md` §14（线程唤醒/写入时序）、§16（FST 崩溃隔离）、§17（公平性测量）已经源码核实/实践验证，**勿重复解压探索**
- 未收录的仿真 API 语义走下方「依赖源码核实流程」，禁止凭记忆断言

## SimEnv 范式（工程约定，必须遵守）

- **目录镜像**：main `src/main/scala/libext/bus/dataBus/DataBusShift.scala` → test `src/test/scala/libext/bus/dataBus/DataBusShiftSimEnv.scala` + `DataBusShiftTest.scala`，包名与 main 一致
- **SimEnv 继承 DUT**：`case class XxxSimEnv(...) extends Xxx(...)`，位于 test 侧，封装 `init()`/驱动/监视/记分板/参考模型；需观察的内部信号在 **SimEnv 内**调 `.simPublic()`（`Vec[Reg]` 需 `foreach(_.simPublic())`）。**DUT 本身是 case class 时，SimEnv 必须用普通 class**（Scala 2.11 禁止 case-to-case 继承）
- **可见性最小放宽**：DUT 内部成员为 `private` 而 test 需观察时，在 main 侧最小放宽为 `private[<包名>]`（此为唯一允许的 main 改动，属设计侧变更，遵循 spinal-de 风格），由同包 SimEnv 调 simPublic；不加任何仿真逻辑
- **Test 范式**：`class XxxTest extends org.scalatest.FunSuite`；`val dutCompiled = SimConfig.withWave/withFstWave.compile(XxxSimEnv(...))` 用 `lazy val` 复用编译产物，多个 `test("...") { dutCompiled.doSim { dut => ... } }` 组织 testcase
- **SimConfig 必带工程约定三件套**（与 spinal-de 一致）：`SimConfig.withConfig(SpinalConfig(nameWhenByFile = false, genLineComments = true, mergeSyncProcess = false)).withFstWave...`；nameWhenByFile=false 避免 when/switch 条件信号带 `when_<文件>_l<行号>` 命名混入波形；genLineComments=true 使生成 RTL 每条赋值行尾带 `// @ <文件>.scala l<行号>` 注释保留 RTL↔Scala 映射；mergeSyncProcess=false 使每个寄存器独立 always 块便于定位（已源码核实 when.scala:79/153、Statement.scala:322、ComponentEmitter.scala:202，withConfig 见 SimBootstraps.scala:844）
- **命名**：`XxxSimEnv`（环境/驱动/监视/模型）与 `XxxTest`（testcase 组织）分离

## 时序语义速查（§14 已源码核实，SpinalHDL 1.11.0 + Verilator）

| 操作 | 语义 |
|------|------|
| `waitSampling()`/`onSamplings` 唤醒后读信号 | 读到**沿前快照**——正是本时钟沿所采样的值 |
| 线程内 `#=` 写入 | 缓冲写入，**下一个时钟沿**才被 DUT 采样 |
| 同一沿唤醒的多线程读 | 同一份沿前一致快照，**无竞争**（Verilator `isBufferedWrite=false`） |
| 监视握手 | `waitSampling(); if (valid && ready) 捕获 payload` —— 恰好捕获本沿传输 |
| 驱动握手 | `payload #= x; valid #= true; waitSamplingWhere(ready)` 后拉低 valid |
| 逐拍白盒比对 | 同一 wake 读一致快照 → 算期望次态 → **下一 wake** 比对实际寄存器 |
| 复位 | `waitSampling` 受复位门控；`forkStimulus` 默认复位 16 周期，复位后 `waitSampling(n)` 跳过 |

完整推演与源码行号依据见 `spinal-sim-reference.md` §14。

## 常见陷阱

| 陷阱 | 对策 |
|------|------|
| 访问内部信号报 UNACCESSIBLE SIGNAL | SimEnv 内调 `.simPublic()`，并确保信号有名字 |
| 赋值在 `forkStimulus` 之前 | 先 `forkStimulus`（内部给时钟/复位初值）再驱动信号 |
| `doSim` body 结束但 fork 线程未完 | 用 `doSimUntilVoid`（等全部线程） |
| 波形无信号 | `.withWave` + `withWaveDepth(0)` 全深度 |
| 复位期间采样无效 | `waitSampling` 不含复位期；用 `waitRisingEdge` 跳过复位 |
| `simRandom` 与全局 Random 混用 | 仿真内只用 `simRandom`（seed 关联可复现） |
| 仿真挂死无提示 | 开头加 `SimTimeout(周期数)` |
| 同 JVM 多次 doSim + FST 第 3 次起 SIGSEGV | 逐 testcase 独立进程（见下） |
| 全消费后测输出字节份额验证调度比例 | 错误方法——须在满压力稳态窗口测量（§17） |
| 仿真线程内读 `.fire`/`.first` 报 NPE | signalCache 懒信号仿真阶段必崩；读 valid/ready 后 Scala 层算 fire（§14.5，已源码核实） |
| `case class SimEnv extends case class DUT` 编译报错 | SimEnv 改普通 class（§15） |
| `clockDomain.fork` 编译报错 | 用 sim 包级 `fork { }`；clockDomain 只有 forkStimulus 等扩展（§15） |
| `checkEmptiness` 编译报错 | 官方拼写 `checkEmptyness()`，少一个 i（§8，已源码核实） |

## 运行环境要点（§16 已实践验证）

- **sbt 必须 fork**：`build.sbt` 需 `Test / fork := true`（VerilatorBackend 强制）；建议 `Test / javaOptions += "-Xmx2g"`
- **本工程 sbt 启动方式**：未全局安装 sbt，用 IDEA 内置 sbt-launch.jar：`java -Xms512m -Xmx2g -classpath "<IDEA>/plugins/Scala/launcher/sbt-launch.jar" xsbt.boot.Boot Test/compile`（勿加 `-batch`）
- **FST 多仿真崩溃隔离**：Verilator 5.030 下同一 JVM 连续多次 `doSim`（`withFstWave`）第 3 次起原生 SIGSEGV。修复：脚本逐例调用 `testOnly <Suite> -- -z "<完整用例名>"`（每次 sbt 启动即新进程）；用**完整用例名**避免 `-z` 子串误匹配；编译产物 `lazy val`。工程要求 FST 时用逐例隔离而非降级 VCD
- **日志范式**：控制台 + 逐 case 文件双输出、**逐行 flush**；断言失败**先落盘再抛出**（封装 `check(cond, msg)`）；记录 init 配置/每笔握手/账本快照/终检汇总

## 参考文件与加载策略

唯一参考手册：`spinal-sim-reference.md`（自包含，无需加载设计文档）。按需读取对应章节：

| 需求 | 章节 |
|------|------|
| 仿真配置/启动/波形 | §1 |
| 信号读写（`#=`/`toBoolean` 等） | §2 |
| 时钟域 API（forkStimulus/waitSampling 等） | §3 |
| 线程与调度/仿真流程控制 | §4-5 |
| Stream/Flow 驱动监视库（spinal.lib.sim） | §6-7 |
| ScoreboardInOrder / Phase | §8-9 |
| SparseMemory / SimData | §10-11 |
| 完整测试平台示例 | §12 |
| 常见陷阱 | §13 |
| **线程唤醒/写入时序语义（已核实，直接采用）** | §14 |
| **目录组织与 SimEnv 范式** | §15 |
| **运行环境/FST 隔离/日志范式** | §16 |
| **调度公平性/字节配比测量方法学** | §17 |

DUT 的 RTL 行为疑问（协议握手规则、组件内部逻辑）→ 查 **spinal-de** skill 的设计文档；仿真框架 API 疑问 → 本 skill §1-12 或下方源码核实流程。

**仿真失败需波形定位根因时 → 加载 spinal-wawk-debug skill**（wawk 分析 FST/VCD：只看 SpinalHDL 层用户定义信号、过滤 `_zz_*` 生成中间变量、经生成 RTL 行尾注释映射回 Scala 行号、交付 Scala 代码修复建议而非 Verilog）。

## 硬性规则：改动门禁（仿真失败修复场景，必须遵守）

针对“为修复仿真失败/定位问题而做的代码改动”（新建测试平台等非修复性开发不受此门禁约束）：

1. **波形证实先行**：无论改的是仿真代码（test 侧）还是 DE 代码（main RTL），改动前必须先用 wawk 在波形上证实根因（加载 spinal-wawk-debug skill 执行）。wawk 程序必须**实际运行并拿到真实输出**，“预期输出/静态代码推断”不能替代波形证实；程序报错先修到跑通（语法查 spinal-wawk-debug 红线表与 wawk-debug 陷阱表）。无波形证据 → 不改动
2. **DE 改动由用户决策**：根因落在 main RTL（DE 代码）时，代理只交付修改提案（波形证据 + Scala 文件/行号 + 前后片段 + 理由），**不直接修改 main**；由用户决定是否修改、何时修改。仿真代码（test 侧）修复可直接执行，但同样须先满足规则 1 并在改后重跑验证
3. **修改记录必须归档**：每项改动（含被用户否决的 DE 提案）写入归档文件 `doc/debug_archive/<YYYYMMDD>_<模块>_<问题短名>.md`，必含字段：日期/模块/失败现象/波形证据（wawk 程序+真实关键输出+FST 路径+时间戳）/根因归属（自研 vs lib，定位次序结论）/改动类型（DV/DE）/文件+行号+前后片段/**DE 用户决策结果（批准/否决/待定，必填）**/改后验证结果。记录模板见 spinal-wawk-debug skill

**合理化借口对照表**：

| 借口 | 事实 |
|------|------|
| "静态代码/Verilog 已看出根因，波形验证多余" | 门禁要的是波形实证；静态推断会错（信号名/时序/位宽），wawk 跑一遍几分钟 |
| "客户在等，先改了再补证据" | 无证据的改动可能改错地方；证据先行反而最快 |
| "DE 改动很小，直接改省一轮交互" | main 是交付物，改不改由用户决策，与改动大小无关 |
| "wawk 程序报错，用预期输出代替" | 报错程序=没有证据；修到跑通才算证实 |
| "记录口头说过就行" | 无归档=不可追溯；DE 提案无决策字段=责任不清 |

## 依赖源码核实流程（通用，禁止网络）

**触发条件**：`spinal-sim-reference.md` 未收录某仿真 API、或需确认仿真框架内部行为（如调度器唤醒顺序、后端写入缓冲语义）时。§14/§16/§17 已核实内容**不触发**本流程。

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
     ls "$SRC_DIR/lib/spinal/sim" | head              # 验证解压产物存在（仿真源码在 core 的 spinal/core/sim 与 lib 的 spinal/lib/sim）
     ```
   - 执行后记住 `$SRC_DIR` 实际路径，直接进入第 4 步读源码；同一会话内复用该目录，不重复解压
   - **唯一降级条件（可观察谓词）**：逐项核对当前会话工具清单、确认无任何命令执行工具后，向用户**列出工具清单作为证据**并说明能力边界，才允许给出上述命令请用户执行。未列工具清单证据就向用户输出解压/建目录命令 = 违规
   - Read 工具无法直读 jar 的原因：jar 是 ZIP 容器，条目内容为 DEFLATE 压缩二进制，直读只见 `PK` 魔数与乱码（IDEA 能打开是因其内置 jar 虚拟文件系统实时解压）
4. **读明文源码核实**：逐文件读取 `.scala`（仿真重点：`core/spinal/core/sim/package.scala`、`sim/spinal/sim/SimManager.scala`、`SimThread.scala`、`SimVerilator.scala`、`lib/spinal/lib/sim/`），结论引用具体文件与行号
5. **反哺文档**：核实后的仿真 API 事实补入 `spinal-sim-reference.md` 对应章节，标注核实所依据的版本号（设计侧 API 反哺至 spinal-de 的 `spinal-api-reference.md`）

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
| "§14 结论可能过时，再解压核实一遍" | §14 已按同版本源码核实并标注行号，直接采用，重复探索浪费时间 |

**Red Flags**（出现即回到步骤 3 重做）：
- 向用户输出解压/mkdir 命令，却未附工具清单证据
- 用"建议放在某目录"等软措辞替代自建目录动作
- 解压后不验证产物就直接宣称完成

## 覆盖范围声明

**已覆盖**（经源码核对/实践验证）：SpinalSim 框架（SimConfig/后端/时钟域/线程调度）、`spinal.lib.sim`（Stream/Flow 驱动监视、ScoreboardInOrder、Phase、SparseMemory、SimData）、线程唤醒/写入时序语义（1.11.0）、SimEnv 工程范式、Verilator FST 崩溃隔离、日志范式、调度公平性测量方法学。

**未覆盖**（涉及时走「依赖源码核实流程」）：VPI/Icarus/GHDL 后端细节差异（§14.4 仅提示 `isBufferedWrite` 语义差异）、formal 形式化验证、`lib/sim` 长尾工具（手册未收录条目）。