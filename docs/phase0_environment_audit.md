# Phase 0 环境审计报告

- 审计日期：2026-10-15
- 主机：`andylong-desktop`
- 项目根：`/opt/personal_robot/`
- 范围：只读检查。未安装软件、未改系统配置、未打开电机、未发送运动命令。

## 1. 操作系统与硬件

| 项 | 实测 |
|---|---|
| 发行版 | Ubuntu 24.04.4 LTS（noble） |
| 内核 | `6.8.0-1065-raspi` |
| 架构 | aarch64 / `arm64`（`dpkg --print-architecture`） |
| CPU | ARM Cortex-A76 × 4，最高 2400 MHz |
| 内存 | 3.9Gi 物理；审计时约 1.0Gi used / 2.9Gi available |
| Swap | `/swapfile` 2.0Gi，当时未使用 |
| 磁盘 | `/dev/mmcblk0p2` ext4，57G，已用约 13G（24%），可用约 42G |
| 节流状态 | 无 `/dev/vcio`，无法运行 `vcgencmd get_throttled` |

结论：与 ROS 2 Jazzy 官方 Ubuntu 24.04 目标匹配。4GB RAM 对后期「桌面 ROS + 视频 + 本机大模型」偏紧，需限制 onboard 推理与机上 RViz。

## 2. 用户与权限

| 项 | 实测 |
|---|---|
| 用户 | `andylong`（uid 1000） |
| 组 | `andylong,adm,dialout,cdrom,sudo,dip,plugdev,users,lpadmin,sambashare` |
| 串口组 | 已在 `dialout` |
| 视频/音频组 | **不在** `video`（gid 44）、`audio`（gid 29） |
| sudo | 交互式 sudo 可用；无密码的 `sudo -n` 失败 |

结论：C30D USB 串口权限已具备。摄像头/声卡节点在加入对应组并重新登录前可能出现权限失败。任何 apt、udev、组变更都需要现场输入 sudo 密码。

## 3. 开发工具

| 工具 | 状态 |
|---|---|
| Python | `/usr/bin/python3`，3.12.3 |
| `python3-serial` | 已安装 3.5-2；`import serial` 成功 |
| `python3-opencv` | 已安装 4.6.0 |
| `python3-pip` | **未安装** |
| `python3-venv` | **未安装** |
| Git | 2.43.0 |
| 项目 Git | `/opt/personal_robot` **不是 git 仓库** |
| Docker | **未安装** |
| unzip | 已安装 |
| p7zip | **未安装**（无法列出 `doc/pi_robot.1.2.6.7z` 内容） |
| build-essential / cmake / pytest | 已安装 |

## 4. ROS 2 与构建系统

| 项 | 实测 |
|---|---|
| 发行版 | Jazzy，路径 `/opt/ros/jazzy` |
| 环境 | `ROS_DISTRO=jazzy`；`~/.bashrc` 含 `source /opt/ros/jazzy/setup.bash` |
| CLI | `/opt/ros/jazzy/bin/ros2` 可运行 |
| 元包 | `ros-jazzy-desktop` 0.11.0（含 ros-base / ros-core） |
| colcon | `/usr/bin/colcon`，`python3-colcon-common-extensions` |
| rosdep | 0.27.0 |
| RMW | `RMW_IMPLEMENTATION` 未设置；已装 Fast DDS（`rmw-fastrtps-cpp`） |
| CycloneDDS | 未安装 |
| Apt 源 | `/etc/apt/sources.list.d/ros2.list`：`http://packages.ros.org/ros2/ubuntu noble main`，arch=arm64 |

已确认存在：tf2、robot_state_publisher、teleop_twist_keyboard/joy、cv_bridge、image_transport、rviz2、rqt 套件。

未安装（按阶段延后）：Nav2、twist-mux、xacro、joint-state-publisher、usb-cam / v4l2-camera。

结论：Phase 1 不是从零安装 Jazzy，而是验证已有安装、清理工作空间、补开发依赖。

## 5. 串口与 USB 设备

当前 C30D 相关串口（审计时刻）：

- 字符设备：`/dev/ttyACM0`，`crw-rw---- root dialout`
- 稳定路径：`/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C98181506-if00` → `ttyACM0`
- USB：Bus 002 Device 002，`ID 1a86:55d4` QinHeng Electronics USB Single Serial（CH343 类）
- 无 `/dev/ttyUSB*`
- `/etc/udev/rules.d/` 无项目自定义 C30D 规则（仅有 snap 规则）

