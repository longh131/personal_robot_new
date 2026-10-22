# REMOTE 媒体与网页底盘

- 拍照、录像、录音、电量、WebRTC 预览、双向语音。无 ASR/TTS/LLM。
- 文件：手动 `data/media/remote/photos|videos|recordings`；IDLE 看守 `data/media/remote/sentry/`（封面 jpg + mjpeg + wav）。
- 云台 MG90S：仅界面，未接硬件。
- 退出 REMOTE 或心跳超时：停预览、停录、关 RTC、停发速度。
- 网页底盘：按住才走（含左转/右转、Q/E）。松开停发。发 `drive` 技能，经 Command Bus → `/cmd_vel_remote` → Safety。不打开电机串口。限速见 `robot.yaml` `remote.*`。`start.sh` 不启 ROS。零速≠工业急停。
