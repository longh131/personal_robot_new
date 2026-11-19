# V1 系统架构（实装）

- 日期：2026-11-19  
- 说明：描述**当前代码真实路径**。Phase 0 的 `architecture.md` 为早期设计稿，其中部分包名（如独立 `robot_control`）与现网不完全一致。

## 1. 分层（实装）

```
Remote (src/remote)          网页、WebRTC、云台、媒体、REMOTE 登录
Awake / 语音助手 (src/awake) 唤醒、ASR/TTS、指令、记忆、语音行走
Runtime (src/runtime)        IDLE/AWAKE/REMOTE/FAULT 状态机（Python）
Command Bus (ROS)            /robot/skill_cmd → 限速 Twist
Safety (ROS)                 模式许可、超时、软件急停、近障裁速 → /cmd_vel_safe
C30D Driver (ROS)            订 /cmd_vel_safe，串口 /dev/c30d
Lidar (ROS)                  /scan；可选 follow→/cmd_vel_awake（默认关）
Indicators / Sentry          LED蜂鸣；IDLE 看守（默认关）
Config / Data / Logs         配置、媒体、模型、日志分离
```

## 2. 运动控制链（唯一合法路径）

```text
REMOTE 网页 ──skill_pub(source=remote)──► /robot/skill_cmd
AWAKE 语音 ──skill_pub(source=awake)───► /robot/skill_cmd
                                              │
                                              ▼
                                         command_bus
                              REMOTE → /cmd_vel_remote
                              AWAKE  → /cmd_vel_awake
                              （另一路发零速，避免串台）
                                              │
                                              ▼
                                         safety_manager
                         校验 mode/permit/estop/超时/雷达近障
                                              │
                                              ▼
                                        /cmd_vel_safe
                                              │
                                              ▼
                                          c30d_driver ──USB──► C30D
```

硬规则：

- 上层**不得**直写串口或绕过 Safety。  
- Safety 是**唯一**向底盘放行速度的出口（`/cmd_vel_safe`）。  
- AWAKE→REMOTE 必须先 **IDLE**（`must_via_idle`）。登录 REMOTE 时实装为先 `mode_cmd(IDLE)` 再 `REMOTE`。

## 3. 模式机

### 3.1 Python（`src/runtime/machine.py`）

互斥模式：`IDLE` | `AWAKE` | `REMOTE` | `FAULT`。  
入口：`src/main.py` + 事件队列；AWAKE 由麦唤醒/本地 socket；REMOTE 由网页登录。

### 3.2 ROS Safety（`safety_manager` arbiter）

- `/robot/mode_cmd` 请求模式；发布 `/robot/mode`。  
- 许可源：`awake` ↔ `/cmd_vel_awake`，`remote` ↔ `/cmd_vel_remote`。  
- `/robot/estop` 软件急停锁存（独立于「模式」概念，优先级最高）。  
- **无已验证独立硬件急停。**

## 4. 进程与启动拓扑

`scripts/start.sh`：

1. 可选 `tools/frp/frpc` + `config/frpc.toml`  
2. `ros2 launch safety_manager safety.launch.py`  
   - `safety_node`、`c30d_node`、`bus_node`  
   - 默认：`lidar_node`、`lidar_follow`（跟随逻辑默认 `enabled=false`）  
3. `.venv` 运行 `src/main.py`（REMOTE HTTP + AWAKE + 可选 sentry）

日志：`logs/ros_bringup.log` 等。

## 5. 关键话题（摘要）

| 话题 | 作用 |
|---|---|
| `/robot/skill_cmd` | 技能 JSON（drive/ping/…） |
| `/robot/skill_result` | 受理结果 |
| `/robot/mode_cmd` / `/robot/mode` | 模式请求 / 当前模式 |
| `/robot/estop` | 软件急停 |
| `/cmd_vel_remote` / `/cmd_vel_awake` | 分源速度入 Safety |
| `/cmd_vel_safe` | 唯一放行到底盘 |
| `/scan` | 雷达 |
| `/robot/obstacle_stop` / `/robot/obstacle_status` | 近障状态 |
| `/robot/follow_enable` | 雷达跟随开关（Bool） |
| `/odom`、TF | 里程计（Phase 5） |

细节见 `safety_interface.md`、`command_bus.md`、`lidar_assist.md`。

## 6. 配置与密钥边界

| 位置 | 内容 |
|---|---|
| `config/robot.yaml` | 行为/硬件参数（可提交） |
| `config/identity.json` | 人设与唤醒词（可提交） |
| `config/cloud.env` | 云密钥（**不提交**） |
| `config/remote_auth.json` | 网页账密哈希（**不提交**） |
| `config/frpc.toml` | 穿透（**不提交**） |
| `data/` | 媒体、记忆库、唤醒模型 |
| `logs/` | 运行日志与障碍缓存等 |

填写说明：`config/README.md`。

## 7. 与设计稿差异（避免误解）

| 设计稿提法 | 实装 |
|---|---|
| 独立 `robot_control` 包 | 限速与仲裁主要在 **command_bus + safety_manager + c30d_driver** |
| `personal_ai/` 目录树 | 现为 **`src/awake` + `src/runtime` + 记忆 SQLite**，非完整 Core |
| `robot_bringup` 包 | 实际用 **`safety_manager/safety.launch.py`** 一揽子拉起 |
