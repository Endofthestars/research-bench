# Changelog

## rf 0.1.1 / ef 0.1.1(未发布)

### 新增
- **`settings` 交互式设置面板(rf、ef 共享 skill)**:体验对标 Claude Code 内置 `/config`——
  `AskUserQuestion` 菜单逐层选择「配置段 → 键 → 新值」,主菜单按 manifest 只列已启用模块的段,
  支持 `settings <段号|关键词|env>` 直达;写入规则与 `config` 完全同源(逐值确认、`env.RW_*`
  特例、`source-dir` 双处同步),`modules`/`exec-profile` 修改仍转介 `init`。
  与 `config` 分工:`config` 面向"知道键名"的定点命令式调用,`settings` 面向"浏览着改"。
- **shared/ 单一事实来源**:rf、ef 共有的 30 个文件(公共 skill/command、operator/steward agent、
  session-init-check hook、全部 templates)抽取到顶层 `shared/`,文内插件前缀以 `{{P}}` 占位;
  `scripts/sync-shared.sh` 渲染进两个插件目录,`--check` 模式校验漂移。
  插件内的对应副本自此为生成物,改共享内容只改 `shared/` 再同步,消除双份手工维护。
  插件安装物不变(仍是两棵自包含目录树)。
- **仓库开发工具(`.claude/`,不随插件分发)**:3 个 agent(plugin-dev 插件开发、service-dev
  remote-control 服务开发、consistency-auditor 只读全仓一致性审计)+ 3 个 skill
  (`/add-capability` 新增能力脚手架、`/sync-shared` 共享内容同步、`/release` 发版流程)。
- **commands/ 显式命令入口**:每个 skill 增加一份同名的 `commands/<skill>.md` 薄壳
  (内容仅为"按对应 SKILL.md 执行"),与 skill 走同一命名空间(`/rf:<name>`、`/ef:<name>`)。
  目的:部分 Claude Code 版本对插件 skill 的斜杠补全不完整,commands 注册路径的补全更可靠;
  同名共存实测无冲突,skill 的 `disable-model-invocation` 门控不受影响。
  (与 0.5.1 被废弃的 `commands/rf-*` 伪前缀方案不同:本次命名空间来自插件自身的 `name`,
  commands 只是同名的第二注册路径,不承担命名职责。)

### 修复
- **README 本地安装方法**:原文档给出的 `.claude/settings.json` `"plugins": [路径]` 写法并非
  Claude Code 支持的机制,按其操作插件不会被加载(`/init` 会命中内置命令而非 `/rf:init`)。
  改为官方支持的两种方式:本地目录 `marketplace add` 后安装,或 `claude --plugin-dir` 按次加载。

### 文档
- README 新增「Skill 参考」一节:14 个 skill 的功能、模块依赖、执行方式与适用场景的规范说明,
  后续章节顺延编号。
- 命名统一为 `rf`(Research Flow,研究流程插件)与 `ef`(Experiment Flow,实验流程插件);
  源码目录同步调整为 `res-flow/` 与 `exp-flow/`。

## Unreleased

### 新增
- **remote-control**:新增可选的自建远程触发/监控服务,包含 FastAPI 后端、静态 Web/PWA 面板、
  systemd/Caddy/Docker 部署材料和安全说明。它不是 Claude Code 插件,而是 research-bench 的远程
  操作配套服务。

### 文档
- 更新项目描述:当前仓库定位为 `rf`(Research Flow)插件、`ef`(Experiment Flow)插件和 `remote-control` 可选服务
  组成的工作流套件,而不是单一 `research-bench` 插件。
- 仓库/marketplace 品牌名统一为 `research-bench`(简称 `rb`)。

## [BREAKING] rf 0.1.0 / ef 0.1.0(2026-07)—— 拆分为两个真实插件,仓库更名 research-bench

### 设计总纲
0.5.1 用 `commands/lf-*` / `commands/rf-*` 伪装出来的短前缀,本质仍是单一插件
`research-bench` 里的短横线文件名,不是真正的 Claude Code 命名空间。经查证官方文档确认:
冒号前的命名空间(`/plugin:skill`)只能来自插件自身 `plugin.json` 的 `name`,一个插件不能对外
暴露两个命名空间。因此本次废弃 0.5.1 的别名方案,**把仓库拆成两个真正独立、各自可安装的插件**:

