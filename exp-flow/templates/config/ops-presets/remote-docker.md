<!-- ops 预设 | 档案:remote-docker(远程 × docker)| init 装配时把下表嵌入 config §7.2
     (替换 OPS-PRESET 占位行)。表中 `<例:…>` 仍是占位,按项目填;命令形态按本档案给示意:
     同步靠 docker cp、执行经远程句柄 exec/run。 -->

| op | 轻重 | 项目命令/脚本 | 后置条件(operator 执行后验证) |
|---|---|---|---|
| sync-code | 重 | `<例:scripts/ops/sync-code.sh(docker cp 源码+experiments 到远程工作目录并 chown)>` | 远程目录时间戳更新 |
| install-editable | 重 | `<例:scripts/ops/install-editable.sh(远程句柄 exec -u root 容器内 pip install -e .)>` | `pip show` 可查到包 |
| pull-data | 重 | `<例:scripts/sync-datasets.sh(容器内 dvc pull,仅启用 data 模块时映射)>` | 挂载点目标数据存在 |
| smoke | 重 | `<例:scripts/ops/smoke.sh(远程句柄 exec 执行 §6 smoke 脚本,合成数据少量 epoch)>` | 退出码 0 + tracking 连通 |
| launch | 重 | `<例:scripts/ops/launch.sh <exp>(远程句柄 exec -d 后台启动 §6 训练封装,日志重定向)>` | 日志文件存在 + tracking 出现 run id |
| status | 轻 | `<例:scripts/ops/status.sh <exp>(tail 远程日志 + 查 tracking run 状态,只读)>` | — |
| collect | 轻 | `<例:experiments/collect_results.py(汇总完成的 run 进结果汇总表,幂等)>` | 汇总表出现对应行 |
