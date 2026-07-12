#!/usr/bin/env bash
# 将 shared/ 渲染到 plugins/rf/ (P=rf) 与 plugins/ef/ (P=ef)。
# shared/ 是两插件共有文件的唯一事实来源;插件目录内的对应副本是生成物,不要手改。
# 用法:
#   scripts/sync-shared.sh          渲染并覆盖两插件内的副本
#   scripts/sync-shared.sh --check  只校验是否漂移(CI/审计用),漂移则退出码 1
set -euo pipefail
cd "$(dirname "$0")/.."

CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

status=0
while IFS= read -r -d '' src; do
  rel="${src#shared/}"
  for pair in "rf:plugins/rf" "ef:plugins/ef"; do
    P="${pair%%:*}" dir="${pair#*:}"
    dest="$dir/$rel"
    rendered="$(sed "s/{{P}}/$P/g" "$src")"
    if [ "$CHECK" = 1 ]; then
      if [ ! -f "$dest" ] || [ "$rendered" != "$(cat "$dest")" ]; then
        echo "DRIFT: $dest 与 shared/$rel 不一致" >&2
        status=1
      fi
    else
      mkdir -p "$(dirname "$dest")"
      printf '%s\n' "$rendered" > "$dest"
      [ -x "$src" ] && chmod +x "$dest"
    fi
  done
done < <(find shared -type f -print0)

if [ "$CHECK" = 1 ]; then
  [ "$status" = 0 ] && echo "OK: 所有共享文件与 shared/ 一致"
  exit "$status"
fi
echo "已从 shared/ 渲染到 plugins/rf/ 与 plugins/ef/"