- **`rf`**(Research Flow):`analyze-architecture`、`modify-architecture`、`propose-hypothesis`、
  `refine-direction`、`check-novelty`、`audit-results`,命名空间 `/rf:<skill>`。
- **`ef`**(Experiment Flow):`build-env`、`deploy-env`、`run-experiment`、`test-workflow`,命名空间
  `/ef:<skill>`。
- 共享基座 `init`/`config`/`update-workflow`/`audit-workflow` 在两个插件里各留一份完整复制
  (内容按各自命名空间改写自引用前缀,行为等价,不是裁剪版)。
- 仓库/marketplace 品牌名改为 `research-bench`(简称 `rb`),它本身不是插件,只是文档/仓库层面的
  总名字。

### 不兼容变更
- 旧的单插件安装方式 `research-bench@research-bench` 和 `/research-bench:<skill>` 调用
  语法**不再存在**,改为分别安装 `rf@research-bench`、`ef@research-bench`,调用改为 `/rf:<skill>` /
  `/ef:<skill>`。
- 删除 `commands/` 目录(18 个 0.5.1 引入的短横线别名文件),被真正的插件命名空间取代。
- `rf`、`ef` 作为全新的可安装身份,版本号从 `0.1.0` 起算,不延续旧插件的 `0.5.1`。

### 权衡与已接受的代价
- **hook 按插件重新分配、不是全量复制**:`guard-protected-write`(源码写保护)只在 `rf`;
  `guard-train-channel`(训练启动通道保护)只在 `ef`;`session-init-check` 两边都有。只装一个插件
  时会有对应的保护机制缺口,正常使用预期两个插件一起装。
- **共享内容用真实文件复制,不用符号链接**:公开分发的插件仓库在 Windows 上克隆时符号链接可能
  签出成纯文本文件而不是真目录,存在静默失效风险;改为接受维护漂移的代价换取跨平台可靠性。
- 两个插件都装时,`session-init-check` 会重复触发(只读、幂等,可接受的噪音);`init` 等共享 skill
  会在两个命名空间下各出现一次(预期行为,不是 bug)。

## 0.5.1(2026-07)—— 命令 namespace:`lf` / `rf`

### 设计总纲
参考 `academic-research-skills`(Imbad0202)的实现方式:插件全名(`research-bench`)和 skill 名保持不变,
新增 `commands/` 目录,为每个 skill 生成一个薄封装命令,提供比 `research-bench:<skill>` 更短的调用
别名。短别名按**执行 vs 研究方向**分成两组 namespace(而非拆成两个独立插件,避免拆散共享的
agents/hooks/config manifest),不引入新的语义或职责边界。

### 新增
- **执行流程(`lf-*`)**:`build-env`、`deploy-env`、`run-experiment`、`test-workflow`。
- **研究流程(`rf-*`)**:`analyze-architecture`、`modify-architecture`、
  `propose-hypothesis`、`refine-direction`、`check-novelty`、`audit-results`。
- **公共基座(两组都有)**:`init`、`config`、`update-workflow`、`audit-workflow` 各自在
  `lf-*` 和 `rf-*` 下都有等价命令,可从任一 namespace 触达。
- 每个命令只做一件事——调用同名 skill,并透传 `$ARGUMENTS`。
- README 新增「简写命令」一节说明两套 namespace 的范围,目录结构补充 `commands/` 一节。

## 0.5.0(2026-07)—— discovery 模块:方向发现关卡链(P0+P1 批次)

### 设计总纲
方向链路从**登记制**转向**关卡制**(docs/PROPOSAL-direction-first.md):新方向进注册表前须过三关——
`check-novelty` 查新(关卡 1)→ pilot 试点(关卡 2,本批次由人工判定)→ `reviewer` 对抗审查(关卡 3),
关卡裁决写入方向 dossier 的 `gates.jsonl`(追加式 JSONL,脚本可机械判读)。审查者与账本权力分离:
reviewer **能「否」不能「准」**、无写工具,裁决文本交回主流程,登记注册表仍需 update-workflow + 用户确认。
本批次实施 P0+P1;pilot 执行约定 / select_direction 契约扩展 / claims 投稿缺口报告 /
survey-literature / close-direction 属后续批次(P2–P4)。

