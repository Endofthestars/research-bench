#!/usr/bin/env bash
# PreToolUse hook(lf plugin):拦截绕开受控启动通道直接执行训练的命令。
# 不变量:**训练必须走受控启动通道**(通道由执行档案 exec-profile 决定——远程句柄、docker exec、
# ssh 或 scripts/run.sh 启动器);直接启动训练会绕开 env 注入、日志留档与可复现约束。
#
# 模块门控:先读项目 config(.claude/research-bench.config.md)顶部 frontmatter 的 manifest;
# config 不存在、或 modules 不含 exec → 静默放行(exit 0),本保护机制只在启用 exec 模块时生效。
#
# Claude Code 通过 stdin 传入 JSON(.tool_input.command = 将要执行的 Bash 命令)。
# 规则:命令含训练特征、但不含合法启动通道特征 → 阻止(退出码 2 = 阻止并把 stderr 反馈给 Claude)。
#
# 通用化:两组模式从环境变量读取。在项目 .claude/settings.json 的 "env" 中按项目需要覆盖
# (值来源见 config §7.1;也可用 /lf:config set env.* 经确认后代写):
#   RW_TRAIN_PATTERNS  —— 训练命令特征,扩展正则,`|` 分隔;未设用内置默认(常见训练入口示例)
#   RW_EXEC_PATTERN    —— 合法启动通道特征,扩展正则;命令匹配它才放行。
#                         未设时按 frontmatter 的 exec-profile 取内置默认通道模式:
#                           remote-docker → docker[[:space:]]+--context.*(exec|run)
#                           remote-venv   → ssh[[:space:]]
#                           local-docker  → docker.*(exec|run)
#                           local-venv    → scripts/run\.sh
#                         无 exec-profile 字段时回退 remote-docker 默认(兼容旧 config)。

cfg="${CLAUDE_PROJECT_DIR:-$PWD}/.claude/research-bench.config.md"
[ -f "$cfg" ] || exit 0
# 只在 frontmatter(第一对 --- 之间)里读取 modules: 行,避免误读正文;剥掉行尾 # 注释再匹配
modules_line="$(awk '/^---[[:space:]]*$/{n++; next} n==1 && /^modules:/{print; exit} n>=2{exit}' "$cfg")"
modules_line="${modules_line%%#*}"
# 模块名 exec(注:子串匹配也涵盖 0.3.x 的旧模块名,以兼容旧 config)
printf '%s' "$modules_line" | grep -q 'exec' || exit 0

input="$(cat)"

# 解析 .tool_input.command:优先 jq,次选 python3;都没有才退回原始输入(可能误拦截,但避免漏拦训练命令)
if command -v jq >/dev/null 2>&1; then
  cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
elif command -v python3 >/dev/null 2>&1; then
  cmd="$(printf '%s' "$input" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except Exception: pass')"
else
  cmd="$input"
fi

# 训练特征(默认覆盖常见的 CLI/wrapper/smoke/eval 入口;按项目用 RW_TRAIN_PATTERNS 覆盖)
train_re="${RW_TRAIN_PATTERNS:---train|--do-train|train_wrapper\.py|smoke_test\.py|fit\.py}"

# 合法启动通道特征:env 优先;未设则按 frontmatter 的 exec-profile 取内置默认
if [ -n "${RW_EXEC_PATTERN:-}" ]; then
  exec_re="$RW_EXEC_PATTERN"
else
  profile="$(awk '/^---[[:space:]]*$/{n++; next} n==1 && /^exec-profile:/{sub(/^exec-profile:[[:space:]]*/,""); sub(/[[:space:]]*#.*$/,""); print; exit} n>=2{exit}' "$cfg")"
  case "$profile" in
    remote-venv)  exec_re='ssh[[:space:]]' ;;
    local-docker) exec_re='docker.*(exec|run)' ;;
    local-venv)   exec_re='scripts/run\.sh' ;;
    *)            exec_re='docker[[:space:]]+--context.*(exec|run)' ;;  # remote-docker 或无字段(兼容)
  esac
fi

if printf '%s' "$cmd" | grep -qE -e "$train_re"; then
  if ! printf '%s' "$cmd" | grep -qE -e "$exec_re"; then
    echo "阻止:检测到训练命令未走受控启动通道。训练必须走受控启动通道(匹配 /$exec_re/,由执行档案决定,见 config §7.1;如 docker --context <远程> exec …、ssh <远程> …、scripts/run.sh …)。" >&2
    exit 2
  fi
fi

exit 0
