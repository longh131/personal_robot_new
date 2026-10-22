# C30D 通信协议证据表（Phase 2A）

日期：2026-10-15  
方法：只读核对厂商 zip、归档驱动、现有日志。未打开串口，无抓包文件。

图例：**F** 已证实事实（本仓库/本机可复核） | **C** 源码陈述（仅证明该文件内容） | **H** 推测 | **T** 待验证

## 1. 物理连接（本机）

| ID | 陈述 | 级 | 证据 |
|---|---|---|---|
| F1 | 树莓派看到 USB CDC ACM：`1a86:55d4`，序列 `5C98181506` | F | Phase 1：`/dev/c30d` → `ttyACM0`，by-id 一致 |
| F2 | 用户属 `dialout`，设备组 `dialout` | F | Phase 1 |
| T1 | 该 USB-UART 接到 STM32 的哪一路 USART | T | 无原理图；zip 未描述 CH343 接线 |
| T2 | 链路上实际波特率 | T | 旧代码写 115200；zip USART1 注释 115200。2B-1 未读 termios（会打开设备） |
| F11–F15 | 设备链接、CDC、无占用 | F | `docs/phase2b1_serial_env.md` |

## 2. 旧驱动（归档，禁止运行）

| ID | 陈述 | 级 | 证据 |
|---|---|---|---|
| F3 | 组帧：`7B 00 00 vx_hi vx_lo vy_hi vy_lo wz_hi wz_lo xor 7D`，vx/vy/wz 为有符号 int16 大端；xor 为此前全部字节 BCC | F | `archive/legacy_c30d_driver/c30d_driver/serial_protocol.py` |
| F4 | 离线按该算法：全零=`7b00000000000000007b7d`；vx=60=`7b0000003c00000000477d` | F | 本机纯计算，未下发 |
| F5 | 节点写死 `/dev/ttyACM0`、115200；订 `/cmd_vel`；`Twist` 各分量 ×300 后 `int()` 下发 | F | `c30d_node.py` |
| F6 | 0.5 s 无新命令及进程退出时发送 (0,0,0) | F | 同上 watchdog/`finally` |
| F7 | `single_test.py` 无限 `build_frame(60,0,0)`，无停止条件 | F | 归档脚本。**禁止运行** |
| H1 | 该 11 字节帧即 USB 上固件所解析的运动协议 | H | 仅有发送端代码，无 RX 解析对照、无抓包 |
| H3 | ×300 表示 mm/s 或固件整数单位 | H | 无注释、无固件引用 |

## 3. 厂商 STM32 zip（L150Pro C30D 2025.11.14）

| ID | 陈述 | 级 | 证据 |
|---|---|---|---|
| C1 | `uart1_init(115200)` 注释：可用于与 ROS 通信 | C | `BALANCE/system.c` |
| C2 | **USART1 接收中断读出数据后丢弃，无组帧** | C | `HARDWARE/usartx.c` `USART1_IRQHandler` |
| C3 | USART2 9600：APP 方向键 `0x41–0x48` 等；`0x7B`/`0x7D` 为 PID **ASCII** 参数起止，不是 int16 速度帧 | C | `USART2_IRQHandler` |
| C4 | UART5 460800：雷达帧 `A5 5A`，与运动命令无关 | C | `UART5_IRQHandler`、`usartx.h` |
| C5 | `Check_Sum` / `Receive_Data` / `Send_Data` **整段注释**；`XYZ_Target_Speed_transition` 已定义（mm/s→m/s 注释）但本包 `control.c` 未见调用 | C | `usartx.c` / `usartx.h` |
| C6 | USB 库为 **Host/HID（PS2）**，不是 Device CDC | C | `HARDWARE/USB/USB_HOST` |
| T3 | 板上运行固件是否等于该 zip | T | 无版本/校验对比 |
| T4 | CH343 是否接到 USART1（若是，则该 zip 下 USB 运动命令会被丢弃） | T | 与历史“能走”并存则强烈暗示固件≠该 zip 或走了别的口 |

`MOTOR.zip`：未发现 `0x7B` 速度帧实现（仅外设库/BSP）。不作为本机协议证据。

## 4. 日志与抓包

| ID | 陈述 | 级 | 证据 |
|---|---|---|---|
| F16 | 2B-2 只读打开 `/dev/c30d` 约 5 s 成功，RX 空 | F | `docs/phase2b2_readonly_serial.md`。不据此否定或肯定运动协议 |
| F8 | 仓库内 **没有** 运动相关 pcap/hex 抓包 | F | 2B-2 仅空 RX 记录 |
| F9 | 归档 log 仅为 colcon/egg 构建输出，无 `cmd vx=`、无帧十六进制 | F | `archive/legacy_c30d_driver/log/` |
| H-hist | 前进/后退/左移/右移曾经成功 | H | 用户项目说明；无本次可引用记录 |

## 5. 停车（全部未在本阶段证实）

| ID | 陈述 | 级 |
|---|---|---|
| T5 | 全零帧使电机停止 | T（KI-001） |
| T6 | 反向速度制动不造成反向位移 | T（KI-002） |
| T7 | 停发/关串口/拔 USB 后电机行为 | T |
| F10 | 无已验证硬件急停 | F（KI-003） |

## 6. 2A 结论

不能冻结“C30D USB 运动帧格式”。唯一可冻结的发送端假说是 **H1+F3**，供 2C 在批准后用单帧验证。  
**不得**根据该 zip 宣称 USART1 已实现 ROS 速度解析。  
**不得**把 (0,0,0) 当急停。
