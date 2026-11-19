# V1 维护与文档同步

- 日期：2026-11-19  

## 1. 日常运维

| 事项 | 做法 |
|---|---|
| 启停 | `scripts/start.sh`；Ctrl+C 清理子进程 |
| 日志目录 | 只用 `logs/`；根下旧 `log/`、`opt/` 已于 2026-11-19 删除 |
| 看 ROS | `logs/ros_bringup.log`；`ros2 node list` / `ros2 topic echo /robot/mode` |
| 改限速/听音/云台 | 改 `config/robot.yaml` 后重启 start |
| 改唤醒词/人设 | 改 `config/identity.json` 后重启 |
| 改网页密码 | `scripts/set_remote_password.py` 后重启 |
| 换云 Key/模型 | 改 `config/cloud.env` 后重启 |
| 重建 ROS | `colcon build` 相关包后再 start |
| 相机无图 | `rpicam.sh --list-cameras`、`i2cdetect`；查 KI-017 |
| AWAKE 后 REMOTE 不动 | 确认 `/robot/mode` 为 REMOTE；登录应先 IDLE 再 REMOTE |

## 2. 排障优先级

1. **安全**：是否急停锁存、是否 FAULT、底盘 `/dev/c30d` 是否在。  
2. **模式**：Python 模式与 `/robot/mode` 是否一致。  
3. **Bus**：`skill rejected` 原因（`no_motion_permit` / `source_mode_mismatch` / `estop_latched`）。  
4. **传感器**：雷达丢数时近障逻辑见 `safety.yaml` / `lidar_assist.md`。  
5. **云与音频**：ASR 空、TTS 超时查网络与 `cloud.env`；声卡名是否仍为 Y1076。

## 3. 变更纪律（与 AGENTS.md 一致）

1. 一次只做一个已批准范围；不擅自进下一阶段。  
2. Python 新依赖只进根目录 `requirements.txt`；系统依赖只进 `setup.sh`。  
3. 不写死串口为 `/dev/ttyACM0`。  
4. 不运行无停止条件运动脚本。  
5. 不默认启动电机；Agent 不自测发速度/转舵机。  

## 4. 文档同步约定（强制）

**今后代码或配置有重要变更时，必须同步更新相关文档**，至少检查：

| 变更类型 | 更新文档 |
|---|---|
| 新能力 / 砍能力 | `v1_requirements.md`、`v1_progress.md`、对应专题 md |
| 运动链、话题、模式规则 | `v1_architecture.md`、`safety_interface.md`、`command_bus.md` |
| 新包/新目录/职责变化 | `v1_modules.md` |
| 启动方式、依赖、配置项 | `v1_deploy.md`、`config/README.md` |
| 测试方式或验收 | `v1_test.md` |
| 新风险 | `known_issues.md`（编号延续） |
| REMOTE / AWAKE 行为 | `remote.md` / `awake.md` |

文档索引：`docs/README.md`。  
历史 `phase*` 文一般**追加说明**或在 V1 文中标注「已由实装替代」，避免偷偷改历史结论造成审计混乱。

## 5. 备份建议

- 定期备份：`config/`（含本地密钥）、`data/memory/`、重要媒体。  
- 若使用 git：勿提交 `cloud.env`、`remote_auth.json`、`frpc.toml`、大数据与模型文件（见 `.gitignore`）。

## 6. 联系实现边界

维护者提问「现在有没有某某功能」时，以 **`v1_progress.md` + 源码** 为准，不以早期 `architecture.md` 设计愿望为准。
