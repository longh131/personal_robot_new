# LED / 蜂鸣器探测（2026-10-19）

- 批准范围：树莓派 GPIO 短闪/短鸣。未装包，未开电机，未写 Command Bus。
- 引脚按旧 zip 复测：LED **BCM16**，蜂鸣 **BCM12**（`/dev/gpiochip4` RP1）。两线当时均空闲。
- 已执行：LED 亮灭 3 次（各 0.25s）；蜂鸣软件 PWM 2 kHz 约 0.4s。结束已拉低释放。
- 用户确认：LED 闪了三下，蜂鸣器响了一声。引脚 **GPIO16 / GPIO12 有效**。

未做：技能 ID。

## 模式与叠加（2026-10-20）

公共模块 `src/indicators/`，AWAKE/REMOTE 都用，互不 import。

| 状态 | LED | 说明 |
|---|---|---|
| IDLE | 慢呼吸 | 等唤醒 |
| IDLE 低电 | LED 快闪 + 蜂鸣持续 | 低于 `robot.yaml` 的 `low_battery_pct`；离开 IDLE 即停 |
| AWAKE | 常亮 | 交互中、未播报 |
| REMOTE | 快闪 | 远程控制 |
| 播报中 | 中速呼吸 | 叠加，不是新模式。TTS 时 `Cues.set_speaking(True/False)` |
| 唤醒被拒 | 约 1.2s 快闪 + 蜂鸣 3 声 | REMOTE/FAULT/急停时 `wake` |

GPIO：LED BCM16，蜂鸣 BCM12。`--no-led` / `--no-buzzer`。
