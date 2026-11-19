# Command Bus

- 校验技能 ID 与来源。不打开串口。
- 话题：`/robot/skill_cmd`、`/robot/skill_cancel`、`/robot/skill_result`。订 `/robot/mode`、`/robot/estop`。
- `ping`：IDLE 也可。
- `drive`：REMOTE/AWAKE 且 `motion_enabled`。20 Hz：REMOTE→`/cmd_vel_remote`，AWAKE→`/cmd_vel_awake`（另一路发零速）；超时 1s 清零。仍经 Safety，不直连电机。
- `dance_1` / `dance_2`：仍只排队，无履约。
- AWAKE/REMOTE 只发 ID（`drive` 可带 vx/vy/wz）。网页遥控走 `drive`，不再直发 Twist。
- 限速参数与 `robot.yaml` `remote.*` 对齐（默认 0.15 / 0.15 / 0.40）。
- 零速≠工业急停。