### 新增
- **模块 `discovery`(第 7 个模块)+ `templates/config/60-discovery.md`(配置 §12,锚点不重排)**:
  §12.1 Zotero MCP 端点与集合约定(`directions/<slug>` 每方向一集合,导入即验证);
  §12.2 Codex 通道(主流程调用后传给 reviewer 合并;未配置降级独立 agent 冷上下文审查);§12.3 pilot 预算 env
  (如 PILOT_MAX_HOURS / MAX_TOTAL_GPU_HOURS,由项目训练封装读取,启用 exec 时登记进 §7.2);
  §12.4 查新参数(检索源清单 / 近月窗口 / 新颖性分级门槛 / review 分数线,默认 ≥8/10 可配)。
  两条保护条款写入本段:阈值修改属削弱检查标准,须显式说明并经用户确认;
  关卡与档位正交——auto/loop 档跳关必须留 gates.jsonl 的 skip 记录(含理由),不允许静默跳。
- **`references/novelty-protocol.md`**:查新协议,与 evidence-protocol 同级、被 skill/agent 引用不内联
  ——四阶段(核心主张提取 3–5 个 → 多源检索,每主张 ≥3 种查询表述、强制查近 6 个月 arXiv →
  跨模型交叉验证 → 分级判定:每主张高/中/低 + 最接近前期工作对照表 + 0–10 总分 + 继续/谨慎/放弃);
  反幻觉规则(「已验证」= 按 DOI/arXiv id 成功导入 Zotero,对照表每行必带 Zotero key;
  无 Zotero 降级 arXiv/CrossRef/Semantic Scholar 三层核验,验不过标 `[UNVERIFIED]`,禁止凭记忆编 DOI);
  判定标准(「应用 X 于 Y 不构成创新,除非产生意外洞见」、方法与实验设置双层新颖性)。
- **`check-novelty` skill(skills 13 → 14,关卡 1)**:主流程按协议执行主张提取/检索/判定,
  阶段三交叉验证委托 reviewer;产出 novelty.md + gates.jsonl 行,写入走 update-workflow 或经用户确认;
  无 Zotero / 无 Codex 均有显式降级句式。
- **`reviewer` agent(服务 5 → 6,关卡 3)**:顶会审稿人立场(假设所有主张有问题)——
  新颖性交叉验证(Codex 裁决由主流程传入,与自身检索**双签**)+ 价值评分(X/10 + 逐条薄弱论点 + 具体实验设计建议);
  只读 + WebSearch/WebFetch,**无写工具、无记忆**;
  不提新方向(strategist 职责)、不重查完整性(auditor 职责);
  单向数据流扩展为 `auditor → strategist ← reviewer`。
- **方向档案目录化(dossier)**:`templates/project/directions/_TEMPLATE.md` 重构为 `_TEMPLATE/` 目录
  ——`direction.md`(保留原字段:核心诊断三件套 / slug / flag / baseline_group / access_level /
  子任务表 / 注册表行;新增 claims 表(论文接口)、Zotero 集合指针 + 关键引用 key 清单、
  frontmatter `status` 状态机 seed→surveyed→novelty-checked→piloted→reviewed→active→closed)、
  `novelty.md` / `review.md` / `pilot.md`(关卡产出骨架);gates.jsonl 不建实体模板,
  schema({gate, verdict, score, ts, evidence_ptr, reason})以注释块写在 direction.md 末尾。

### 变更
- **evidence-protocol.md**:读取清单新增「§12 Zotero 文献库(经 MCP 检索;仅当 manifest 含 discovery)」;
  数据源优先级补文献维度(用户粘贴 > Zotero 库内已验证条目 > web 检索结果,未落库视为未验证);
  模块缺席降级节补 discovery 缺席行为。既有条目不重排。
