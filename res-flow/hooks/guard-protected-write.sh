#!/usr/bin/env bash
# PreToolUse hook(rf plugin):对敏感路径的写操作降级为"向用户请求确认"。
# 匹配 Edit|Write|MultiEdit(见 hooks.json)。两条规则,命中任一 → 输出 permissionDecision "ask"
# (不直接拒绝,由用户当场确认;字段名依官方 hooks 文档:hookSpecificOutput.permissionDecision/-Reason):
#   (a) 目标路径落在 config frontmatter `source-dir` 指定的模型源码根下(改源码须走 modify-architecture 规则);
#   (b) 目标是项目 .claude/settings.json 或 .claude/hooks/ 下文件(保护机制不可在未确认的情况下削弱)。
# config 不存在 → 静默放行(exit 0)。

proj="${CLAUDE_PROJECT_DIR:-$PWD}"
cfg="$proj/.claude/research-bench.config.md"
[ -f "$cfg" ] || exit 0

input="$(cat)"

# 解析 .tool_input.file_path(Edit/Write/MultiEdit 的文件路径字段,依官方文档):
# 优先 jq,次选 python3;都没有 → 无法可靠取路径,静默放行(本 hook 只降级不直接拒绝,漏拦截可接受)
if command -v jq >/dev/null 2>&1; then
  fp="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"
elif command -v python3 >/dev/null 2>&1; then
  fp="$(printf '%s' "$input" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))
except Exception: pass')"
else
  exit 0
fi
[ -n "$fp" ] || exit 0

# 相对路径按项目根解析;规范化(有 realpath -m 则使用,否则按原始路径前缀匹配)
case "$fp" in /*) : ;; *) fp="$proj/$fp" ;; esac
if command -v realpath >/dev/null 2>&1; then
  fp="$(realpath -m -- "$fp" 2>/dev/null || printf '%s' "$fp")"
  proj="$(realpath -m -- "$proj" 2>/dev/null || printf '%s' "$proj")"
fi

ask() { # $1=展示给用户与 Claude 的原因
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

# 规则 (b):保护机制自身
case "$fp" in
  "$proj/.claude/settings.json")
    ask "rf 保护机制:要写 .claude/settings.json(permission/hook env 所在)。该操作可能影响保护机制,请确认。" ;;
  "$proj/.claude/hooks/"*)
    ask "rf 保护机制:要写 .claude/hooks/ 下文件。该操作可能影响保护机制,请确认。" ;;
esac

# 规则 (a):模型源码根(frontmatter 的 source-dir;取第一对 --- 之间的行,剥注释/引号/尾斜杠)
src="$(awk '/^---[[:space:]]*$/{n++; next} n==1 && /^source-dir:/{sub(/^source-dir:[[:space:]]*/,""); sub(/[[:space:]]*#.*$/,""); print; exit} n>=2{exit}' "$cfg")"
src="${src%\"}"; src="${src#\"}"; src="${src%/}"
# 未填或仍是占位(含 <)→ 跳过规则 (a)
if [ -n "$src" ] && ! printf '%s' "$src" | grep -q '<'; then
  case "$src" in /*) src_abs="$src" ;; *) src_abs="$proj/$src" ;; esac
  case "$fp" in
    "$src_abs"/*|"$src_abs")
      ask "rf 保护机制:目标在模型源码根($src)下。改源码须走 modify-architecture 规则(flag 可开关、验权重加载),请确认。" ;;
  esac
fi

exit 0
