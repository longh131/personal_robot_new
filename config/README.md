# config/ 说明

密钥类文件不要提交 git。改完后一般要重启 `scripts/start.sh`。  
**以后凡改 config（含新增文件、改字段、改填写方式）都要同步更新本文件。**

| 文件 | 用途 | 提交 | 怎么填 |
|---|---|---|---|
| `identity.json` | 机器人是谁：名字、人称、人设、展示用唤醒词、问候/告别/退出词 | 可提交 | 直接改 JSON |
| `robot.yaml` | 现场/硬件/行为：时区、超时、听音、打断、记忆条数、UPS、低电、声卡 | 可提交 | 直接改 YAML |
| `cloud.env` | 云端 ASR/TTS/LLM **密钥和模型名** | **否** | 从 example 复制后填 `DASHSCOPE_API_KEY` 和 `DEEPSEEK_API_KEY` |
| `cloud.env.example` | 云端配置模板 | 是 | 不要把真 Key 写进 example |
| `remote_auth.json` | 远程网页登录（用户名 + 密码哈希） | **否** | 见下方「远程登录密码」 |
| `remote_auth.json.example` | 远程账密模板 | 是 | 不要手改 hash |
| `frpc.toml` | 内网穿透（pi.zwic.cn） | **否** | 从 `frpc.toml.example` 复制，token 与云端 frps 相同 |
| `frpc.toml.example` | frpc 模板 | 是 | 只改 example 里的占位符说明 |

## 远程登录密码

网页登录只读 `remote_auth.json` 的用户名和密码哈希，不含心跳。  
REMOTE 心跳超时：`robot.yaml` 的 `remote.heartbeat_timeout_s`（秒，默认 30，至少 8）。经 FRP 容易卡，别设太短。改完重启 `start.sh`。

设置或修改（至少 8 位，交互输入，终端不回显）：

```bash
python3 /opt/personal_robot/scripts/set_remote_password.py --user andylong
```

脚本会写入 `/opt/personal_robot/config/remote_auth.json` 并 `chmod 600`。改完重启 `scripts/start.sh`。不要把密码写进 README 或 identity。

## 唤醒词

- **只改** `identity.json` 的 `wake_words`。启动时编成 Sherpa `data/models/wake/keywords.txt`（会覆盖该文件）。
- 改 JSON 后必须重启 `start.sh`。日志应有 `kws from identity.json n=…`。
- 词宜短、互不高度相似；太短容易误唤醒。

## 云端 TTS（已接问候）

- 当前：**Qwen3-TTS-Flash** + 音色 **Cherry**。
- `DASHSCOPE_TTS_MODEL=qwen3-tts-flash`（若带日期的 `qwen3-tts-flash-2025-11-27` 已下线，用这个当前名）。
- **换音色改 `DASHSCOPE_TTS_VOICE`**（Cherry / Bella / Mia 等），然后重启 `start.sh`。
- 喇叭/麦克风：`robot.yaml` 的 `audio.playback` / `audio.capture`（默认 `plughw:Y1076,0`）。
- 进 AWAKE 后随机播 `identity.json` 的 `greetings`，听完一句再 ASR。
- ASR：`DASHSCOPE_ASR_MODEL`（默认 `paraformer-realtime-v2`）。
- LLM：官方 DeepSeek（默认 `deepseek-flash`，`DEEPSEEK_API_KEY`）。人设只来自 `identity.json`。
- 搜索插件：天气/新闻走 `web_search`（百炼联网）。
- 本地工具：几点 / 日期 / 电量。UPS 地址在 `robot.yaml` 的 `ups`（只读，不跑厂商关机脚本）。
- IDLE 低电报警：低于 `robot.yaml` 的 `low_battery_pct`（默认 10）时蜂鸣持续、LED 快闪。**仅 IDLE**。
- 听完再答：`robot.yaml` 的 `listen.wait_s` / `silence_s` / `max_s` / `rms`。
- 播报打断：`interrupt.enabled`。播报走 PipeWire 全双工，说话约 0.2s 后停 TTS；句首约 0.5s 会预录，避免「你很好」只认出「很好」。打断后继续用 PipeWire 听，不再抢 `plughw`。误触发调高 `interrupt.rms`。告别语不打断。
- 长期记忆：SQLite `data/memory/facts.sqlite`（不进 git）。偏好有时间戳、可覆盖。不是聊天记录。召回条数 `memory.prompt_limit`。短期记忆为本轮 AWAKE 对话，回 IDLE 清掉。
- 命中 `identity.json` 的 `exit_phrases` 则播 `farewells` 回 IDLE。
- AWAKE 无有效对话超时：`robot.yaml` 的 `idle_timeout_s`（秒，默认 30，范围 5–86400）。改完重启 `start.sh`。
- 密钥只在 `cloud.env`，不要写进 Python。

