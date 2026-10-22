# 音频探测（2026-10-19）

- 批准范围：麦 + 喇叭通断。未装新软件，未开电机，未做对讲/ASR。
- 结果：**ALSA 通路通。** 播放与录音命令均成功。请你确认是否听到 880Hz 提示音和回放。

## 事实

- 用户已在 `audio` 组。
- 播放：`vc4-hdmi-0`、`Yundea 1076`（card 1）、`vc4-hdmi-1`。
- 采集：仅 `Y1076` capture。
- 测的是 USB `Yundea 1076`（`plughw:Y1076,0`），不是 HDMI。
- `PCM` 播放约 80%；`Mic` 采集开、约 80%。
- `aplay` 1s 880Hz：成功。`arecord` 16 kHz 单声道 3s：成功。录音 peak ≈ -35 dBFS（有信号，偏安静）。
- 文件：`hardware_test/audio/beep_880hz.wav`、`mic_3s.wav`。
- 无 `pactl`；Python 无 `sounddevice`。未接 Ubuntu `libcamera`。

## 回退

无系统包变更。mixer 音量留在约 80%。

## 未做

双向对讲、延迟测量、ROS 音频节点、唤醒/ASR/TTS。那是 Phase 8/9，另批。
