# V1 测试说明

- 日期：2026-11-19  
- 原则：自动化优先；实机运动须有步骤/预期/停止条件，且通常需用户在场批准。

## 1. 自动化单测（无电机）

在项目根，使用 venv：

```bash
cd /opt/personal_robot
PYTHONPATH=src .venv/bin/python -m pytest \
  src/awake/test_intent.py \
  src/awake/test_scheduler.py \
  src/runtime/test_machine.py \
  src/remote/test_drive_scale.py \
  src/remote/test_media_library.py \
  src/remote/test_gimbal.py \
  src/sentry/test_watch.py \
  -q
```

ROS 包测试（需已 source Jazzy，并按包惯例运行），例如：

- `ros2_ws/src/safety_manager/test/`（`test_arbiter.py`、`test_obstacle.py`）  
- `ros2_ws/src/command_bus/test/test_validator.py`  
- `ros2_ws/src/c30d_driver/test/`（协议、串口链路、odom 等）

具体命令以各包 `pytest`/`ament` 习惯为准；**测试不得调用禁止脚本 `single_test.py`**。

## 2. 人工验收清单（V1）

### 2.1 启动与模式

1. `scripts/start.sh` 后 Safety 起来；IDLE 等待。  
2. 说唤醒词进 AWAKE；说「再见」回 IDLE。  
3. IDLE 下网页登录进 REMOTE；心跳保持；登出回 IDLE。  
4. AWAKE 中登录应 `awake_busy`。  
5. **AWAKE → 再见 → 再登录 REMOTE，遥控应能走**（回归：模式须经 IDLE）。

### 2.2 REMOTE 运动与安全

1. 按住前进/平移/转向有响应；松手停发。  
2. 限速滑条生效。  
3. 软件急停后不能再遥控运动（锁存）。  
4. 前方近障时前进应被 Safety 裁掉（看 `/robot/obstacle_stop` 或网页状态）。  
5. **不宣称工业急停。**

### 2.3 音视频

1. 预览有图（相机在线时）；拍照落盘 `data/media/remote/photos`。  
2. 通话：浏览器麦与机身扬声器/麦互通。  
3. 云台按键有动作（供电与接线正常时）。

### 2.4 AWAKE

1. 天气/新闻/时间/电量。  
2. 「倒计时 10 秒」到点有声；可取消。  
3. 记忆确认写入；「我喜欢什么」；忘掉须确认。  
4. 「相机怎样」走自检意图（非纯闲聊）。  
5. 「前进」持续走，「停下」停；近障有提示。  
6. 连续空听有「没听清」类提示。

### 2.5 雷达跟随（可选）

仅当显式 `follow_enable true` 且模式 AWAKE 时测距离保持；默认关。**不是**视觉认人跟随。

## 3. 历史实机记录位置

- 协议/停止：`phase2_*.md`、`c30d_protocol_evidence.md`  
- 着地滑行：`ground_coast_test_plan.md`  
- 相机/音频探测：`camera_probe.md`、`audio_probe.md`  
- 雷达：`lidar_probe.md`、`lidar_assist.md`  

## 4. 已知测试缺口（诚实列出）

- 断线、杀进程、拔 USB 的停车完备性：**未作为工业认证项**（见 KI-003）。  
- 相机稳定性依赖硬件接触，自动化无法替代插线复测。  
- 云 ASR/TTS 受网络与配额影响，空识别/超时仍可能出现。
