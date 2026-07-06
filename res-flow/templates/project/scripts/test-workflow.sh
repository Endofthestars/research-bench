#!/usr/bin/env bash
# 骨架文件 | 模块:maintenance(guards / ops 层同时服务 exec 模块的保护机制回归与 ISA 映射核对)
# init 实例化到 config §11「确定性测试脚本」指定的路径(约定 scripts/test-workflow.sh)。
# 调用方:test-workflow skill 调用并解读 ✅/❌;init 收尾校验实际运行 `guards` 层;
#         steward / audit-workflow 的 C9 检查项调用 `ops` 层。
#
# 接口契约(固定,不可改名;实现随项目换):
#   test-workflow.sh guards        —— 保护机制断言(本地秒级,可直接使用)
#   test-workflow.sh sanity        —— 本地健康检查(语法/构建文件/py/yaml;TODO 按项目实现)
#   test-workflow.sh ops           —— ISA 映射 dry-run 断言(config §7.2 每个 op:映射非占位、
#                                     引用的脚本存在且可执行;不得实际执行训练;可直接使用);
#                                     追加:manifest 含 discovery 时,断言方向 dossier 的
#                                     gates.jsonl 行行是合法 JSON(不含则 SKIP)
#   test-workflow.sh connectivity  —— 远程只读探测(访问远程;TODO 按项目实现)
#   test-workflow.sh all           —— 只执行本地层 guards+sanity+ops(connectivity 必须显式单独执行)
# 输出:逐项 ✅/❌/⚠️SKIP + 末尾汇总;退出码 0 = 全过,非 0 = 有失败。判对错的是本脚本,skill 只解读。
set -u

# ---- 定位 plugin 的 guard 脚本 -------------------------------------------
# __PLUGIN_ROOT__ 由 init 实例化时替换为实际插件根(${CLAUDE_PLUGIN_ROOT});
# 也可用环境变量 RW_PLUGIN_ROOT 覆盖(插件搬家/多版本时)。
PLUGIN_ROOT="${RW_PLUGIN_ROOT:-__PLUGIN_ROOT__}"
if [ ! -f "$PLUGIN_ROOT/hooks/guard-train-channel.sh" ]; then
  # 保障:在常见插件安装目录里搜(占位未被替换、或插件被移动时)
  for cand in "$HOME"/.claude/plugins/*/ef/ "$HOME"/.claude/plugins/ef/ \
              "$HOME"/.claude/plugins/*/exp-flow/ "$HOME"/.claude/plugins/exp-flow/; do
    [ -f "${cand}hooks/guard-train-channel.sh" ] && PLUGIN_ROOT="${cand%/}" && break
  done
fi
GUARD="$PLUGIN_ROOT/hooks/guard-train-channel.sh"

# 项目根:guard 会读 ${CLAUDE_PROJECT_DIR}/.claude/research-bench.config.md 的 manifest
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CLAUDE_PROJECT_DIR="$PROJECT_ROOT"
CFG="$PROJECT_ROOT/.claude/research-bench.config.md"

PASS=0; FAIL=0; SKIP=0

ok()   { echo "✅ $1"; PASS=$((PASS+1)); }
bad()  { echo "❌ $1"; FAIL=$((FAIL+1)); }
skip() { echo "⚠️SKIP $1"; SKIP=$((SKIP+1)); }

# 读 frontmatter 的 modules: 行(第一对 --- 之间,剥行尾注释)
manifest_modules() {
  awk '/^---[[:space:]]*$/{n++; next} n==1 && /^modules:/{sub(/#.*/,""); print; exit} n>=2{exit}' "$CFG" 2>/dev/null
}

# 构造 PreToolUse 的假 stdin JSON(与 Claude Code 真实喂给 hook 的形态一致)喂给 guard,断言退出码。
assert_guard() { # $1=描述 $2=期望退出码 $3=命令串
  printf '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"%s"}}' "$3" \
    | bash "$GUARD" >/dev/null 2>&1
  actual=$?
  if [ "$actual" -eq "$2" ]; then ok "$1"; else bad "$1(期望退出码 $2,实际 $actual)"; fi
}

