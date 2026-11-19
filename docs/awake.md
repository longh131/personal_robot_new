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
- 系统：停发、退出、音量。查询：时间/日期/电量/天气新闻；**相机怎样**、**急停了吗**。
- 娱乐：拍照到 `data/media/awake/photos`；音乐点名/随机；听指令时暂停播放。
- 助手：记忆确认写入；**我喜欢什么/记得什么**查询；**忘掉…**确认后失效。
- **倒计时 / 提醒 / 闹钟**：进程内定时，到点蜂鸣+TTS；**取消倒计时/取消提醒**。回 IDLE 未到点的任务仍保留至进程退出。
- 电机：持续行驶 + **快点/慢点**调档；近障主动停并语音提示。`awake.vx_max`、`drive_refresh_s`、`empty_asr_prompt_n`、`timeout_warn_s` 见 `robot.yaml`。
- 质量：连续空 ASR 提示「没听清」；超时前「还在吗」；失败分因（相机/云/运动链路）。
- 听音：`min_voiced_s` 丢掉过短毛刺；`post_tts_gap_s` 减轻播后回声进 ASR；相机口令支持「怎么样/检查一下相机」等软匹配；TTS 超时会重试一次。

- 退出 AWAKE：停速 + `mode_cmd(IDLE)`（skill_pub 与 `ros2 pub --once`）；epoch 作废迟到的 `MODE AWAKE`，避免堵死后续 REMOTE。

## 跟随（备案，未做）

采购 Camera Module 3 Wide 后再开发：脸/登记开锁 + 背后人体跟踪 + 雷达刹停；仅 AWAKE → `/cmd_vel_awake`。
