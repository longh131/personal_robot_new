# Phase 4 — 安全管理（操作流程）

- 日期：2026-10-19
- 状态：**Phase 4 已关闭。** 见 `docs/phase4_close.md`。
- 你跟着看这份即可。接口定义仍以 `docs/safety_interface.md` 为准。

你回复 **「批准实施 Phase 4」** 之后，才编码。着地运动仍要另批。

---

## 目标

让运动必须经过安全层：模式互斥、超时、急停锁存、FAULT。AI/遥控/键盘都不能直连串口。

## 依赖（已具备）

- 离地：`Mec-S` 固件、使能 `O N`、ROS `i` 能转、松开能停。
- 驱动已只订 `/cmd_vel_safe`（Phase 3）。4A 已接 Safety。

## 失败回退

停 launch、关节点。驱动可临时改回只订 `/cmd_vel` 做对照。不改固件、不着地。

**限制：** 无硬件急停。软件急停 = 停发 + 零帧 + 固件约 0.3s 滑行。不是工业级急停。仍转立刻切断电机电源。

---

## 你怎么配合

| 谁 | 做什么 |
|---|---|
| 你 | 审核本计划；离地、使能 `O N`；按验收清单按键；确认现象 |
| Agent | 写包、单测、改驱动只订 `/cmd_vel_safe`、写 launch |
| 禁止 | 着地；AI/遥控打开 `/dev/c30d`；超时自动解除急停 |

---

## 分步（批准后才做）

### 4A — 无电机（先做完再碰轮）

1. 新包 `ros2_ws/src/safety_manager`（不拷旧项目）。
2. 模式：`IDLE` `AWAKE` `REMOTE` `FAULT`。AWAKE↔REMOTE 必须经 IDLE。
3. 话题（与冻结接口一致）：

   | 话题 | 作用 |
   |---|---|
   | `/cmd_vel_remote` | 遥控/ROS 键盘入口 |
   | `/cmd_vel_awake` | 预留 AI，本阶段不接真 AI |
   | `/cmd_vel_safe` | **到底盘的唯一速度** |
   | `/robot/mode` | 当前模式 |
   | `/robot/estop` | 急停请求/状态，`true` 锁存 |
   | `/robot/fault` | 故障原因 |

4. 许可：`IDLE`/`FAULT`/急停锁存 → 不向 `/cmd_vel_safe` 发非零。
5. `/cmd_vel_*` 超过 0.3s 无新消息 → 停发非零（走已验证停发）。
6. 急停：立刻许可 `none`；解除 **只能人工**（再发 `estop=false`），禁止自动清。
7. `c30d_driver` 改为 **只订 `/cmd_vel_safe`**，不再订 `/cmd_vel`。
8. 单元测试（无串口）：互斥、切换先 revoke、超时、急停锁存、双源不同时放行。
9. 验收：测试全过；`ros2 topic info /cmd_vel_safe` 订阅者只有驱动。

### 4B — 离地实机（4A 通过后再向你要一次口头批准）

前提：轮离地、屏 `Mec-S`、`O N`、准备切断电机电源。

1. `ros2 launch`：`safety_manager` + `c30d_driver`（不要旧的只订 `/cmd_vel` 的 launch 当正式入口）。
2. 设 `REMOTE`，键盘改发 **`/cmd_vel_remote`**（`i` 应转）。
3. 松手/`k`：应停（约 0.5–1s 可接受）。
4. 发 `/robot/estop true`：应立刻不再响应 `i`，轮停。
5. 不人工清急停时，再 `i` 不得转。
6. 清急停后须重新 `REMOTE` 才可动。
7. `AWAKE` 时 `/cmd_vel_remote` 不得动轮。
8. 不停：切断电机电源，停止 4B。

---

## 本阶段验收

- [x] AWAKE 与 REMOTE 不能同时有运动权
- [x] 切换先撤销旧许可，旧 Twist 不能继续驱动
- [x] 超时停发（4B 软件侧 `HALT_REQUEST`）
- [x] 急停锁存，须人工清除后重新 `REMOTE`
- [x] 驱动不订 `/cmd_vel`
- [x] 文档已更新；未宣称工业级急停

## 明确不做

Phase 5 里程计、Phase 6 远程界面、相机、着地、Command Bus 完整产品化。
