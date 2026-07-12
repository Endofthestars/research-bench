<!-- 模块:exec | 吸收段:§5 执行环境、§6 实验脚手架、§7 保护机制 + ops 映射表
     依赖它的 skill/agent:build-env(仅 docker 运行时)、deploy-env(仅 remote-docker)、
     run-experiment、operator 服务;guard-train-channel hook 据 manifest 是否含 exec 决定启停,
     据 frontmatter 的 exec-profile 取默认通道模式(RW_EXEC_PATTERN 未设时)。
     装配:init 两问确定档案(位置 local|remote × 运行时 docker|venv)后，§5 按档案适用性裁剪小节;
     §7.2 嵌入 templates/config/ops-presets/<exec-profile>.md 对应预设;local 两档案实例化
     scripts/run.sh 受控启动器;启用本模块时还会实例化 scripts/test-workflow.sh
     (guards 层可直接使用,ops 层对 §7 映射做 dry-run 断言)。 -->

## 5. 执行环境(run-experiment / build-env / deploy-env / operator 用)

### 5.0 档案声明与通用项(全部档案)
- 执行档案:`<remote-docker | remote-venv | local-docker | local-venv>`(与顶部 frontmatter 的
  `exec-profile` 保持一致;位置表示训练执行位置,运行时表示环境管理方式)
- **不变量(四档案同一条)**:训练必须走**受控启动通道**——remote-docker = 远程句柄 exec/run、
  remote-venv = ssh、local-docker = docker exec/run、local-venv = `scripts/run.sh` 启动器
  (local 两档案由 init 实例化 `scripts/run.sh` 骨架,见 §7.1);直接启动训练会被 guard 拦。
- 工作目录:`<例:${WORK_HOME}/mymodel-dev(remote 档案指远程机上的目录,local 档案指本机目录)>`
- 运行用户 uid:gid 约定:`<例:1000:1000(youruser),非 root;docker cp / 写文件后须
  chown -R 1000:1000 <工作目录>>`(不适用时删除;local-venv 通常不需要)
- python/pip pin:`<例:环境内均用 <环境 python> -m pip,避免宿主 miniconda 影响>`(不适用时删除)

### 5.1 远程句柄(仅 remote-* 档案;local 档案删本节)
- 远程句柄:`<例:remote-docker → docker context `node19`(无 SSH、只有 docker socket,代码同步靠
  docker cp);remote-venv → ssh youruser@node19(代码同步靠 rsync/scp)>`
- 本地 build 句柄(仅 remote-docker):`<例:docker --context default(本地网络较稳定,不在远程构建)>`
- `REMOTE_HOME`:`<例:/public/home/youruser>`

### 5.2 镜像分层(仅 *-docker 档案;venv 档案删本节)
| 镜像 | 角色 | FROM |
|---|---|---|
| `<例:mymodel-base>` | 底座:CUDA/py/torch/依赖,依赖变才重建 | — |
| `<例:mymodel-dev>` | 开发 / smoke | base |
| `<例:mymodel-run>` | 正式训练 | base |
- 约定:镜像只包含运行环境,模型源码不写入镜像,运行时同步源码 + `pip install -e .`
- build/deploy 脚本:`<例:scripts/deploy-env.sh(build <layer> / push <layer> / all;push 仅
  remote-docker 有意义)>`

### 5.3 venv/conda 环境(仅 *-venv 档案;docker 档案删本节)
- 环境类型与激活方式:`<例:.venv → source .venv/bin/activate;或 conda → conda activate mymodel>`
- 环境定义文件:`<例:requirements.txt / environment.yml / pyproject.toml(uv)>`
- 环境重建命令:`<例:python -m venv .venv && .venv/bin/pip install -r requirements.txt>`
  (remote-venv 在远程机上执行,经 ssh)

