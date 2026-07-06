---
description: 按执行档案(exec-profile)执行训练实验，包含 baseline 对照、实验跟踪记录和复现信息。交互判断由主流程完成，关键 op 序列一次性委托 operator 执行。适用于启动训练、对比改动效果和执行消融实验。
---

执行本插件的 `run-experiment` skill:读取 ${CLAUDE_PLUGIN_ROOT}/skills/run-experiment/SKILL.md 并严格按其内容执行。用户附加参数:$ARGUMENTS
