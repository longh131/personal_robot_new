# 安全层接口冻结（Phase 2A）

日期：2026-10-15  
状态：设计冻结。Phase 4 已关闭。模式请求 `/robot/mode_cmd`。

## 1. 话题

| 话题 | 类型 | 方向 | 规则 |
|---|---|---|---|
| `/cmd_vel_remote` | `geometry_msgs/msg/Twist` | 遥控 → Safety | 仅 REMOTE 且急停未锁、有许可时采用 |
| `/cmd_vel_awake` | `geometry_msgs/msg/Twist` | AI → Safety | 仅 AWAKE 且同上 |
| `/cmd_vel_safe` | `geometry_msgs/msg/Twist` | Safety → 驱动 | **底盘唯一速度入口**。未来 `c30d_driver` 只订此话题 |
| `/robot/mode` | `std_msgs/msg/String` | Safety 发布 | 取值 `IDLE` `AWAKE` `REMOTE` `FAULT` |
| `/robot/estop` | `std_msgs/msg/Bool` | 双向：请求订+状态发 | `true`=急停锁存 |
| `/robot/fault` | `std_msgs/msg/String` | Safety 发布 | 故障原因；可空 |

禁止：AI/远程/teleop 发布到 `/cmd_vel_safe`。禁止任何非驱动节点打开 C30D 串口。  
过渡期若存在 `/cmd_vel`，不得作为到底盘的路径。

QoS（实现时）：速度与急停用 VOLATILE + 小队列（深度 1 建议），避免旧 Twist 滞留。

## 2. 模式互斥

同一时刻一个模式。`IDLE`/`FAULT` 无运动许可。

| 转移 | 允许 | 条件 |
|---|---|---|
| IDLE→AWAKE | 是 | 唤醒成功且 `estop=false` |
| IDLE→REMOTE | 是 | 远程会话有效且 `estop=false` |
| AWAKE→IDLE | 是 | 退出/超时；先 revoke |
| REMOTE→IDLE | 是 | 断开/退出；先 revoke |
| *→FAULT | 是 | 串口丢失、协议失败超限、安全检查失败 |
| FAULT→IDLE | 是 | 人工确认 + 自检 + `estop=false` |
| AWAKE↔REMOTE | **否** | 必须经 IDLE |

许可源标识：`none` | `awake` | `remote`。与模式绑定，不得双源。

## 3. 控制权切换

1. `revoke`：许可=`none`；停止向 `/cmd_vel_safe` 发非零 Twist；清空内部最新命令。
2. 等待：**安全静止**（2D 定义）或进入 FAULT。2D 前不得把“已发零速”当作静止。
3. `grant`：新模式与许可源同时生效。
4. 实现须保证切换后旧消息不能再被驱动执行（深度 1 + 切换时发布者侧停发）。

## 4. 急停锁存（非模式）

优先级：硬件急停（无）> `/robot/estop` 锁存 > FAULT > 模式许可。

置位：立刻许可=`none`；停止非零 `/cmd_vel_safe`；若 2D 已选定停止策略则执行，否则只停发并记录能力不足。  
复位：仅人工；禁止超时自动清除。  
通信失联（命令超时，建议默认 300 ms，2D 可改）：视同软件急停路径。

**已冻结限制：** 无硬件急停。软件急停不是工业级；离地/着地短测停发有效。

## 5. 驱动约束（Phase 3 才编码）

- 只订 `/cmd_vel_safe`。
- 设备用 `/dev/c30d` 或 by-id，禁止写死假定永为 `ttyACM0`。
- 协议按 2C 结果，不按归档包复制节点。
- 断开、坏数据、超时、重复命令、退出必须处理；退出不得调用未验证的运动帧当“安全”。
