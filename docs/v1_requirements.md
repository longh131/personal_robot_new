# V1 需求与范围

- 日期：2026-11-19  
- 依据：`AGENTS.md`、当前源码与配置；用户确认「第一版本完成」时的能力边界。

## 1. 产品目标（长期）

基于 **Raspberry Pi 5（4GB，ARM64）+ Ubuntu 24.04** 的个人 AI 移动机器人，具备类似个人助手的交互与任务能力。长期清单见 `AGENTS.md` §2（底盘、ROS 2、远程、音视频、语音 AI、记忆与 Agent、导航扩展等）。

## 2. V1 已纳入需求（应对齐实装）

| 编号 | 需求 | V1 状态 |
|---|---|---|
| R1 | C30D 麦克纳姆轮底盘经 ROS 2 限速控制 | **已完成**（Safety → `/cmd_vel_safe` → `c30d_driver`） |
| R2 | 模式互斥 IDLE / AWAKE / REMOTE / FAULT + 软件急停锁存 | **已完成**（无工业级硬件急停） |
| R3 | Command Bus 校验运动技能（来源、模式、限速、超时） | **已完成**（`drive` 等；`dance_*` 仅排队未履约） |
| R4 | 网页 REMOTE：登录、心跳、遥控、预览/拍照/录像/录音、云台、媒体库、软件急停 | **已完成**（能力边界见 `remote.md`） |
| R5 | 摄像头预览与拍照（CSI + 项目内 rpicam/PiSP） | **部分完成**：链路已接；模组曾 I2C `-121` 时好时坏（见 KI-017） |
| R6 | 双向语音通话（浏览器 ↔ 机身麦/喇叭，非 ASR） | **已完成**（WebRTC；经 FRP 可能降级 JPEG） |
| R7 | 语音唤醒 → AWAKE：ASR/TTS/闲聊、关键词指令、天气新闻、记忆、行走等 | **已完成**（云端 DashScope/DeepSeek；非完整 Personal AI Core） |
| R8 | 激光雷达只读扫描 + Safety 四向近障刹速 | **已完成**（跟随节点默认关） |
| R9 | 编码器里程计与 TF | **已完成**（着地短测有记录；不宣称导航级精度） |
| R10 | 内网穿透 frpc 暴露网页 | **已完成**（配置不进 git） |

## 3. 明确不在 V1 / 未完成

| 编号 | 内容 | 说明 |
|---|---|---|
| U1 | 工业级硬件急停 | **未具备**；仅有软件急停锁存 |
| U2 | 视觉「认出主人并跟随」 | **未做**；备案：脸/登记开锁 + 背后 ReID + 雷达刹停；倾向采购 Camera Module 3 Wide 后再开发 |
| U3 | 雷达距离跟随产品化 | 节点存在，**默认关闭**；非视觉跟人 |
| U4 | Nav2 建图定位自主巡航 | **未做**（原 Phase 11） |
| U5 | 完整 Personal AI Core（知识库、多工具 Agent、调度编排） | **未做**；现有身份 + SQLite 事实记忆 + LLM 闲聊 + 本地/云工具 |
| U6 | `dance_1` / `dance_2` 履约 | Bus 可排队，**无执行器** |
| U7 | IDLE 看守 sentry | 代码在，`robot.yaml` 中 **`sentry.enabled: false`** |
| U8 | 机械臂 / 3D 打印等插件 | **未做** |

## 4. 安全与工程硬约束（需求级）

1. **AI 与 REMOTE 不得打开电机串口**；运动必须经 Command Bus → Safety → `/cmd_vel_safe` → `c30d_driver`。  
2. **REMOTE 与 AWAKE 不得同时拥有运动权**；切换须先 IDLE（Safety：`must_via_idle`）。  
3. **零速度 ≠ 工业急停**；不得宣称工业级急停。  
4. 串口名会变，正式路径用 **`/dev/c30d`**（udev），禁止写死假定永远是 `/dev/ttyACM0`。  
5. Agent/脚本**不得擅自发速度或转舵机**做验收；实机运动须用户批准。  
6. 禁止运行无停止条件的运动脚本（含遗留 `single_test.py`）。

## 5. 硬件基线（现场）

| 项 | 实际配置（以现场为准） |
|---|---|
| 主控 | Raspberry Pi 5，4GB，Ubuntu 24.04 noble |
| 底盘 | Wheeltec C30D，STM32F407，麦克纳姆；USB `1a86:55d4` → `/dev/c30d`，115200 |
| 雷达 | USB STC 转接（udev → `/dev/lidar`）；`lidar_pkg` |
| 相机 | CSI OV5647（Camera v1 类）；项目内 `tools/rpi_camera` + `scripts/rpicam.sh`；**稳定性见 KI-017** |
| 音频 | Yundea 1076 USB 声卡（`plughw:Y1076,0`），非摄像头 |
| 云台 | MG90S；水平 BCM24、俯仰 BCM19；gpiozero+lgpio |
| UPS | I2C 电量只读（`robot.yaml` `ups`） |
| 指示 | LED / 蜂鸣器（GPIO，见 indicators） |

## 6. 相关文档

- 架构实装：`v1_architecture.md`  
- 进度清单：`v1_progress.md`  
- 风险编号：`known_issues.md`
