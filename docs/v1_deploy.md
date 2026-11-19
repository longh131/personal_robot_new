# V1 部署与运行

- 日期：2026-11-19  
- 主机约定：`andylong@` Raspberry Pi 5，项目根 `/opt/personal_robot/`。

## 1. 运行时依赖（已存在于本机时的约定）

| 依赖 | 用途 |
|---|---|
| Ubuntu 24.04 + ROS 2 Jazzy | `source /opt/ros/jazzy/setup.bash` |
| `ros2_ws` colcon 安装前缀 | `ros2_ws/install/setup.bash` |
| Python `.venv`（建议 `--system-site-packages`） | `requirements.txt`：sherpa-onnx、dashscope、PyYAML、pypinyin、aiortc |
| 系统包 | 见 `setup.sh`（gpiozero/lgpio、雷达 udev 等）；**改系统须先批准** |
| `tools/rpi_camera` | Pi 5 PiSP/rpicam，经 `scripts/rpicam.sh` 调用 |
| 可选 `tools/frp/frpc` | 与 `config/frpc.toml` |

## 2. 配置清单（启动前）

按 `config/README.md` 准备：

1. `cloud.env`（从 example 复制，填 API Key）  
2. `remote_auth.json`（`scripts/set_remote_password.py`）  
3. 可选 `frpc.toml`  
4. 按现场改 `robot.yaml`（声卡、限速、云台脚、听音等）  
5. 按需改 `identity.json`（唤醒词、人设）  

密钥类文件权限建议 `600`，**不要提交 git**。

## 3. 构建 ROS 包（有代码变更时）

```bash
source /opt/ros/jazzy/setup.bash
cd /opt/personal_robot/ros2_ws
colcon build --symlink-install
# 按需：--packages-select safety_manager command_bus c30d_driver lidar_pkg lidar_assist
```

## 4. 日常启动 / 停止

```bash
cd /opt/personal_robot
scripts/start.sh
# Ctrl+C 结束：脚本 trap 会清理 frpc / ros launch / main
```

启动后预期：

- 日志出现 `ros: safety_manager up`（或提示看 `logs/ros_bringup.log`）  
- `REMOTE http://127.0.0.1:5000`  
- 麦克风唤醒就绪（除非 `--no-mic`）  

常用参数（传给 `main.py`）：`--no-remote` / `--no-awake` / `--no-mic` / `--no-led` / `--no-buzzer`。

## 5. 访问方式

| 方式 | 地址 |
|---|---|
| 本机 | `http://127.0.0.1:5000` |
| 穿透 | 以 `frpc.toml` 为准（示例域名见配置说明） |

登录后进入 REMOTE；**AWAKE 进行中网页登录返回 `awake_busy`**，须先语音退出。

## 6. 设备节点检查

```bash
# 底盘
ls -l /dev/c30d
# 雷达（若已装 udev）
ls -l /dev/lidar
# 相机（项目栈）
scripts/rpicam.sh rpicam-hello --list-cameras
# I2C 探头（OV5647 常在 bus 11 的 0x36）
i2cdetect -y 11
```

底盘未出现时驱动打不开，车不会动（仅插雷达不够）。

## 7. 安全操作提示

- 首次遥控：周围留空、准备断电/拔 USB。  
- 软件急停：网页急停（锁存，需人工恢复流程）。  
- **不是**工业硬件急停。  
- Agent/自动化**不得**自行发速度验收。

## 8. 回滚思路

- 停 `start.sh` 即停运动栈与网页。  
- 配置回退：恢复 `robot.yaml` / 身份 / 云环境备份。  
- ROS：切回已知可工作的 `install` 或重新 `colcon build` 指定提交（若使用 git）。
