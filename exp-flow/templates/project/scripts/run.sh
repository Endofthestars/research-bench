#!/usr/bin/env bash
# 骨架文件 | 模块:exec(仅 local-docker / local-venv 档案;init 定档为 local 时实例化到 scripts/run.sh)
# 契约角色:**local 档案的受控启动通道**——guard-train-channel hook 的 RW_EXEC_PATTERN
#   (local-venv 默认 `scripts/run\.sh`)匹配的就是本脚本:训练命令必须经它启动,直接启动会被拦。
#   它保证四件事:进入正确环境、注入 tracking/权重 env、后台启动 + 日志重定向、回显日志路径。
# 调用方:config §7.2 的 smoke / launch op 映射(operator 执行);用户直接启动训练时也应使用本脚本。
#
# 用法:
#   scripts/run.sh [--fg] <训练命令…>
#     默认**后台**启动(nohup + 日志重定向,不得前台阻塞正式训练);
#     --fg 前台执行并保留日志(smoke 等短任务用)。
# 实现可按项目调整,但启动通道、env 注入、日志记录和路径回显契约保持不变。
set -u

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"          # TODO:按项目定日志目录
mkdir -p "$LOG_DIR"

FG=0
[ "${1:-}" = "--fg" ] && { FG=1; shift; }
[ $# -ge 1 ] || { echo "用法:$0 [--fg] <训练命令…>" >&2; exit 64; }

# ---- 1. 进入环境(按执行档案保留对应分支;值见 config §5.2/§5.3)------------
# local-venv:激活 venv/conda
#   source "$PROJECT_ROOT/.venv/bin/activate"          # TODO:或 conda activate <env 名>
# local-docker:改为经容器执行(此时下方“启动”段的命令前缀应加 docker exec)
#   DOCKER_PREFIX="docker exec <容器名>"                # TODO:容器名见 config §5.2

# ---- 2. 注入 tracking / 权重 env(不通过训练命令联网下载权重;值见 config §8/§9,凭据从 .env 读取)----
# [ -f "$PROJECT_ROOT/.env" ] && set -a && . "$PROJECT_ROOT/.env" && set +a
# export MLFLOW_TRACKING_URI="<tracking 写入端点,config §9>"     # TODO
# export MODEL_WEIGHTS_PATH="<权重本地路径,config §8>"           # TODO
# export RW_GIT_HASH="$(git -C <SOURCE_DIR> rev-parse HEAD)"      # TODO:复现保真,主流程也会传入

# ---- 3. 启动:后台 + 日志重定向,回显日志路径 -----------------------------------
LOG_FILE="$LOG_DIR/run-$(date +%Y%m%d-%H%M%S)-$$.log"   # 加入 pid,避免同秒启动时文件名重复
if [ "$FG" -eq 1 ]; then
  "$@" 2>&1 | tee "$LOG_FILE"
  status=${PIPESTATUS[0]}
  echo "日志:$LOG_FILE"
  exit "$status"
else
  nohup "$@" >"$LOG_FILE" 2>&1 &
  echo "已后台启动(pid $!)"
  echo "日志:$LOG_FILE"
fi
