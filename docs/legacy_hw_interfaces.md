# 旧 pi_robot zip 硬件接口（只读参考）

来源：`doc/pi_robot.1.2.6.7z`。**不拷贝为正式驱动。引脚/设备名必须在本机复测。**

| 设备 | 旧代码接口 | 备注 |
|---|---|---|
| LED | `gpiozero.PWMLED`，默认 **GPIO 16** | IDLE 呼吸 / AWAKE 常亮 / REMOTE 快闪 |
| 蜂鸣器 | `gpiozero.PWMOutputDevice`，默认 **GPIO 12**，PWM 2 kHz | 无源蜂鸣；intent `BEEP` |
| 相机 | **Picamera2** CSI，640×480；拍照 `switch_mode_and_capture_file` | 本机还有 USB **Yundea 1076**，不能假定仍是 CSI |
| 录像配音 | `arecord -D` 默认 **`plughw:2,0`**，`.env` 的 `AUDIO_DEVICE` | 本机播放/采集卡是 **Y1076 card 1**，须重测 |
| 唤醒/ASR 麦 | `sounddevice`，16 kHz 单声道 float32 | 未指定 ALSA 卡号 |
| 超声波（另件） | `lgpio`，TRIG **24** ECHO **25**，优先 `gpiochip4` | 本阶段未排进「先测」清单 |

C30D 固件里也有板载 LED/蜂鸣器（STM32），与树莓派 GPIO 16/12 **不是同一套**。先确认灯和蜂鸣器焊在 Pi 上还是底盘上。
