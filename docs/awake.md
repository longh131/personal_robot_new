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

进 AWAKE 后随机播 `identity.json` 的 `greetings`，听完一句再云 ASR。DeepSeek 回答后 Qwen TTS（HTTP，15s 超时）。播报中可打断；播完不关麦，同一路接着听，避免「退出」落在空档。告别不打断。天气/新闻走搜索；几点/日期/电量走本地工具。长期事实在 `data/memory/facts.sqlite`。超时、听音、UPS、低电在 `config/robot.yaml`。说「再见/退出」立即告别回 IDLE。