## REMOTE 媒体

- 拍照/录像/录音文件：`data/media/remote/`（路径在 `robot.yaml` 的 `media.photos` / `videos` / `recordings`）。
- 录像、录音可按键开始/结束；不能超过 `video_max_s` / `audio_max_s`（秒）。
- 预览：WebRTC。局域网可用；经 FRP 仅 TCP 时 ICE 可能失败，页面会回退 JPEG。
- 通话：浏览器麦 ↔ 机器人喇叭/麦，**不含 ASR/TTS/LLM**。登录 REMOTE 会先停唤醒麦，对讲采集 `audio.capture`。
- 云台 MG90S：页面按键已留，`gimbal.enabled` 现为 false，不转舵机。
- 网页底盘：按住才走，松开停发。网页只发 `drive` 技能，经 Command Bus → Safety，不直连串口。`start.sh` 不启电机。

### 网页底盘限速（`robot.yaml` 的 `remote`）

走 ROS `Twist`，**不是**「转几圈」。按住只发恒速，不会越按越快。

| 字段 | 控制什么 | 网页对应 | 名义单位 |
|---|---|---|---|
| `vx_max` | 前后平移上限。`+vx` 前进，`-vx` 后退 | 前进 / 后退 | 米/秒（名义） |
| `vy_max` | 左右平移上限。`+vy` 左移，`-vy` 右移 | 左移 / 右移 | 米/秒（名义） |
| `wz_max` | **原地转向**角速度上限，**不是**前进/后退。`+wz` 逆时针（从上往下看），`-wz` 顺时针 | 左转 / 右转（Q / E） | 弧度/秒（名义） |

当前值：`vx_max`/`vy_max` `0.15`，`wz_max` `0.40`。

怎么理解数值：

- `1.0` **不是**「一秒十转」，也还没标定成真实地面速度。
- 名义上：`vx=1` ≈ 每秒 1 米；`wz=1` ≈ 每秒 1 弧度（约 57°/秒，转一圈约 6.3 秒）。实车对不上这个尺子。
- 驱动会 `×300` 再限幅 `120`，所以发到电机的有效上限约 `120/300 = 0.4`。yaml 写成 `1.0` 也会被截到约 `0.4`。
- `0.15 × 300 = 45`，着地短测已能慢走。要更快先加 `vx_max`，但仍会被 `0.4` 卡住；再快要改驱动 `c30d.yaml` 的 `count_limit`（另批，别随便加）。

改 `robot.yaml` 后网页夹紧会马上读新值；运动链路仍要 Safety+驱动在跑。零速≠工业急停。

## IDLE 看守（sentry）

仅 `IDLE` 且急停未锁。进 REMOTE/AWAKE 停检测与录制。不走位、不转云台。触发后录 `clip_s` 秒画面+声音（录音时暂停唤醒麦）。

文件都在 `media.sentry`（默认 `data/media/remote/sentry/`），与网页手动拍照/录像分开：`时间.jpg` 封面、`时间.mjpeg` 画面、`时间.wav` 声音、`events.jsonl` 事件（`notify` 预留）。VLC 可看 mjpeg、听 wav。

| 字段 | 含义 | 默认 |
|---|---|---|
| `sentry.enabled` | 是否开看守 | true |
| `sentry.threshold` | 灰度帧差阈值，越大越钝 | 10 |
| `sentry.clip_s` | 每次触发录制秒数（2–60） | 10 |
| `sentry.cooldown_s` | 两次事件最短间隔（秒） | 8 |
| `sentry.max_events_per_hour` | 每小时最多事件 | 12 |
| `sentry.warmup_s` | 开相机后忽略抖动 | 2 |
| `sentry.buzzer` | 触发时是否短鸣 | false |

改完重启 `start.sh`。