run_guards() {
  echo "== guards:保护机制断言(guard-train-channel.sh)=="
  if [ ! -f "$GUARD" ]; then
    skip "找不到 guard 脚本($GUARD);设 RW_PLUGIN_ROOT 后重试"
    return
  fi
  # 用固定模式测 guard 的机制(解析 stdin → 匹配 → 拦/放 → 模块门控),保证确定性;
  # 项目真实模式在 .claude/settings.json 的 env 里(未设时 guard 按 exec-profile 取默认),本测试不依赖它。
  export RW_TRAIN_PATTERNS='--train|train_wrapper\.py|smoke_test\.py'
  export RW_EXEC_PATTERN='docker[[:space:]]+--context.*(exec|run)'

  # 三类断言(注意:若 config 的 modules 不含 exec,guard 静默放行是**正确行为**,
  # 此时第一条会拿到 0——脚本先探测模块门控再定期望值)
  if manifest_modules | grep -q 'exec'; then
    expect_block=2
  else
    echo "   (config 未启用 exec 模块 → guard 应全放行)"
    expect_block=0
  fi
  assert_guard "直接启动训练命令被拦(未走受控启动通道)" "$expect_block" \
    "python experiments/train_wrapper.py --config experiments/config_smoke.yaml"
  assert_guard "走受控启动通道的训练命令放行" 0 \
    "docker --context node19 exec -d dev python experiments/train_wrapper.py --config c.yaml"
  assert_guard "无关命令放行" 0 \
    "ls -la scripts/"
  unset RW_TRAIN_PATTERNS RW_EXEC_PATTERN
}

run_sanity() {
  echo "== sanity:本地健康检查 =="
  # TODO(按项目实现):契约——只做本地静态检查,秒级完成,不修改远程环境。建议项:
  #   bash -n scripts/*.sh                     # 脚本语法
  #   python -m py_compile experiments/*.py    # py 语法
  #   python -c 'import yaml,sys; yaml.safe_load(open(sys.argv[1]))' experiments/config_smoke.yaml
  #   docker build --check / hadolint          # 构建文件
  skip "sanity 层未实现(TODO:见脚本内注释)"
}

