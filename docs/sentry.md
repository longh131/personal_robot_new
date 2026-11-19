# IDLE 看守

- 仅 IDLE、急停未锁。REMOTE/AWAKE 停。不走位、不转云台。
- 2026-11-17：相机 I2C 无应答期间 `sentry.enabled=false`，避免预览空转刷屏。摄像头恢复后再开。
- 帧差触发后录 `clip_s` 秒（默认 10）：MJPEG + WAV。录音期间暂停唤醒麦。
- 目录：`data/media/remote/sentry/`（与手动 photos/videos 分开）。
- `notify` 预留，不推终端。
