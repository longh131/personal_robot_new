# 已知问题与风险

- 更新日期：2026-11-19（保留历史条目；V1 总览见 `docs/README.md` / `v1_*.md`）
- 说明：下列编号持续有效。新问题追加编号，勿复用已关闭语义。

## 安全（高）

### KI-001 零速度命令未必等于停车

历史测试：发送零速度不一定立即停电机。遗留 `c30d_node.py` watchdog 与退出路径均发送 `(0,0,0)`。

状态：旧 Mec 固件上零帧停不了。`firmware/c30d_servo` 离地：松手停发后约 0.5–1s 滑行停下（含键盘松手检测延迟）。**仍不得把零速当急停。**

### KI-002 反向速度制动可能造成反向运动

历史测试：用反向速度试图刹车可能导致倒车。

状态：未复测。Phase 2 必须记录该策略是否禁止。

### KI-003 无已验证的独立硬件急停

审计未见独立于树莓派的急停回路或驱动使能切断。

软件急停上限：串口仍可写入且固件承认停发/零帧。离地与着地短测（约 15cm）已见停下。断线、杀进程、拔 USB：**未测**。`/odom` 着地位移仍为 0。

**不得宣称具备工业级急停能力。**

### KI-004 控制权切换与话题残留

多节点同时向 `/cmd_vel` 发速度会抢控制。切换 AWAKE/REMOTE 时，旧 Twist 可能因队列继续生效。

要求：底盘只订一条 Safety 放行话题；切换先 revoke 再 grant。

### KI-005 危险遗留脚本

`ros2_ws/src/c30d_driver/c30d_driver/single_test.py` 无限发送 `vx=60`，无停止条件。

**禁止运行。** Phase 1 随包归档后仍禁止执行。

## 协议（高）

### KI-006 协议三套说法不一致

1. 遗留 Python：二进制 `0x7B` 速度帧 + XOR + `0x7D`。
2. 厂商 STM32 zip：USART2 将 `0x7B`/`0x7D` 用于 APP PID ASCII 参数；ROS `Check_Sum` 已注释。
3. 现场：前进/后退/平移曾被验证，但未留下本次可引用的抓包记录。

错误帧存在被固件当成方向键或 PID 参数的风险（USART2 APP 协议）。Phase 2C 前禁止随机扫字节。详见 `docs/c30d_protocol_evidence.md`。L150 原包 USART1 丢弃 RX。个人机器人固件已在 `firmware/c30d_servo` 接上解析；须重新编译烧录后才能对照。

### KI-007 串口设备名会变

当前为 `/dev/ttyACM0`，稳定名为  
`/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C98181506-if00`。

写死 `ttyACM0` 会在设备增减后打错口。

## 环境（中）

### KI-008 4GB 内存

Jazzy Desktop + 视频 + 本机 LLM 可能导致 OOM。后期推理优先远端大模型或量化小模型；避免在机器人上常驻 RViz。

### KI-009 用户不在 video / audio 组

已加入 `video`/`audio`。Y1076 播放/录音已通。标题过时，保留编号。

### KI-010 无 git 仓库

无法用版本回滚。建议 Phase 1 初始化（需另批，不自动 push）。

### KI-011 pip / venv / p7zip 缺失

无法用标准 venv 做隔离测试，也无法列出旧 7z 包文件。列入 Phase 1。

### KI-012 工作空间污染

`src/c30d_driver/{build,install,log}` 与 `ros2_ws/{build,install,log}` 并存。colcon 不应在源码树内生成安装前缀。

### KI-013 无法读取 Pi 节流状态

缺少 `/dev/vcio`，不能用 `vcgencmd` 确认欠压/限频。过热或电源不足可能表现为“随机运动异常”，排查时需注意。

### KI-014 sudo 非免密

自动化安装不能在无用户确认时完成。符合项目“先说明影响再批准”的要求。

## 产品范围（记录）

### KI-016 云台 USB-A 5V 带不动双轴同时转

MG90S 曾由 UPS USB-A 供电；现多已独立 5V。两轴同时转仍可能欠压。当前驱动单轴运动；`gpiozero`+`lgpio`，水平 BCM24、俯仰 BCM19。

### KI-017 计划更换：云台舵机 + CSI 摄像头

- 日期：2026-11-17。用户确认现舵机已可用，**计划换更好舵机**；现 OV5647 CSI **计划换更好摄像头**（曾出现 I2C `-121` 探头失败）。
- 候选舵机（名称）：DS3225、Feetech STS3215、WaveShare ST3215、Dynamixel XL430-W250。
- 候选摄像头（名称）：Raspberry Pi Camera Module 3、Camera Module 3 Wide、Arducam IMX519、Raspberry Pi HQ Camera。
- 更换后须重测：云台引脚/供电、CSI/`rpicam`、REMOTE 预览与 AWAKE 拍照。
- 2026-11-19 现场：`dtoverlay=ov5647` 下内核再次 `ov5647 … error -121`，`i2cdetect -y 11` 全空，`rpicam` 报 No cameras——与「时好时坏」一致，偏排线/座子/供电接触，而非仅软件缺失。

### KI-015 旧 Pi-Robot 架构不兼容

旧项目电机插件可直控硬件。新架构禁止该路径。可参考状态互斥与语音流程，不可拷贝实现。

## 跟踪

| ID | 计划关闭阶段 | 关闭条件 |
|---|---|---|
| KI-001 | 2 | 实测零速停车时间或证明无效 |
| KI-002 | 2 | 实测或明确禁止反向制动 |
| KI-003 | 长期 | 仅当增加并验证硬件急停 |
| KI-004 | 4 | 模式测试通过 |
| KI-005 | 1 | 已归档；重启后无遗留进程；仍禁止运行 `single_test.py` |
| KI-006 | 2 | 协议文档与抓包一致 |
| KI-007 | 1 | `/dev/c30d` → `ttyACM0` 已验证 |
| KI-008 | 10 | 资源预算写入运行手册 |
| KI-009 | 1 / 8 | `video`/`audio` 已加入；Y1076 播放/录音通断已过（`docs/audio_probe.md`）。对讲另批 |
| KI-010 | 1 | 用户要求暂不 git init |
| KI-011 | 1 | pip/venv/p7zip 已装 |
| KI-012 | 1 | `ros2_ws/src` 已无该包；工作空间级 build/install/log 已删除。归档副本仍含其内部 build/install/log |
| KI-013 | 运维 | 可选修复 vcio 或改用其他遥测 |
| KI-014 | 保持 | 不改为免密 |
| KI-015 | 保持 | 架构约束 |
| KI-016 | 保持 | 单轴互斥；独立供电仍可能欠压 |
| KI-017 | 采购后 | 换件并复测云台/相机 |
