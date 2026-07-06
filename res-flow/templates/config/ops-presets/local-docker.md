<!-- ops 预设 | 档案:local-docker(本地 × docker)| init 装配时把下表嵌入 config §7.2
     (替换 OPS-PRESET 占位行)。表中 `<例:…>` 仍是占位,按项目填;命令形态按本档案给示意:
     代码就在本机(容器挂载/直读),无需同步 → sync-code 标 `不适用`(operator 跳过并在
     回执注明,不算失败;test-workflow ops 层判 SKIP)。 -->

| op | 轻重 | 项目命令/脚本 | 后置条件(operator 执行后验证) |
|---|---|---|---|
| sync-code | 重 | `不适用`(本地档案,代码经挂载直达容器,无需同步) | — |
| install-editable | 重 | `<例:scripts/ops/install-editable.sh(docker exec <容器> pip install -e <挂载的源码目录>)>` | `pip show` 可查到包 |
| pull-data | 重 | `<例:scripts/sync-datasets.sh(容器内 dvc pull,仅启用 data 模块时映射)>` | 挂载点目标数据存在 |
| smoke | 重 | `<例:scripts/ops/smoke.sh(docker exec 执行 §6 smoke 脚本,合成数据少量 epoch)>` | 退出码 0 + tracking 连通 |
| launch | 重 | `<例:scripts/ops/launch.sh <exp>(docker exec -d 后台启动 §6 训练封装,日志重定向)>` | 日志文件存在 + tracking 出现 run id |
| status | 轻 | `<例:scripts/ops/status.sh <exp>(tail 日志 + 查 tracking run 状态,只读)>` | — |
| collect | 轻 | `<例:experiments/collect_results.py(汇总完成的 run 进结果汇总表,幂等)>` | 汇总表出现对应行 |
