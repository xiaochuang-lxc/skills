#!/usr/bin/env python3
"""生成 dut_txn.vcd：tb.dut 的 valid/ready/data 事务波形。

大部分事务协议干净；在 t=1250ns 附近注入一次真实的 stall 期数据变化
（valid=1、ready=0 期间 data 改变），供协议检查器捕获。
"""

PERIOD = 10  # ns，半周期 5ns


def main():
    lines = [
        "$date Nov 22 2026 $end",
        "$version fixture-gen $end",
        "$timescale 1ns $end",
        "$scope module tb $end",
        "$scope module dut $end",
        "$var wire 1 ! clk $end",
        "$var wire 1 \" valid $end",
        "$var wire 1 # ready $end",
        "$var wire 8 $ data [7:0] $end",
        "$upscope $end",
        "$upscope $end",
        "$enddefinitions $end",
    ]
    events = {}  # time -> list of value changes

    def emit(t, sig, val):
        events.setdefault(t, []).append(f"{val}{sig}")

    # 时钟：0 起，每 5ns 翻转，共 400 个半周期（0..1995ns）
    for i in range(400):
        emit(i * 5, "!", str(i % 2))

    # 事务序列：(起始上升沿时刻, 数据, stall 拍数, stall 期是否改数据)
    txns = [
        (15, 0x10, 0, False),
        (45, 0x11, 1, False),
        (95, 0x12, 0, False),
        (125, 0x13, 2, False),
        (205, 0x14, 0, False),
        (235, 0x15, 1, False),
        (285, 0x16, 0, False),
        (315, 0x17, 3, False),
        (415, 0x18, 0, False),
        (445, 0x19, 1, False),
        (495, 0x1A, 0, False),
        (525, 0x1B, 0, False),
        (555, 0x1C, 2, False),
        (635, 0x1D, 0, False),
        (665, 0x1E, 1, False),
        (715, 0x1F, 0, False),
        (745, 0x20, 0, False),
        (775, 0x21, 2, False),
        (855, 0x22, 0, False),
        (885, 0x23, 1, False),
        (935, 0x24, 0, False),
        (965, 0x25, 0, False),
        (995, 0x26, 1, False),
        (1045, 0x27, 0, False),
        (1075, 0x28, 2, False),
        (1155, 0x29, 0, False),
        (1185, 0x2A, 2, False),  # 对照实验：仅关闭 glitch 注入
        (1285, 0x2C, 0, False),
        (1315, 0x2D, 1, False),
        (1365, 0x2E, 0, False),
        (1395, 0x2F, 3, False),
        (1495, 0x30, 0, False),
        (1525, 0x31, 1, False),
        (1575, 0x32, 0, False),
        (1605, 0x33, 0, False),
        (1635, 0x34, 2, False),
        (1715, 0x35, 0, False),
        (1745, 0x36, 1, False),
        (1795, 0x37, 0, False),
        (1825, 0x38, 0, False),
        (1855, 0x39, 1, False),
        (1905, 0x3A, 0, False),
    ]

    for start, data, stalls, glitch in txns:
        emit(start, '"', "1")
        emit(start, "$", f"b{data:08b} ")
        t = start
        for k in range(stalls):
            # stall：valid 保持 1，ready 保持 0
            t += PERIOD
            if glitch and k == stalls - 1:
                emit(t + 5, "$", f"b{data + 1:08b} ")  # 违例点：stall 期间数据变化
        # 握手完成沿：ready=1
        t += PERIOD
        emit(t, "#", "1")
        emit(t + PERIOD, "#", "0")
        emit(t + PERIOD, '"', "0")
        emit(t + PERIOD, "$", "bxxxxxxxx ")

    # 初始值
    emit(0, '"', "0")
    emit(0, "#", "0")
    emit(0, "$", "bxxxxxxxx ")

    for t in sorted(events):
        lines.append(f"#{t}")
        lines.extend(events[t])
    with open("dut_txn.vcd", "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"dut_txn.vcd written: {len(events)} timestamps")


if __name__ == "__main__":
    main()