- **strategist**:证据基座接入文献层(引 evidence-protocol 新条目);教训库条目类型新增
  「已被某论文做过」(附撞车论文的 Zotero key)。
- **propose-hypothesis / refine-direction**:「与上下游对接」接入三关链路
  (卡片选中 → check-novelty → pilot(人工判)→ reviewer → refine-direction 收敛 →
  update-workflow 落档案);refine 的八维收敛流程不动,输入收集节吸收 novelty.md / review.md(若存在);
  「方向落地块」唯一模板指向改为 `_TEMPLATE/direction.md`(strategist / steward 同步)。
- **init / config**:模块清单加 discovery(§12);init 步骤 3 新增三个场景预设(选完可微调)——
  「找方向包」core+directions+discovery(无 exec,pilot 关降级人工判)/「执行包」core+exec+data+tracking /
  「全家桶」全模块;方向骨架实例化改为 `_TEMPLATE/` 目录形态(契约探测对旧单文件 `_TEMPLATE.md`
  警告"旧契约"不覆盖);config 模式三的 `modules` 取值说明同步;
  00-core.md 的 manifest 取值注释加 discovery,§ 锚点范围 §1–§11 → §1–§12。
- **40-directions.md**:方向文件目录说明改为 dossier 目录形态;注明全量实验选方向时
  select_direction 应校验 gates.jsonl(契约见 §12;契约扩展本身属 P2)。
- **test-workflow.sh 骨架**:ops 层追加 gates 断言(子命令契约不变)——manifest 含 discovery 时,
  断言方向目录下各 dossier 的 gates.jsonl 行行是合法 JSON(python3 优先、次选 jq,二者都不在则 SKIP;
  不含 discovery 则 SKIP;方向目录约定 docs/directions,可用 RW_DIRECTIONS_DIR 覆盖)。
- README:服务角色表加 reviewer 行;模块节加 discovery(注明当前提供 check-novelty,
  survey-literature / close-direction 属后续批次);单向数据流句子更新为 auditor → strategist ← reviewer;
  init 场景预设与目录结构树同步;plugin.json 升 0.5.0。

## 0.4.0(2026-07)—— 执行档案(exec-profile)双轴模型 + config 直通入口

### 设计总纲
v0.3 把"远程 + docker"固定为不可配置为唯一执行形态;0.4.0 把它泛化为**执行档案双轴模型**:
位置(local | remote) × 运行时(docker | venv) = 四种档案:
`remote-docker` / `remote-venv` / `local-docker` / `local-venv`。
保护机制不变量从"训练必须远程"回归为"**训练必须走受控启动通道**"——通道形态随档案变
(远程句柄 exec / ssh / docker exec / `scripts/run.sh`),不变量四档案同一条。

### 新增
- **manifest 字段 `exec-profile`**(00-core.md frontmatter):四档案之一,仅启用 exec 模块时有意义;
  init 两问定档(位置→运行时,各带扫描推荐)写入;guard 据它取默认通道模式。
- **四份 ops 预设** `templates/config/ops-presets/{remote-docker,remote-venv,local-docker,local-venv}.md`:
	  §7.2 映射表的执行档案占位模板,init 装配时嵌入;local 两档的 sync-code 标 **`不适用`**
  (operator 跳过并在回执注明,不算失败;test-workflow ops 层判 ⚠️SKIP 非 ❌)。
- **`templates/project/scripts/run.sh`**:local 档案的受控启动器骨架(即 RW_EXEC_PATTERN 匹配的通道):
	  进入环境(venv 激活 / docker exec,保留占位)→ 注入 tracking/权重 env → 后台启动 + 日志重定向 →
  回显日志路径;支持 `--fg` 前台(smoke 用);init 在 local 两档案时实例化。
- **`config` skill(skills 12 → 13)**:配置直通入口,三模式——查看(manifest + 各段填值/占位统计)、
  `set <键> <值>`(旧值→新值确认;source-dir 同步 frontmatter;改 modules/exec-profile 拒绝转 init,
	  改脚手架拒绝转 update-workflow)、`config init <键值对>` 非交互装配(未提供的值保留占位,收尾校验不变);
  特例 `set env.RW_EXEC_PATTERN` 经确认代写 `.claude/settings.json` 的 `"env"`
  (guard-protected-write 对该写操作再 ask 一次,机制协同;放宽拦截的改动额外提示风险)。
