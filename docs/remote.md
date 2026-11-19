# REMOTE 媒体与网页底盘

- 拍照、录像、录音、电量、WebRTC 预览、双向语音。无 ASR/TTS/LLM。
- 文件：手动 `data/media/remote/photos|videos|recordings`；IDLE 看守 `data/media/remote/sentry/`（封面 jpg + mjpeg + wav）。
- **查看媒体**：主控页底部「查看媒体」开新窗 `/media.html`。分类含 REMOTE 拍照/录像/录音、sentry、AWAKE 拍照/音乐。登录 Cookie 共用；可预览、下载、删除（二次确认）。路径限制在配置目录内，防穿越。
- 登录：先 `ensure_skill_pub`，再以 `ros2 topic pub --once /robot/mode_cmd` 切 REMOTE（可靠路径；skill_pub 仅附带 nudge）。监控区 sticky。
- **限速滑条**：运动区 20%–100%，登录重置 100%；仍受 `remote.vx/vy/wz_max` 硬顶。
- **障碍物**：监控下方四向距离 + 刹停提示（`/robot/obstacle_status` → skill_pub 缓存）。
- **会话/链路**：顶栏 RTT + 心跳剩余。
- **软件急停**：状态区放大按钮 + 确认；文案标明非工业硬件急停、非「已锁存」状态条。不另加 sticky 急停条，避免挡按键。
- 云台 MG90S：`gpiozero` + `lgpio`。水平 **BCM24**、俯仰 **BCM19**。按住才输出，松手 `detach`。单轴测试：`hardware_test/gimbal/servo_lgpio_sweep.py`。独立 5V；可并 220–470µF。
- 退出 REMOTE 或心跳超时：停预览、停录、关 RTC、停发速度、云台回中停 PWM。
- 网页底盘：按住才走。发 `drive` 技能，经 Command Bus → `/cmd_vel_remote` → Safety → `/cmd_vel_safe` → `c30d_driver`。`scripts/start.sh` 同时拉 Safety+Bus+C30D（默认不转，等 REMOTE 按键）。零速≠工业急停。
- AWAKE 进行中网页登录返回 `409 awake_busy`，不得抢断；须语音退出 AWAKE 回 IDLE 后再登 REMOTE。Safety 无硬件急停。
- 云台按住只发一次开始、松开发停；HTTP/1.1 keepalive。避免经 FRP 把 workconnection 打满后心跳失败变成 `/api/gimbal` 401。
