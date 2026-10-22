# 记忆

- 短期：本轮 AWAKE 的对话 history。回 IDLE 丢弃。
- 长期：SQLite 事实表，不是聊天全文。字段：kind/key/value/text、时间、来源、valid。同 kind+key 覆盖（一年前爱喝咖啡、后来改茶，以新记录为准）。
- 写入：说出稳定偏好（喜欢/爱喝/记住…）时抽取；或模型调 `remember_fact`。问句不写。
- 读出：偏好优先注入 system prompt；再按当前问句匹配。
- 库：`data/memory/facts.sqlite`，WAL。不把记忆写进 `identity.json`。
- 不是向量库、不上云存档。LLM 调用仍会把召回的几条事实发到云端补全。
- 本刀不做遗忘策略以外的 GDPR 导出界面。`valid=0` 为软删。