- **init 预扫描新增**:`nvidia-smi`(本地 GPU → 位置推荐 local)、`.venv`/`environment.yml`/conda
	  痕迹(→ 运行时推荐 venv)、docker 可用性(→ 运行时推荐 docker);含 exec 时先通过两轮问题确定档案,
	  再按档案裁剪问答(remote 场景询问远程句柄、docker 场景询问镜像分层)与装配。

### 变更(改名清单,收尾 grep 依据)
- 模块 `remote-exec` → **`exec`**;分段模板 `10-remote-exec.md` → **`10-exec.md`**;
  hook `guard-local-train.sh` → **`guard-train-channel.sh`**(hooks.json 同步);
  env `RW_REMOTE_PATTERN` → **`RW_EXEC_PATTERN`**(`RW_TRAIN_PATTERNS` 保留)。
- **guard 泛化**(规则不变:训练特征命中且不含通道特征 → exit 2):门控读 modules 含 `exec`
  (天然兼容旧名 remote-exec);RW_EXEC_PATTERN 未设时按 exec-profile 取内置默认通道模式
  (remote-docker `docker --context …(exec|run)` / remote-venv `ssh ` / local-docker
  `docker …(exec|run)` / local-venv `scripts/run\.sh`);无 exec-profile 字段回退 remote-docker
  默认(兼容);错误文案泛化为"训练必须走受控启动通道"。
- **10-exec.md §5 重组**:"远程执行环境"→"执行环境"——§5.0 档案声明与通用项(工作目录、uid 约定)
  + 按档案适用性小节(§5.1 远程句柄仅 remote、§5.2 镜像分层仅 docker、§5.3 venv/conda 仅 venv);
  §6/§7 结构保持,§7.2 改为按档案嵌入 ops 预设。
- **skill 门控**:build-env 仅 docker 运行时可用(venv 档案明确降级"无镜像概念");
  deploy-env 仅 remote-docker 可用;run-experiment / operator / steward / audit-workflow /
  modify-architecture / test-workflow 措辞与 § 引用适配档案模型。
- **test-workflow.sh 骨架**:guards 层用新脚本名与 RW_EXEC_PATTERN;ops 层映射标「不适用」判
  ⚠️SKIP 非 ❌。**checklist**:C2 增 exec-profile 一致性、C4–C6/C9 同步新名与"受控通道"措辞。
- README:exec 模块新名 + 档案矩阵(2×2)+ config skill 三模式与边界表 + 结构树更新;
  plugin.json / marketplace.json 描述同步。

## 0.3.1(2026-07)—— init 环境预扫描

### 新增
- **init 步骤 2「环境预扫描」**:提问前先做一轮本地只读扫描,把命中结果整理为后续问答的候选选项与"(推荐)"标注:
  - 模块推荐:`.gitmodules` / Dockerfile·`docker/` / `.dvc/` / 依赖文件含 mlflow·wandb 类 / `docs/directions/`;
  - `source-dir` 候选:submodule 路径、含 `pyproject.toml`/`setup.py` 的顶层目录;
  - 远程/本地句柄候选:`docker context ls`;
  - tracking 端点候选:`.env`·环境变量中的 `*_TRACKING_URI` 类。
- **扫描三规则**(写入 init 规则):只读不写;只扫本地不得联网(端点可达性归 test-workflow `connectivity` 层);
  结果只作候选与推荐,未经用户确认不进 config——"config 只放人确认过的事实"立场不变。
- 问答规则:有候选则列选项、最可能项放首位标"(推荐)"并附扫描依据,始终保留"未确定/其他"出口;
  无候选或扫描失败静默退回开放提问。

## 0.3.0(2026-07)—— 四层模型重构

### 设计总纲
四层模型定名并推导全部命名与职责:**L3 意图层 = skills(轻量编排入口,负责判断与交互)/
L2 服务层 = agents(五个服务承担核心任务)/ L1 驱动层 = 项目契约脚本(固定子命令 = ISA)/
L0 机制层 = hooks + config frontmatter manifest**。

