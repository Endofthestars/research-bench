<!-- ops 预设 | 档案:remote-venv(远程 × venv)| init 装配时把下表嵌入 config §7.2
     (替换 OPS-PRESET 占位行)。表中 `<例:…>` 仍是占位,按项目填;命令形态按本档案给示意:
     同步靠 rsync/scp、执行经 ssh + venv/conda 激活(激活方式见 §5.3)。 -->

| op | 轻重 | 项目命令/脚本 | 后置条件(operator 执行后验证) |
|---|---|---|---|
| sync-code | 重 | `<例:scripts/ops/sync-code.sh(rsync 源码+experiments 到 ssh <远程>:<工作目录>)>` | 远程目录时间戳更新 |
| install-editable | 重 | `<例:scripts/ops/install-editable.sh(ssh <远程> "source .venv/bin/activate && pip install -e <工作目录>")>` | `pip show` 可查到包 |
| pull-data | 重 | `<例:scripts/sync-datasets.sh(ssh <远程> "cd <工作目录> && dvc pull",仅启用 data 模块时映射)>` | 目标数据存在 |
| smoke | 重 | `<例:scripts/ops/smoke.sh(ssh <远程> "source .venv/bin/activate && python experiments/smoke_test.py")>` | 退出码 0 + tracking 连通 |
| launch | 重 | `<例:scripts/ops/launch.sh <exp>(ssh <远程> "… nohup <§6 训练封装> > logs/<exp>.log 2>&1 &" 后台)>` | 日志文件存在 + tracking 出现 run id |
| status | 轻 | `<例:scripts/ops/status.sh <exp>(ssh <远程> "tail logs/<exp>.log" + 查 tracking run 状态,只读)>` | — |
| collect | 轻 | `<例:experiments/collect_results.py(汇总完成的 run 进结果汇总表,幂等)>` | 汇总表出现对应行 |
