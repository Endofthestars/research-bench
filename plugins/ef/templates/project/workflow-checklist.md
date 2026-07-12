<!-- 骨架文件 | 模块:maintenance | init 实例化到 config §11「一致性检查清单」指定的路径
     调用方:audit-workflow(清单模式)逐条核对(唯一判据来源);update-workflow(steward)改完按本清单自检。
     接口契约:检查项编号 C1…Cn 是 audit 报告的引用锚点;每条含「查什么/怎么查」两栏。
     下面 10 条是通用起步项,按项目增删改;改本文件 = 改检查标准,受 update-workflow 规则 3 保护。 -->

# 工作流一致性检查清单

| 编号 | 查什么 | 怎么查 |
|---|---|---|
| C1 | config 已启用段落无 `<占位>` 残留 | `grep -n '<占位\|<例:' .claude/research-bench.config.md`(示例说明行除外) |
| C2 | config frontmatter 与正文一致:`source-dir` == §2 `SOURCE_DIR`;`modules` 与实际存在的 § 段一一对应;`exec-profile` == §5.0 档案声明(启用 exec 时) | 目测比对 frontmatter 与正文各 § 标题、§5.0 |
| C3 | 提示词/文档引用的源文件名与 `SOURCE_DIR` 实际文件一致 | 对 §2 表格里每个文件 `ls <SOURCE_DIR>/<文件>` |
| C4 | 镜像名/脚本名与容器构建文件、`scripts/` 实际一致(docker 运行时档案;venv 档案查 §5.3 环境定义文件) | `grep -rn '<镜像名>' scripts/ docker/` 对照 §5.2 镜像表 |
| C5 | hook 拦截模式覆盖所有训练入口:§7.1 列出的每个训练特征都能被 `RW_TRAIN_PATTERNS` 匹配,受控启动通道模式与档案一致 | 执行 `scripts/test-workflow.sh guards`;新增训练入口后人工比对 §7.1 与 settings.json env(`RW_TRAIN_PATTERNS` / `RW_EXEC_PATTERN`) |
| C6 | 路径/执行句柄一致:工作目录、权重路径、挂载点、远程句柄(remote 档案)与 run/deploy 脚本一致 | `grep -rn '<执行句柄>\|<工作目录>' scripts/` 对照 §5 |
| C7 | 方向注册表与方向 dossier 不漂移:注册表每行的状态 == 对应 dossier 的 `direction.md`「状态」;方向 dossier 都已登记(启用 directions 时) | 逐行比对注册表与 `<方向文件目录>/*/direction.md` |
| C8 | README 结构树(结构索引)与实际目录一致 | `ls` 实际结构对照 README 结构树段 |
| C9 | 每个 ISA op 在 §7.2 有映射且引用的脚本存在可执行(启用 exec 时;否则不适用;映射标「不适用」的 op 计 SKIP 非失败) | 执行 `scripts/test-workflow.sh ops`(dry-run,不实际执行) |
| C10 | 方向 dossier 的 `gates.jsonl` 可被机器读取(启用 discovery 时;无 dossier 时可 SKIP) | 执行 `scripts/test-workflow.sh ops`,查看 gates JSONL 校验项 |
| C11 | agent 记忆目录不含应进 config/文档的事实(memory: project 的记忆是项目内文件,本项审得到):architect / steward 的记忆只应有"指向文档的索引 + 工作偏好" | 读 `.claude/` 下 agent 记忆目录(如 `.claude/agent-memory/*/`),抽查条目——路径/端点/架构结论等事实类内容应指向 config §/文档,不应内联;发现内联事实 → 移进 config/文档并把记忆改成索引 |
