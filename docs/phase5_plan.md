# Phase 5 — 编码器、里程计、TF（操作流程）

- 日期：2026-10-19
- 状态：**已正式关闭**（2026-10-19）。见 `docs/phase5_close.md`。着地补测另批。
- 关闭 Phase 5 后**立刻**做着地补测（`docs/ground_coast_test_plan.md`），不插入别的阶段。

回复 **「批准实施 Phase 5」** 后才编码。着地另见该补测文档，不在本阶段做。

## 目标

从 C30D 24 字节回包解析轮速，发 `/odom` 与 `odom`→`base_link` TF。不要求导航级精度。

## 依赖

Phase 3–4；固件已在 USB 上回 24 字节 `7B…7D`（速度 mm/s 量级）。

## 回退

停节点，不再发 `/odom`。不改固件。

## 分步（批准后）

1. 驱动只读已打开的 `/dev/c30d` RX，解析 24 字节反馈；不新开第二路串口。
2. 积分速度得位姿；`frame_id=odom`，`child=base_link`。
3. 单测：拆帧、静止速度≈0、积分一小段。
4. 离地：`REMOTE` 短时 `i`，`/odom` 有变化；停后速度回落。TF 树有 `odom`→`base_link`。

不做：Phase 6、相机、着地、Nav2、工业急停。