驱动与测试代码不得写死 `/dev/ttyACM0`。应使用 by-id 路径，或 Phase 1 增加 udev 软链接（提案名：`/dev/c30d`）。

## 6. 摄像头与音频（仅存在性，未做功能测试）

- USB 相机：`Yundea Technology Yundea 1076`（`4759:3931`），序列号 `415035333633350F`
- 另有 CSI 相关节点：`/dev/video0` 的 `ID_V4L_PRODUCT=rp1-cfe`，以及大量 `/dev/video*`
- `aplay -l` / `arecord -l` 未列出声卡

Phase 7/8 前必须复测设备和组权限。本次未打开相机、未录音。

## 7. 项目目录实际内容

`/opt/personal_robot/` 当前仅有：

- `doc/`：厂商资料与旧项目（见下）
- `ros2_ws/`：已有 colcon 工作空间与遗留 `c30d_driver`

`doc/` 文件：

- `README.md`：旧项目「小派 Pi-Robot」说明（Python Brain + 插件，非 ROS2）
- `pi_robot.1.2.6.7z`：旧代码包
- `L150Pro_C30D(2.0)_小车STM32源码_霍尔编码器_2025.11.14.zip`
- `MOTOR.zip`
- `树莓派5B_聊天机器人开发方案.docx`

`ros2_ws/` 问题：

- 源码包：`src/c30d_driver/`
- 工作空间级 `build/`、`install/`、`log/`（colcon 生成，不应当源码维护）
- **源码树内嵌套** `src/c30d_driver/{build,install,log}`，属于错误构建方式

目标树中的 `hardware_test/`、`personal_ai/`、`remote/`、`config/`、`data/`、`logs/`、`scripts/`、`docs/` 在审计时均不存在（本文件写入后才有 `docs/`）。

## 8. 遗留 `c30d_driver` 可行性

检查对象：

- `ros2_ws/src/c30d_driver/c30d_driver/serial_protocol.py`
- `ros2_ws/src/c30d_driver/c30d_driver/c30d_node.py`
- `ros2_ws/src/c30d_driver/c30d_driver/single_test.py`
- 对照厂商 `HARDWARE/usartx.c`（zip 内只读）

**结论：不能作为正式驱动复用。** 批准 Phase 1 后整包移入 `archive/legacy_c30d_driver/`（含误放在 src 下的 build/install/log）。

原因：

1. 组帧假说为 `0x7B + 0x00 0x00 + vx/vy/wz int16 大端 + XOR + 0x7D`。仅可作 Phase 2 对照，不能当作已验证协议。
2. 厂商源码 USART2 将 `0x7B`/`0x7D` 用于 APP PID **ASCII** 参数帧；`Receive_Data`/`Check_Sum` 已被注释。板上固件可能与 zip 不一致，必须重新抓包。
3. 节点硬编码 `/dev/ttyACM0`，直接订阅 `/cmd_vel`，watchdog 发送零速度。与「零速未必停车、反向制动可能倒车」冲突，且绕过 Safety Layer。
4. `single_test.py` 无限发送 `vx=60`，无停止条件。**禁止运行。**
5. 项目规范禁止把未经验证实验代码升格为正式驱动。

## 9. 可能影响后续安装的系统配置

- ROS 2 官方 apt 源已配置，后续 `apt install ros-jazzy-*` 会走该源。
- Jazzy Desktop 已占用磁盘与内存；机上同时开 RViz、摄像头、AI 需资源预算。
- Locale 为 `C.UTF-8`。ROS 一般可用；中文 TTS/日志建议后续评估 `en_US.UTF-8` 或 `zh_CN.UTF-8`。
- 未发现独立硬件急停输入设备。
- 无 Docker；Phase 1 按已选方案不安装。

## 10. Phase 1 依赖清单（需单独批准，此处不执行）

拟安装/变更：

- apt：`python3-pip`、`python3-venv`、`p7zip-full`
- 组：`andylong` 加入 `video`、`audio`（需重新登录）
- udev：按 USB by-id 创建 `/dev/c30d`（插拔验证，不发运动命令）
- 工作空间：归档遗留驱动；`.gitignore` 忽略 `ros2_ws/{build,install,log}`

明确不装：Docker、Nav2、CycloneDDS、usb-cam。

回退：卸载上述 apt 包、删除 udev 规则、从组中移除用户。不改动 `/opt/ros/jazzy` 本体。
