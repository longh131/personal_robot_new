# V1 模块说明（实装）

- 日期：2026-11-19  
- 根路径：`/opt/personal_robot/`

## 1. 顶层目录

| 路径 | 作用 |
|---|---|
| `src/` | 个人助手与 REMOTE（Python） |
| `ros2_ws/src/` | ROS 2 包源码 |
| `config/` | 配置（密钥类不进 git） |
| `data/` | 媒体、记忆、唤醒模型 |
| `logs/` | 运行日志（`start.sh` / 障碍缓存等）；**不要与已删除的旧目录 `log/` 混淆** |
| `scripts/` | `start.sh`、`rpicam.sh`、改密等 |
| `docs/` | 工程文档 |
| `doc/` | 厂商/旧项目只读资料 |
| `hardware_test/` | 硬件探测脚本 |
| `tools/` | frpc、**rpi_camera**（正式路径）、UPS 厂商脚本等 |
| `firmware/` | C30D 相关固件资料 |
| `.venv/` | Python 虚拟环境 |
| `requirements.txt` / `setup.sh` | pip 与系统依赖入口 |

### 已清理（2026-11-19）

| 已删除 | 原用途 | 替代 |
|---|---|---|
| `log/` | 早期 colcon version-check 残留 | ROS：`ros2_ws/log/`；业务：`logs/` |
| `opt/` | 指向 `tools/rpi_camera` 的旧符号链接 | `tools/rpi_camera` + `scripts/rpicam.sh` |
| `.lgd-nfy0` | lgpio 运行时 FIFO 残留 | 无 |

仍保留、非 bringup 必需：`hardware_test/`、`tools/UPS_HAT_E/`（参考）、`ros2_ws/src/ws_smoke`（冒烟包）。

## 2. Python：`src/`

### 2.1 `main.py`

进程入口：状态机、REMOTE HTTP、AWAKE socket/麦克风、sentry 钩子；AWAKE 进出时同步 ROS `mode_cmd`。

### 2.2 `runtime/`

- `machine.py` / `events.py` / `idle.py`：模式与事件循环。  
- 测试：`test_machine.py`。

### 2.3 `remote/` — REMOTE 界面

| 文件/目录 | 功能 | 状态 |
|---|---|---|
| `http_server.py` | `127.0.0.1:5000` 登录、API、静态页、favicon | 已完成 |
| `static/` | 遥控 UI、媒体页、PR 图标 | 已完成 |
| `ros_bridge.py` / `skill_pub.py` | 技能与模式（不写串口） | 已完成 |
| `camera.py` / `media.py` | 预览、拍照录像录音 | 已完成（依赖相机可用） |
| `rtc.py` | WebRTC 对讲 | 已完成 |
| `gimbal.py` / `hw_pwm.py` | 云台 | 已完成 |
| `media_library.py` | 媒体浏览删除 | 已完成 |
| `auth.py` | 登录哈希 | 已完成 |

专题：`remote.md`、`remote_cloud.md`。

### 2.4 `awake/` — AWAKE 语音助手

| 能力 | 模块 | 状态 |
|---|---|---|
| 唤醒 KWS | `mic.py` / `keywords.py`（Sherpa） | 已完成 |
| 对话循环 | `talk.py` | 已完成 |
| 意图词表 | `intent.py` | 已完成（含软匹配） |
| 履约 | `actions.py` | 已完成 |
| 云 ASR/TTS/LLM | `cloud.py` | 已完成 |
| 天气新闻搜索 | `search.py` | 已完成 |
| 持续行走/快慢 | `halt.py` + `skill_pub.py` | 已完成 |
| 倒计时/提醒 | `scheduler.py` | 已完成 |
| 记忆 | `memory.py` → `data/memory/facts.sqlite` | 已完成 |
| 拍照/音乐/音量 | `photo.py` / `music.py` / `volume.py` | 已完成 |
| 自检 | `status.py` | 已完成 |
| 本地工具 | `tools.py`（时间日期电量） | 已完成 |

专题：`awake.md`、`memory.md`。

### 2.5 `indicators/`

LED / 蜂鸣器线索（唤醒拒绝、低电、定时提示音等）。

### 2.6 `sentry/`

IDLE 运动检测录制；**默认关闭**（`robot.yaml` `sentry.enabled: false`）。见 `sentry.md`。

### 2.7 `settings.py`

统一读取 `identity.json` / `robot.yaml`。

## 3. ROS 2：`ros2_ws/src/`

| 包 | 可执行/作用 | 状态 |
|---|---|---|
| `safety_manager` | 模式、急停、超时、近障裁速；`safety.launch.py` | 已完成 |
| `c30d_driver` | 串口驱动、限速、odom/TF；订 `/cmd_vel_safe` | 已完成 |
| `command_bus` | 技能校验；REMOTE/AWAKE 分话题发 Twist | 已完成 |
| `lidar_pkg` | 发布 `/scan` | 已完成 |
| `lidar_assist` | `follow_node` → `/cmd_vel_awake`；默认不使能 | **节点有，产品跟随未开** |
| `ws_smoke` | 工作空间冒烟包 | 工具性 |

注意：工作区内若仍有实验脚本，**禁止**运行无停止条件运动测试（见 KI-005）。

## 4. 脚本与工具

| 项 | 说明 |
|---|---|
| `scripts/start.sh` | 一键：frpc + ROS launch + `main.py` |
| `scripts/rpicam.sh` | 使用 `tools/rpi_camera` 的 PiSP/rpicam，不覆盖系统 libcamera |
| `scripts/set_remote_password.py` | 设置网页密码 |
| `setup.sh` | 系统包/udev（需 sudo，先说明再执行） |

## 5. 模块边界（防回归）

- `awake` **不得** `import remote`（声卡/串口抢占与架构约束）。  
- REMOTE 与 AWAKE 运动都只发 **skill**，由 Bus+Safety 落地。  
- `follow_node` **关闭时不得**向 `/cmd_vel_awake` 刷零速（会冲掉语音驱动）。
