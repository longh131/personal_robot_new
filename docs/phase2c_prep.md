# Phase 2C 准备（未发送运动）

日期：2026-10-15  
状态：已执行并关闭。离地前进/停发/ROS 键盘已验。见 `docs/phase2_close.md`。

## 候选协议（假设，未确认）

选定唯一有发送端证据的候选，**不是已验证固件协议**：

- 帧：`7B 00 00` + vx/vy/wz 有符号 int16 大端 + XOR(此前字节) + `7D`（11 字节）
- 波特率假设：115200（旧驱动 + zip USART1 注释；2B-2 未测 termios）
- 本次规划：`vx=60, vy=0, wz=0` → hex `7b0000003c00000000477d`
- 证据：归档 `serial_protocol.py` / 历史短测用过 vx=60；用户称曾能前进。2B-2 只读无 RX，不支持也不否定该帧。
- 冲突：厂商 zip USART1 丢弃 RX、USART2 的 `7B` 是 APP ASCII。板上固件可能≠ zip。

不确定性：单位、符号、是否需周期重发、固件是否认此帧。不扫波特率、不发探测字节、不试第二种协议。

## 最小测试顺序（尚未批准执行）

1. 单次低速前进（本脚本 `--execute-forward`）。
2. **单独观察停止**：停止发送后看轮是否仍转。零速/反向不当急停；仍转则切断电机电源。
3. 前进与停止经审核后，才规划后退/横移。

## 脚本

路径：`hardware_test/c30d/motor_test/c30d_forward_once.py`

| 命令 | 行为 |
|---|---|
| `python3 .../c30d_forward_once.py` | 默认检查，**不开串口** |
| `python3 ... --print-frame` | 只打印 hex |
| 见下 | 才发送（本阶段禁止运行） |

发送触发（待另批）：

```bash
C30D_ALLOW_EXECUTE=1 python3 /opt/personal_robot/hardware_test/c30d/motor_test/c30d_forward_once.py \
  --execute-forward --confirm-wheels-off --confirm-power-cut-ready
```

缺环境变量或确认旗标则拒绝发送。退出不发零帧、不反向。

## 时限与停止

- 发送窗 0.20 s，周期 0.05 s，最多 4 帧，然后 close。
- **定时结束 = 停止发送 ≠ 电机已停。**
- 仍转：现场立即切断电机驱动电源。
- 无硬件急停。日志：`hardware_test/c30d/logs/forward_once.log`（仅 execute 时写）。
