# Personal AI Robot — 工程文档索引

- **基准日期**：2026-11-19  
- **声明**：本目录描述**当前仓库已实现内容**。历史阶段设计/关闭记录仍保留，若与 V1 实装文档冲突，**以 `v1_*.md` 与源码为准**。  
- **Agent 总则**：`/opt/personal_robot/AGENTS.md`（阶段门禁与安全禁令优先于本目录旧文）。

## V1 实装文档（推荐从这里读）

| 文档 | 内容 |
|---|---|
| [v1_requirements.md](v1_requirements.md) | 项目目标、V1 需求范围、安全约束 |
| [v1_architecture.md](v1_architecture.md) | 实际分层、模式机、运动数据流 |
| [v1_modules.md](v1_modules.md) | 目录与模块职责（已实现） |
| [v1_progress.md](v1_progress.md) | 开发进度：已完成 / 部分完成 / 未完成 |
| [v1_deploy.md](v1_deploy.md) | 环境、配置、启动与部署 |
| [v1_test.md](v1_test.md) | 自动化测试与人工验收要点 |
| [v1_maintain.md](v1_maintain.md) | 运维、排障、文档同步约定 |

## 专题与探测记录（按需）

| 文档 | 说明 |
|---|---|
| [awake.md](awake.md) | AWAKE 语音与指令 |
| [remote.md](remote.md) | REMOTE 网页遥控 |
| [command_bus.md](command_bus.md) | Command Bus |
| [safety_interface.md](safety_interface.md) | Safety 话题接口 |
| [lidar_assist.md](lidar_assist.md) | 雷达避障与距离跟随 |
| [memory.md](memory.md) | 长期记忆 |
| [sentry.md](sentry.md) | IDLE 看守（默认关） |
| [known_issues.md](known_issues.md) | 已知问题与风险编号 |
| [config/README.md](../config/README.md) | 配置文件填写说明 |

## 历史阶段文档（只读归档性质）

`phase0_*` … `phase5_*`、`phase_plan.md`、`architecture.md`（Phase 0 设计稿）、协议/固件探测文等：记录当时结论，**不代表全部仍是唯一实现路径**。导航与大模型 Agent 等远期目标见 `v1_progress.md` 未完成项。

## 厂商与旧项目（非实现源）

- 仓库根 `doc/`：厂商资料、旧项目压缩包等，**只读参考，不得直接拷贝为正式驱动**。
