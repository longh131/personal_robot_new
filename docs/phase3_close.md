# Phase 3 关闭

- 日期：2026-10-19
- 状态：**正式关闭**（用户审核，2026-10-19）

## 已做

- `c30d_driver` 只订 `/cmd_vel_safe`
- 限速 `count_limit=120`（不另建 `robot_control`，与冻结接口一致：Safety → 驱动）
- `/c30d/connected`；写/开失败 → `serial_disconnect` halt
- 退出发零帧后关串口（Mec-S 离地停发策略）
- 默认口 `/dev/c30d`，拒绝 `/dev/ttyACM0`
- 单测：组帧、限幅、门闩、串口失败断开

## 不做

独立 `robot_control` 包、着地、拔线实机、Phase 4。

## 回退

停节点。需要旧键盘直连时不可再订 `/cmd_vel`（已删除）。