### 新增
- **服务层 2 → 5**(`agents/`,统一四段结构:职责与边界 / 工具白名单 / 产出契约 / 约束):
  - `operator`(执行调度):按 config §7.2 的 ops 映射表执行关键 op 序列,验证后置条件,
	    回传结构化**脱敏回执**(敏感 env 值 → `***`,名单在 §7.2);遇到歧义时带完整现场信息返回主流程,
    不得擅自选择;单 op 失败恢复重试 ≤2 次;guard 对其同样生效。
  - `auditor`(实验完整性审计):收编原 analyze-results 子代理逻辑(完整性缺口 / 方向漂移三类 /
	    可信度四条 / 论文必要性三级、待办卡片与输出结构);只读、无 WebSearch、无 memory
	    (设计为无状态);不得提新方向,有价值现象只标注「值得探索,留给 strategist」。
  - `strategist`(假设与方向策略):收编原 propose-hypothesis 子代理逻辑(假设卡片、
	    教训库先行比对、输出规范);无 memory(教训库=长期知识库,注册表=当前工作索引);
    不得重新审计完整性,现状以 auditor 报告为准。
  - `steward`(由 workflow-builder 改名):维护对象扩到 manifest、模块段、骨架、ops 映射;
    新约束"不代替 operator 直接执行关键 op";受 update-workflow 委托时走两段式(计划+diff → 应用+自检)。
  - `architect` / `steward` 新增**记忆规则**段:事实均写文档/config,记忆只存指向文档的索引
    与工作偏好;冲突以文档为准并当场修正记忆。
  - **auditor → strategist 单向数据流**:审计报告是探索的可选输入,双方互不越界;
    共同的证据读取规则提取为 `references/evidence-protocol.md`,两 agent 引用不重复内联。
	- **ISA 与回执**(config §7.2/§7.3 + operator 定义):七个 op 保持最小集合——
	  `sync-code / install-editable / pull-data / smoke / launch`(关键操作,必须经 operator)+
  `status / collect`(轻,主流程可直接执行);每 op 一行映射 + 后置条件 + 敏感 env 名清单;
	  **租约互斥**:launch 后写 `.rw-lease-<exp>`,sync/install 前查租约,避免中断正在启动的训练。
- **test-workflow.sh 契约扩 `ops` 层**:对 §7.2 每个 op 做 dry-run 断言(映射非占位、
  脚本存在且可执行),不实际执行训练;`all` = guards+sanity+ops 本地三层。
- **checklist 扩到 C10**:C9(每个 ISA op 在 §7.2 有映射且脚本存在)、
  C10(agent 记忆目录不含应进 config/文档的事实)。
- **init 契约探测**:骨架目标文件已存在时探测是否符合契约(如对已有 test-workflow.sh
  试执行一个子命令),不符则明确警告"存在但不兼容契约",仍不覆盖。

