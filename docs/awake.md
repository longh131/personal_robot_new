# AWAKE

## 第一刀（已通过 2026-10-20）

- 套接字 `wake`：`IDLE -> AWAKE`，网页 `awake_busy`。
- REMOTE 时忽略；`Cues.denied()` 蜂鸣 3 声 + LED 快闪。

## 麦克风（Sherpa-ONNX KWS）

- 不用 openWakeWord。中文关键词：**小派**。
- 模型：`data/models/wake/`（WenetSpeech zipformer 3.3M int8，ModelScope 已下载）。
- 改词：只改 `identity.json` 的 `wake_words`，启动时生成 `keywords.txt`。
- 检出后仍 `handle_text("wake")`。`--no-mic` 关闭。
- 依赖：`.venv` + `requirements.txt`（`sherpa-onnx`）。

验收：重启 `scripts/start.sh`，日志有 `mic wake ... kws=sherpa`。IDLE 下说「小派」应 `mic detected` 并进入 AWAKE。REMOTE 时说不应切模式，应蜂鸣。

## 云 TTS 问候

进 AWAKE 后随机播 `identity.json` 的 `greetings`，听完一句再云 ASR。指令走关键词表；未命中才 DeepSeek。Qwen TTS（HTTP，15s 超时）。播报中可打断；播完不关麦。告别不打断。天气/新闻走百炼联网搜索（默认 `qwen-plus`+`enable_search`）；失败口头兜底，不崩 AWAKE 线程。几点/日期/电量走本地工具。长期事实在 `data/memory/facts.sqlite`，须确认才写。超时、听音、UPS、低电在 `config/robot.yaml`。说「再见/退出」立即告别回 IDLE。REMOTE 网页登录在 AWAKE 时拒绝（`awake_busy`），不得抢断对话。

## 对话指令（本刀）

- 不引用 `remote/`。听清 → 关键词指令（最长词优先，再比权重）→ 否则闲聊 → TTS。REMOTE 抢权停听停播、不告别抢声卡。
- 系统：停发、退出、音量（含调大/调高等口语）。查询：时间/日期/电量/天气新闻。娱乐：拍照到 `data/media/awake/photos`；音乐点名/随机；听指令时暂停播放以免抢麦。助手：记忆须确认才写入主人档案。
- 电机语音：进 AWAKE 时 `mode_cmd(AWAKE)`；说「前进」等为**持续行驶**（`awake/skill_pub` 每 `drive_refresh_s` 刷新 → Bus → `/cmd_vel_awake`），说「停下/别动」或退出 AWAKE 才停；近障由 Safety 刹该向。速度见 `awake.vx_max` 等。跟随同依赖 AWAKE 许可。
- 闹钟/倒计时/提醒只占词表，履约后做。
