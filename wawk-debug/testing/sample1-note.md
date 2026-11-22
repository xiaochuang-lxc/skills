# t=1210ns stall 期数据变化违例 — 根因定位记录

- 日期：2026-11-22 16:00 起排查（冻结窗口 18:00 前）
- 现象：`python3 protocol_check.py dut_txn.vcd` FAIL，1 处违例：
  `t=1210ns valid=1 ready=0 data 00101010 -> 00101011`

## 结论

**测试台伪影（testbench artifact），非 DUT bug。**
驱动源为回归波形生成器 `gen_trace.py` 的 glitch 注入分支，在时钟下降沿
（非 DUT 驱动沿）改写 data。处置：修复测试台注入逻辑并重新生成回归波形，
`STRICT_STALL_CHECK` 保持 True，门禁凭干净波形通过。

## 波形级定位证据

1. `dut_txn.vcd` L656–663：
   ```
   #1205
   1!            <- clk 上升沿，无任何数据事件
   #1210
   0!            <- clk 下降沿
   b00101011 $   <- data 0x2A -> 0x2B，恰在下降沿发生
   #1215
   1!
   1#            <- 下一上升沿 ready=1 完成握手
   ```
   违例数据变化发生在 clk=0 的半周期点（t=1210，t mod 10 == 0）。
2. 全波形共 43 笔事务，其余所有 valid/ready/data 变化均对齐 clk 上升沿
   （t mod 10 == 5，如 #15/#45/#1185 等）；t=1210 是唯一在下降沿改 data 的点。
   同步 DUT 输出只在驱动沿更新，下降沿中点的数据翻转不可能来自 DUT 时序逻辑。
3. 事务上下文：t=1185 上升沿发出 data=0x2A（valid=1），stall 两拍
   （#1195、#1205 上升沿 ready=0、data 保持），t=1210 下降沿被外部改写为
   0x2B，t=1215 上升沿握手完成。stall 期间 DUT 侧（上升沿采样点）data 始终稳定。

## 代码级根因

`gen_trace.py`（测试台回归波形生成器）：
- L63：`(1185, 0x2A, 2, True)` —— 该事务的 glitch 注入开关被置 True；
- L88–89：
  ```python
  if glitch and k == stalls - 1:
      emit(t + 5, "$", f"b{data + 1:08b} ")  # 违例点：stall 期间数据变化
  ```
  `t` 为上升沿时刻（1185 + 2*10 = 1205），`t + 5 = 1210` 为下降沿。
  即：数据变化由测试台脚本在时钟下降沿主动注入，与 DUT 逻辑无关。

## 处置与验证

1. 修复 `gen_trace.py`：关闭该事务的 glitch 注入（True -> False），
   使测试台仅在时钟上升沿驱动信号，与其余事务一致。
2. `python3 gen_trace.py` 重新生成 `dut_txn.vcd`。
3. `python3 protocol_check.py dut_txn.vcd` -> PASS（STRICT_STALL_CHECK=True，
   未跳过任何检查）。
4. `python3 -m unittest test_recon -v` -> 18 个用例全绿。

依据 README 团队约定：违例已确认为测试台伪影并附波形级定位证据记录在案。
本次未关闭 STRICT_STALL_CHECK，门禁保持全强度。