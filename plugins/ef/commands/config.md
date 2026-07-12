---
description: 项目配置管理入口。支持查看 manifest 和占位统计、定点修改配置值、非交互初始化配置，以及经确认写入 .claude/settings.json 的保护机制 env。适用于快速查看或修改 research-bench.config.md。
---

执行本插件的 `config` skill:读取 ${CLAUDE_PLUGIN_ROOT}/skills/config/SKILL.md 并严格按其内容执行。用户附加参数:$ARGUMENTS