run_ops() {
  echo "== ops:ISA 映射 dry-run 断言(config §7.2;不实际执行任何 op)=="
  if [ ! -f "$CFG" ]; then
    skip "无 config($CFG);先执行 /rf:init"
    return
  fi
  if ! manifest_modules | grep -q 'exec'; then
    skip "config 未启用 exec 模块,§7.2 ops 映射表不存在"
    return
  fi
  has_data=0
  manifest_modules | grep -q 'data' && has_data=1

  for op in sync-code install-editable pull-data smoke launch status collect; do
    # 取 §7.2 表中该 op 的行(形如 | <op> | 轻/重 | <命令/脚本> | <后置条件> |)
    row="$(grep -E "^\|[[:space:]]*${op}[[:space:]]*\|" "$CFG" | head -1)"
    if [ -z "$row" ]; then
      bad "op ${op}:§7.2 映射表缺该行(operator 将拒绝执行)"
      continue
    fi
    # 第 3 列 = 项目命令/脚本;剥反引号与首尾空白
    cell="$(printf '%s' "$row" | awk -F'|' '{print $4}' | sed 's/`//g; s/^[[:space:]]*//; s/[[:space:]]*$//')"
    if [ "$op" = "pull-data" ] && [ "$has_data" -eq 0 ]; then
      skip "op pull-data:未启用 data 模块,允许不映射"
      continue
    fi
    # 标「不适用」的 op = 当前执行档案没有的动作(如 local 档案的 sync-code),SKIP 非失败
    case "$cell" in
      不适用*)
        skip "op ${op}:当前执行档案不适用(operator 会跳过并在回执注明)"
        continue ;;
    esac
    case "$cell" in
      *'<'*|"")
        bad "op ${op}:映射含占位或为空(operator 将拒绝执行;补 config §7.2 该行)"
        continue ;;
    esac
    # 取第一个 token 当作脚本/命令;dry-run 只验证存在性与可执行性,不得运行
    tok="${cell%% *}"
    case "$tok" in
      */*)
        p="$tok"; case "$p" in /*) : ;; *) p="$PROJECT_ROOT/$p" ;; esac
        if [ ! -f "$p" ]; then
          bad "op ${op}:引用的脚本不存在($tok)"
        elif [ "${p##*.}" = "sh" ] && [ ! -x "$p" ]; then
          bad "op ${op}:脚本存在但无执行位($tok;chmod +x)"
        else
          ok "op ${op}:已映射,脚本就位($tok)"
        fi ;;
      *)
        if command -v "$tok" >/dev/null 2>&1; then
          ok "op ${op}:已映射,命令可用($tok)"
        else
          bad "op ${op}:映射的命令不在 PATH($tok)"
        fi ;;
    esac
  done
}

run_ops_gates() {
  echo "== ops(gates):方向 dossier 的 gates.jsonl 逐行 JSON 断言(config §12;不实际执行任何 op)=="
  if [ ! -f "$CFG" ]; then
    skip "无 config($CFG);先执行 /rf:init"
    return
  fi
  if ! manifest_modules | grep -q 'discovery'; then
    skip "config 未启用 discovery 模块,无 gates.jsonl 契约"
    return
  fi
  # 校验器:python3 优先,次选 jq;二者都不在则 SKIP
  if command -v python3 >/dev/null 2>&1; then
    validate_jsonl() {
      python3 -c '
import json, sys
ok = True
for i, line in enumerate(open(sys.argv[1]), 1):
    line = line.strip()
    if not line:
        continue
    try:
        json.loads(line)
    except ValueError:
        print("  行 %d 非法 JSON" % i)
        ok = False
sys.exit(0 if ok else 1)' "$1"
    }
  elif command -v jq >/dev/null 2>&1; then
    validate_jsonl() { jq -s '.' "$1" >/dev/null 2>&1; }
  else
    skip "python3 与 jq 均不可用,无法校验 gates.jsonl"
    return
  fi
  # 方向目录:约定 docs/directions(即 config §10 的方向文件目录;路径不同用 RW_DIRECTIONS_DIR 覆盖)
  dir_root="${RW_DIRECTIONS_DIR:-$PROJECT_ROOT/docs/directions}"
  if [ ! -d "$dir_root" ]; then
    skip "方向目录不存在($dir_root;路径不同可设 RW_DIRECTIONS_DIR)"
    return
  fi
  found=0
  for f in "$dir_root"/*/gates.jsonl; do
    [ -f "$f" ] || continue
    found=1
    slug="$(basename "$(dirname "$f")")"
    if validate_jsonl "$f"; then
      ok "gates:${slug}/gates.jsonl 行行是合法 JSON"
    else
      bad "gates:${slug}/gates.jsonl 含非法 JSON 行(关卡账本被破坏,select_direction 将无法机械判读)"
    fi
  done
  [ "$found" -eq 0 ] && skip "方向目录下暂无 gates.jsonl(尚无 dossier 或关卡未产出)"
}

run_connectivity() {
  echo "== connectivity:远程只读探测 =="
  # TODO(按项目实现):契约——**只读**,不得启动训练、不写跟踪系统。建议项:
  #   <远程句柄> info                          # 远程 daemon 健康检查
  #   <远程句柄> images | grep <镜像名前缀>     # 镜像到位
  #   curl -sf <tracking 端点>/health           # 跟踪服务健康检查(需先 source .env)
  skip "connectivity 层未实现(TODO:见脚本内注释)"
}

case "${1:-all}" in
  guards)        run_guards ;;
  sanity)        run_sanity ;;
  ops)           run_ops; run_ops_gates ;;
  connectivity)  run_connectivity ;;
  all)           run_guards; run_sanity; run_ops; run_ops_gates ;;   # all 只含本地层;connectivity 必须显式单独执行
  *) echo "用法:$0 {guards|sanity|connectivity|ops|all}" >&2; exit 64 ;;
esac

echo "---- 汇总:✅ $PASS ❌ $FAIL ⚠️SKIP $SKIP ----"
[ "$FAIL" -eq 0 ]
