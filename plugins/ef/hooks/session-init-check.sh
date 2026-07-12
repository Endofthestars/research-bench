#!/usr/bin/env bash
# SessionStart hook(ef plugin):检查项目是否已初始化。
# 已有 config → 静默;没有 → stdout 一行提示(SessionStart 的 stdout 会作为上下文给 Claude)。保持简洁。
cfg="${CLAUDE_PROJECT_DIR:-$PWD}/.claude/research-bench.config.md"
[ -f "$cfg" ] && exit 0
echo "ef:本项目尚无 .claude/research-bench.config.md,建议运行 /ef:init 选择模块并初始化。"
exit 0