## 6. 实验脚手架(run-experiment / operator 用)
- smoke test:`<例:experiments/smoke_test.py(合成数据 2 epoch,含 tracking 连通自检)>`
- 训练封装入口:`<例:experiments/train_wrapper.py --config <yaml>>`
- config 模板:`<例:experiments/config_smoke.yaml(flags:{} = baseline,复制改 flags/超参)>`
- 选卡:`<例:experiments/gpu_select.py 自动选最空卡,config model.gpu_id 可固定>`
- 复现固定项:`<例:固定 seed、torch.use_deterministic_algorithms(True)、cudnn deterministic>`

## 7. 保护机制与 ops 映射表(guard-train-channel hook / operator / test-workflow 用)

### 7.1 保护机制(guard-train-channel hook 用)
- **严禁直接启动的训练命令特征**(出现即拦,除非走受控启动通道):
  `<例:--train | train_loop | train_wrapper.py | smoke_test.py | eval.py>`
- **合法启动通道特征**(命令含此模式才放行;语义:本档案的受控启动通道形式):
  `<例:remote-docker → docker --context <远程> exec/run;remote-venv → ssh <远程> …;
  local-docker → docker exec/run;local-venv → scripts/run.sh …>`
- 这两组值同时要写进项目 `.claude/settings.json` 的 `"env"`(`RW_TRAIN_PATTERNS` / `RW_EXEC_PATTERN`,
  见 plugin `hooks/guard-train-channel.sh` 头注释;可用 `rf:config set env.*` 经确认后代写,
  Claude Code 中调用名带前导 `/`);
  hook 只认 env,不解析本段散文——**env 未设时** hook 按 frontmatter 的 `exec-profile` 取内置默认通道模式。
- guard 回归测试:`scripts/test-workflow.sh guards`(init 实例化,固定子命令契约,见 §11 / 脚本头注释)。
- 保护机制对 **operator 服务同样生效**:operator 的每条 Bash 命令照样过 guard,不得规避。

### 7.2 ops 映射表(operator 的 ISA;test-workflow `ops` 层据此 dry-run 断言)
> 七个 op 是固定指令集,**operator 只许组合它们**,保持最小集合。每行把「项目命令/脚本」填成
> 本项目的具体实现;含 `<占位>` 的行视为**未映射**,operator 遇到会拒绝执行并指回这里。
> 标 **`不适用`** 的行是当前执行档案没有的动作(如 local 档案的 sync-code):operator 遇到
> **跳过并在回执注明**,不算失败。关键 op 必须经 operator;轻 op(status / collect,只读或幂等)
> 允许主流程直接执行(照样受 guard 管)。

<!-- OPS-PRESET:init 装配时按 exec-profile 用 templates/config/ops-presets/<档案>.md 的映射表
     替换下面这行占位;人工装配时复制对应预设表到此处。 -->
`<ops 映射表:按执行档案嵌入 templates/config/ops-presets/<exec-profile>.md 的预设表>`

- **敏感 env 名清单**(operator 回执脱敏依据:命令里这些变量的**值**替换为 `***`,变量名保留):
  `<例:MLFLOW_TRACKING_PASSWORD、AWS_SECRET_ACCESS_KEY、AWS_ACCESS_KEY_ID>`

### 7.3 租约互斥(防 sync/install 打断在启动训练)
- **launch 成功后**,operator 在工作目录(§5.0;remote 档案在远程机上)写租约文件:`<例:.rw-lease-<exp>>`,
  内容三行:exp 名 + tracking run id + 启动时间戳。
- **sync-code / install-editable 执行前**先查租约(该 op 于当前档案标「不适用」则整步自然缺席):
  发现活跃训练(租约存在且对应 run 仍在执行)→ **停止并带现场返回主流程**(租约内容 + run 状态),
  由用户决定等待/中止/强行,operator 不得擅自选择。
- 训练确认结束后,在 status / collect 时机**清理租约**(先核对 run 已终态再删)。
