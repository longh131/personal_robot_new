# 雷达嵌入：避障停 + 跟随距离

- 日期：2026-11-17
- 随 `scripts/start.sh` → `safety.launch.py` 拉起：`lidar_node` + `safety` 避障 + `lidar_follow`（默认关）

## 1. 运动避障停止（已开）

- 位置：`safety_manager` 订 `/scan`，在发 `/cmd_vel_safe` 前裁剪速度。
- 四向扇区（各约 ±50°）：前进看前、后退看后、左移看左、右移看右；`stop_m=0.45` 清掉该方向速度，`hard_m=0.30` 全停。原地旋转不按平移刹。
- `ignore_below_m=0.28`：更近的点当车身自回波，不刹停。
- 状态：`/robot/obstacle_stop`（Bool）；详情 `/robot/obstacle_status`（String JSON）。
- 参数：`ros2_ws/src/safety_manager/config/safety.yaml`。
- **底盘必须出现 `/dev/c30d`（USB `1a86:55d4`）**；只插雷达时驱动打不开，车不会动。

## 2. 跟随保持距离（默认关）

- 节点：`lidar_assist/follow_node` → 只发 `/cmd_vel_awake`（须 **AWAKE** 模式才有许可）。
- **关闭时不得往该话题刷零速**（与 Command Bus 语音驱动共用；刷零会冲掉 AWAKE 行走，REMOTE 不受影响）。
- 目标距离默认 `0.80m`，死区 `0.12m`，`vx_max=0.12`。
- 开启：
  ```bash
  ros2 topic pub --once /robot/follow_enable std_msgs/msg/Bool "{data: true}"
  ```
- 关闭：`data: false`（发一次零速）。仍受 Safety 避障约束。
- **本刀不自动跟人识别**，只按正前方最近距离调前后。REMOTE 网页开车仍靠避障刹停。

## 验收（用户操作，Agent 不发速度）

1. `scripts/start.sh`，日志有 `Lidar started`、`obstacle stop on /scan`。
2. REMOTE 前进，前方挡物 <0.4m 应停前进；`/robot/obstacle_stop` 为 true。
3. （可选）进 AWAKE 后 `follow_enable true`，人靠近/远离看是否慢跟。

## 限制

- 无工业急停；零速≠急停。
- 跟随仅 AWAKE；不做视觉跟人。
- 雷达丢数超过 `stale_s` 时不信任测距，避障不误刹（也不在无扫描时额外锁死）。
