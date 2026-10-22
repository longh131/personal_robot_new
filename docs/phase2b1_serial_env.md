# Phase 2B-1 只读通信环境核查

日期：2026-10-15  
方法：`ls`、`udevadm info`、`sysfs` 描述符、`/proc/*/fd` 符号链接扫描。  
**未**对 `/dev/c30d` 或 `/dev/ttyACM0` 执行 open/read/write，未运行 `stty`/`cat`/`python serial`。

图例：**F** 事实 | **H** 推测 | **T** 未知

## 1. 设备与权限

| ID | 陈述 | 级 |
|---|---|---|
| F11 | `/dev/c30d` → `ttyACM0`；by-id `usb-1a86_USB_Single_Serial_5C98181506-if00` 同指向 | F |
| F12 | 节点 `crw-rw---- root dialout`；`andylong` ∈ `dialout` | F |
| F13 | USB `1a86:55d4` QinHeng，产品 `USB Single Serial`，序列 `5C98181506`，`bcdDevice=0444`，驱动 `cdc_acm`，接口 `:020201:0a0000:`（CDC） | F |
| F14 | udev 规则已装：vendor/product/serial 匹配才创建 `c30d` | F |
| F15 | 核查时无进程 fd 指向 `/dev/ttyACM0` 或 `/dev/c30d` | F |
| T2 | 内核当前 termios/波特率 | T | 读取需打开设备，本阶段未做 |
| T8 | 打开后 DTR/RTS 是否复位 STM32 | T | 未打开 |

## 2. USB 与 USART（源码 + 本机，无新抓包）

| 关系 | 级 | 说明 |
|---|---|---|
| Pi CDC ACM ↔ CH343 芯片 | F | VID/PID/驱动 |
| CH343 TX/RX ↔ STM32 某路 USART | T | 无原理图 |
| 若接 USART1 @115200 | H | zip 注释“可与 ROS 通信”；但 **USART1 ISR 丢弃 RX（C2）** |
| 若接 USART2 @9600 | H | 则 `0x7B` 走 APP PID/方向键，乱码有运动风险 |
| 若接 UART5 @460800 | H | 雷达 `A5 5A`，与遗留 11 字节帧冲突更大 |
| 板上固件 = 该 zip | T | 历史“能走”与 C2 冲突，倾向固件不同或接线不是 USART1 丢弃路径 |

波特率证据仅有：**旧驱动 115200（F5）**、**zip USART1 注释 115200（C1）**。链路实测未知（T2）。

协议冲突不变：遗留二进制 `7B…7D` 速度帧 vs USART2 ASCII `7B/7D` vs 已注释 ROS Check_Sum vs USART1 丢弃。

## 3. 下一阶段开门条件

### 3.1 若仅打开串口只读（建议称 2B-2，须另批）

必须同时满足：

1. 用户书面批准「打开 `/dev/c30d` 只读，禁止 write」。
2. `/dev/c30d` 仍在且无占用进程。
3. 轮子离地或顶起并确认可自由转。
4. 身旁可立即断电/拔 USB（无硬件急停）。
5. 脚本：`O_RDONLY` 或不调用 write；固定时长（建议 ≤5 s）；异常即 close；记录 RX hex。
6. 不运行归档驱动 / `single_test.py`。
7. 打开失败或出现异常数据则停止，不改波特率扫描、不发探测字节。

打开串口本身可能改变线状态（T8），即使只读也不是零风险。

### 3.2 若发送运动命令（2C/2D）

**必须再次单独申请批准。** 2B-2 通过不构成运动许可。  
另需：2B-2 或等价只读已完成或你明确豁免；单帧、时间盒、禁止循环；零速/反向不得当急停。
