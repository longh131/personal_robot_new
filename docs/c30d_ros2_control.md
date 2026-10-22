# C30D ROS 2 控制

## 查清的事实

- 11 字节帧可启动电机。
- **Mec-S**、使能 `O N`：停发/`k` 后离地约 0.5–1s 停。
- 无硬件急停。使能关则电机不动。

## 驱动行为（Phase 3）

- **只订 `/cmd_vel_safe`**。不订 `/cmd_vel`。
- 20 Hz；scale=300；限幅 120。
- 超时 0.3s / 近零 / 退出 / 串口失败：`halt_request`，发零帧后停非零。
- `/c30d/halted`、`/c30d/connected`、`/c30d/status`。
- 端口默认 `/dev/c30d`，拒绝写死 `ttyACM0`。

Phase 4 之前，正式入口尚未接 Safety。离地调试才允许：

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r /cmd_vel:=/cmd_vel_safe
```

正式遥控须经 Safety 的 `/cmd_vel_remote` → `/cmd_vel_safe`。