### 变更
- **§ 重排(config-version: 2,无迁移逻辑——尚无实际用户)**:按模块顺序冻结为稳定锚点——
  core §1–4(项目性质/源码布局/指标/**提交规范**)、remote-exec §5–7(远程环境/实验脚手架/
  保护机制+ops 映射)、data §8、tracking §9、directions §10、maintenance §11。
- **模块改名**:`direction-system` → `directions`、`self-maintenance` → `maintenance`;
  分段模板对应改名 `40-directions.md` / `50-maintenance.md`。
- **skill 14 → 12**:`analyze-results` → **`audit-results`**(轻量编排入口,委托 auditor);
	  `build-image` → **`build-env`**(执行委托 operator);`propose-hypothesis` 调整为轻量编排入口
  (委托 strategist,开场提示带上新鲜 auditor 报告);`run-experiment` 重写
  (交互判断留主流程,关键 op 序列一次性委托 operator,收回执转述脱敏命令与 run id);
	  `deploy-env` 传输段委托 operator;`update-workflow` 改两段式委托 steward
  (①计划+diff 不写入文件 → ②主流程预览确认 → ③同一 steward 应用+自检);
  `test-workflow` 契约扩为 `guards|sanity|connectivity|ops|all`;
  全部 skill frontmatter/开场统一声明:所属模块、必需/可选模块、委托哪个服务(或主流程)。
- 所有 agent 均不声明 `model`(继承主会话);hooks 逻辑不变,仅注释里的 § 引用更新。
	- README 重写:四层模型图 + 五服务表 + 模块化安装说明 + 三点边界说明
  (模型策略 / 写保护边界 / 平台要求与团队场景)。

### 移除
- `show-workflow` skill:其"只读全貌"并入 `audit-workflow` 的**轻模式**(结构化快照,
  不执行清单核对);`audit-workflow` 清单核对模式不变。
- `workflow-builder` skill:steward 的正式入口是 `update-workflow`;需要直接用服务时口头指名。
- `agents/workflow-builder.md`(内容并入 `steward.md`)。

## 0.2.0(2026-07)—— 模块化重构

### 新增
- **模块化 config**:单体模板拆为 `templates/config/` 六个分段
  (core / remote-exec / data / tracking / direction-system / self-maintenance);
  装配后的 config 顶部带 YAML frontmatter manifest(`config-version` / `plugin-version` /
  `modules` / `source-dir`),供 hook 与 skill 机械查表。§1–§11 编号保持为全局稳定锚点,
  模块未启用时对应 § 整段缺席、不重排。
- **`init` skill**:交互式初始化器兼模块管理器——选模块(core 强制)→ 装配 config →
	  实例化项目工作区骨架(不覆盖已有文件)→ 交互填写关键值(source-dir、远程句柄、tracking 端点)→
  收尾校验(占位残留清单 + 实际运行 guards 测试)。
- **`templates/project/` 项目工作区骨架**:`directions/_TEMPLATE.md`(方向文件唯一模板,
  propose-hypothesis / refine-direction 的「方向落地块」统一指向它)、`RESEARCH_ROADMAP.md`
  (注册表 + 教训库)、`workflow-checklist.md`(C1–C8 通用检查项)、`scripts/test-workflow.sh`
  (子命令契约固定 `guards|sanity|connectivity|all`;guards 层可直接使用,喂假 JSON 断言 guard 退出码)。
- **SessionStart hook**(`session-init-check.sh`):无项目 config 时输出一行提示建议运行
  `/research-bench:init`;有则静默。
- **写保护 hook**(`guard-protected-write.sh`):Edit|Write|MultiEdit 落在 frontmatter
  `source-dir` 下、或写 `.claude/settings.json` / `.claude/hooks/` 时,降级为
  `permissionDecision: "ask"` 向用户请求确认(不直接拒绝)。
- `CHANGELOG.md`(本文件)。

### 变更
- **guard-local-train.sh**:增加模块门控——config 不存在或 `modules` 不含 `remote-exec` 时
	  静默放行;命令解析优先 jq、次选 python3,都缺才退回原始输入(修复原先无 jq 时把整个 JSON
	  参与匹配导致误拦截的问题)。`RW_TRAIN_PATTERNS` / `RW_REMOTE_PATTERN` env 覆盖机制保留。
- **全部 skill 开场统一为三步**:读 frontmatter manifest → 无 config 提示 init →
  所需模块未启用则明确降级或提示启用;每个 skill 显式声明 必需/可选 模块。
  run-experiment 的 data / tracking / direction-system 步骤按 manifest 有无跳过,跳过时说明。
- `build-image` 的 `tools: Bash` 改为规范键 `allowed-tools: Bash`;
  `workflow-builder` skill 加 `disable-model-invocation: true`。
	- `analyze-results` / `propose-hypothesis` 删除固定的 `model: "opus"`,子代理继承主对话模型。
- `test-workflow` 等 skill 引用测试脚本处改为确切子命令,删除"层名以脚本实际支持为准"类含糊措辞。
- `workflow-builder` agent 职责/约束与新结构同步(manifest、模块段、骨架文件;增删模块归 init)。
- README 重写为分级叙事(安装 → init → core 即用 → 按需加模块);plugin.json 升 0.2.0。

### 移除
- `templates/research-bench.config.md`(单体模板,由 `templates/config/` 分段取代)。
