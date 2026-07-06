# research-bench

research-bench 是面向模型架构研究的工作流套件,把研究方向判断、架构改动、对照实验、结果审计和远程
触发组织成一套可复现、可维护的流程。仓库现在由三部分组成:`rf`(研究方向插件)、`lf`(实验执行插件)
和 `remote-control`(可选的自建远程触发服务)。

`rf` 与 `lf` 是可安装的 Claude Code 插件,分别覆盖研究决策与实验落地;`remote-control` 不是插件,
而是给自有服务器部署的 Web/API 服务,用于从浏览器安全触发和查看 Claude Code 会话。

| 插件 | 命名空间 | 负责什么 |
|---|---|---|
| `rf` | `/rf:<skill>` | 研究方向:架构分析、假设生成、方向管理、查新审计 |
| `lf` | `/lf:<skill>` | 实验执行:环境构建部署、对照实验、工作流测试 |

两个插件共享同一份项目配置文件 `.claude/research-bench.config.md`(路径、执行环境、数据、指标、
跟踪系统等项目专属信息都写在这里)。**建议两个都装**以获得完整工作流;只装一个也能独立工作,但会
有 §7 边界说明里列出的保护机制缺口。

> `research-bench`(简称 `rb`)是仓库的品牌名,本身不是一个可安装的插件。

## 1. 架构模型

```
L3 意图层  skills   —— 用户入口，负责交互、判断和委托
   │ 委托
L2 服务层  agents   —— 六类服务承担分析、执行、验证、探索、审查和维护
   │ 调用
L1 驱动层  项目侧契约脚本 —— 固定子命令作为执行接口
   │ 保障
L0 机制层  hooks + config manifest —— 提供保护机制和机器可读配置
```

### 服务角色

| 服务 | 职责 | 工具范围 | 记忆策略 | 所在插件 |
|---|---|---|---|---|
| `architect` | 分析源码结构、数据流、改造位置和权重兼容性 | 只读源码，可写分析文档 | project memory + 记忆规则 | `rf` |
| `operator` | 按配置中的 ISA 映射执行关键操作并返回脱敏执行回执 | Bash / Read / Grep，无写工具 | 无记忆；执行发现写入回执 | `rf` + `lf`(两边都有) |
| `auditor` | 审计实验计划与结果完整性，输出缺口和待办 | 只读，无 WebSearch | 无记忆 | `rf` |
| `strategist` | 结合结果与文献提出假设和研究方向 | 只读 + WebSearch / WebFetch | 无记忆；教训库作为外部记忆 | `rf` |
| `reviewer` | 以顶会审稿人立场攻击方向价值：新颖性交叉验证与评分、薄弱论点和实验设计建议 | 只读 + WebSearch / WebFetch，无写工具；Codex 裁决由主流程传入 | 无记忆；裁决由主流程代笔写入档案 | `rf` |
| `steward` | 维护工作流配置、脚本和文档一致性 | 读写工作流脚手架 | project memory + 记忆规则 | `rf` + `lf`(两边都有) |

单向数据流为 `auditor → strategist ← reviewer`：审计报告与审查裁决都可以作为策略分析输入，但 `auditor` 不提出新方向、`reviewer` 不重查完整性也不提新方向、`strategist` 不重新审计完整性。三者共同遵循 `references/evidence-protocol.md`；`reviewer` 与查新流程另遵 `references/novelty-protocol.md`(两份协议文档只在 `rf` 插件里),且能「否」不能「准」——裁决只以文本交回主流程，写入注册表和方向档案仍需用户确认。

### ISA 操作集

`operator`(`rf`、`lf` 都携带一份，供各自委托的 skill 调用)只执行配置 §7.2 中声明的七个操作：

- 关键操作：`sync-code`、`install-editable`、`pull-data`、`smoke`、`launch`
- 轻量操作：`status`、`collect`

关键操作必须通过 `operator` 执行；轻量操作可由主流程直接执行。每个操作在项目配置中映射到具体脚本或命令，并声明后置条件和敏感环境变量。`launch` 成功后写入租约文件，`sync-code` 和 `install-editable` 前检查租约，避免影响正在执行的训练任务。

## 2. 安装

### 从 GitHub 安装

仓库包含 `.claude-plugin/marketplace.json`，列出 `rf`、`lf` 两个插件。先添加这个仓库作为
marketplace，再分别安装需要的插件（推荐两个都装）：

```text
/plugin marketplace add Endofthestars/research-bench
/plugin install rf@research-bench
/plugin install lf@research-bench
```

更新插件：

```text
/plugin marketplace update research-bench
```

### 从本地目录安装

也可以先克隆仓库，再在项目的 `.claude/settings.json` 中分别引用两个插件的本地路径：

```bash
git clone git@github.com:Endofthestars/research-bench.git
```

```json
{
  "plugins": [
    "/绝对路径/research-bench/rf",
    "/绝对路径/research-bench/lf"
  ]
}
```

## 3. 初始化

首次在项目中启用插件时，`SessionStart` hook（`rf`、`lf` 各自携带一份）会检查
`.claude/research-bench.config.md` 是否存在。若尚未初始化，会提示运行：

```text
/rf:init
```

或

```text
/lf:init
```

二者行为等价（`init` 是两个插件都携带的共享 skill），装了哪个插件就用哪个的命名空间调用；两个都装时用哪个都一样。

初始化流程包括：

1. 本地只读预扫描：检查 `.gitmodules`、Docker、GPU、venv/conda、DVC、依赖文件、`.env` 等线索。
2. 选择模块：先按研究阶段选场景预设——「找方向包」（core+directions+discovery）、「执行包」（core+exec+data+tracking）、「全家桶」（全模块），选完可微调；`core` 必选。
3. 选择执行档案：启用 `exec` 时，通过“执行位置 × 运行时”确定 `exec-profile`。
4. 生成配置：装配 `.claude/research-bench.config.md`，并按模块裁剪配置段。
5. 实例化项目骨架：生成方向模板、路线图、检查清单、测试脚本和本地启动脚本；已有文件不覆盖。
6. 填写关键值：如 `source-dir`、执行句柄、工作目录、tracking 端点等。
7. 收尾校验：提示占位残留，并在启用 `exec` 时执行保护机制回归测试。

如需新增/删除模块或切换执行档案，再次运行 `/rf:init` 或 `/lf:init`。

## 4. 配置入口

`/rf:config` 或 `/lf:config`（两者等价）用于查看和修改项目配置：

- 查看：输出 manifest、启用模块、关键配置值和占位残留统计。
- `set <键> <值>`：定点修改配置值，写入前展示旧值和新值。
- `config init modules=core,exec exec-profile=local-venv source-dir=src/ ...`：非交互初始化配置和骨架。
- `set env.RW_EXEC_PATTERN <模式>` 或 `set env.RW_TRAIN_PATTERNS <模式>`：经确认后更新 `.claude/settings.json` 的 `"env"`。

职责边界：

- 交互初始化、模块增删、执行档案变更：使用 `init`。
- 查看配置、定点改值、非交互初始化：使用 `config`。
- 修改脚本、hook、skill、agent、检查清单等脚手架内容：使用 `update-workflow`。

## 5. 模块

### core：基础能力(`rf`)

`core` 是必选模块，不依赖执行环境或实验跟踪系统。

| 能力 | 载体 | 所在插件 |
|---|---|---|
| 架构分析 | `analyze-architecture` skill → `architect` agent | `rf` |
| 安全修改架构或 loss | `modify-architecture` skill | `rf` |
| 假设生成（无 tracking 时使用用户提供的证据） | `propose-hypothesis` skill → `strategist` agent | `rf` |
| 源码写保护 | `guard-protected-write` hook | `rf` |

需要填写配置 §1–§4：项目性质、源码布局、指标和提交规范。

### exec：受控执行环境(`lf`)

`exec` 启用实验执行链路和训练启动保护机制。执行档案由“位置 × 运行时”组成：

| | docker | venv/conda |
|---|---|---|
| remote | `remote-docker`：远程 docker daemon，支持 build + deploy 链路 | `remote-venv`：通过 ssh 和环境激活执行 |
| local | `local-docker`：本机 docker 容器执行 | `local-venv`：通过 `scripts/run.sh` 执行 |

四种档案共享同一约束：训练必须通过受控启动通道执行。`guard-train-channel`（`lf` 插件携带）会拦截带训练特征但未匹配受控通道的 Bash 命令。

需要填写配置 §5–§7：执行环境、实验脚手架、保护机制模式和 ISA 映射表。§7.1 的模式也可写入项目 `.claude/settings.json`：

```json
{
  "env": {
    "RW_TRAIN_PATTERNS": "--train|train_loop|fit\\.py",
    "RW_EXEC_PATTERN": "docker[[:space:]]+--context.*(exec|run)"
  }
}
```

### data：数据集与权重管理(`lf`)

`data` 为 `run-experiment` 提供 `pull-data` 步骤，并为 `deploy-env` 提供权重预下载约定。需要填写配置 §8。

### tracking：实验跟踪(`lf`)

`tracking` 为实验记录、结果审计和假设生成提供定量证据来源。需要填写配置 §9。

### directions：研究方向管理(`rf`)

`directions` 提供方向模板、方向注册表、教训库和方向漂移核查。相关能力包括 `propose-hypothesis`、`refine-direction`、`audit-results`（均 `rf`）和 `run-experiment`（`lf`）的方向选择步骤。需要填写配置 §10。

### maintenance：工作流维护(`rf` + `lf` 共享)

`maintenance` 提供工作流审计、更新和测试能力：

- `audit-workflow`：只读审计配置、提示词和脚本一致性。（`rf`、`lf` 都有）
- `update-workflow`：通过 `steward` 两阶段修改工作流脚手架。（`rf`、`lf` 都有）
- `test-workflow`：调用项目侧确定性测试脚本。（仅 `lf`）

需要填写配置 §11。

### discovery：方向发现(`rf`)

`discovery` 为方向进注册表前提供关卡链：查新拦截撞车、试点取实证信号、对抗审查攻击价值。当前提供 `check-novelty`（关卡 1，四阶段查新，流程见 `references/novelty-protocol.md`）与 `reviewer` 审查（关卡 3）；pilot（关卡 2）当前由人工判定，`survey-literature`、`close-direction` 属后续批次。关卡裁决写入方向 dossier 的 `gates.jsonl`；Zotero MCP（文献落库即验证）与 Codex MCP（由主流程调用后传入 reviewer 做跨模型交叉验证）作为外部依赖写入配置，未配置时均有降级路径。依赖 `core`，强烈建议搭配 `directions`。需要填写配置 §12。

## 6. 目录结构

```text
research-bench/                           (仓库根 = research-bench / rb 品牌)
├── .claude-plugin/
│   └── marketplace.json          # 列出 rf、lf 两个插件
├── rf/                            # 插件:研究方向侧,命名空间 /rf:<skill>
│   ├── .claude-plugin/plugin.json
│   ├── agents/
│   │   ├── architect.md
│   │   ├── auditor.md
│   │   ├── strategist.md
│   │   ├── reviewer.md
│   │   ├── operator.md           # 与 lf 共享,供 modify-architecture 的可选 smoke test 委托
│   │   └── steward.md            # 与 lf 共享,供 update-workflow 委托
│   ├── skills/
│   │   ├── analyze-architecture/
│   │   ├── modify-architecture/
│   │   ├── propose-hypothesis/
│   │   ├── refine-direction/
│   │   ├── check-novelty/
│   │   ├── audit-results/
│   │   ├── init/                 # 与 lf 共享,完整复制,自引用改写为 /rf:
│   │   ├── config/                # 同上
│   │   ├── update-workflow/       # 同上
│   │   └── audit-workflow/        # 同上
│   ├── hooks/
│   │   ├── hooks.json             # 只声明本插件实际携带的 hook
│   │   ├── session-init-check.sh  # 与 lf 共享(幂等,双装时重复触发可接受)
│   │   └── guard-protected-write.sh  # 仅 rf:保护 SOURCE_DIR 写入
│   ├── references/
│   │   ├── evidence-protocol.md
│   │   └── novelty-protocol.md
│   └── templates/                 # 与 lf 内容相同的完整复制(init 需要全部 7 个模块模板)
│       ├── config/{00-core,10-exec,20-data,30-tracking,40-directions,50-maintenance,60-discovery}.md
│       ├── config/ops-presets/
│       └── project/{RESEARCH_ROADMAP.md, workflow-checklist.md, directions/_TEMPLATE/, scripts/}
├── lf/                            # 插件:执行侧,命名空间 /lf:<skill>
│   ├── .claude-plugin/plugin.json
│   ├── agents/
│   │   ├── operator.md            # 与 rf 共享
│   │   └── steward.md             # 与 rf 共享
│   ├── skills/
│   │   ├── build-env/
│   │   ├── deploy-env/
│   │   ├── run-experiment/
│   │   ├── test-workflow/
│   │   ├── init/                  # 与 rf 共享,完整复制,自引用改写为 /lf:
│   │   ├── config/                 # 同上
│   │   ├── update-workflow/        # 同上
│   │   └── audit-workflow/         # 同上
│   ├── hooks/
│   │   ├── hooks.json              # 只声明本插件实际携带的 hook
│   │   ├── session-init-check.sh   # 与 rf 共享
│   │   └── guard-train-channel.sh  # 仅 lf:训练启动通道保护
│   └── templates/                  # 与 rf 内容相同的完整复制
├── remote-control/                 # 可选服务:自建远程触发/监控 Claude Code 会话
│   ├── server/                     # FastAPI 后端
│   ├── web/                        # 静态 Web 面板 + PWA
│   ├── deploy/                     # systemd / Caddy / env 模板
│   └── docs/SECURITY.md            # 公网部署前必须阅读的安全说明
├── docs/DESIGN.md
├── CHANGELOG.md
├── LICENSE
└── README.md
```

## 7. 边界说明

- **模型策略**：所有 agent 默认继承主会话模型，不在 frontmatter 中声明 `model`。如需固定模型，可在对应 agent frontmatter 中添加 `model` 字段。
- **写保护边界**：`guard-protected-write` 只覆盖 Claude Code 的 `Edit`、`Write`、`MultiEdit` 工具写入，且**只在 `rf` 插件里**。只装 `lf`、不装 `rf` 时，源码写保护不生效——这是拆分后接受的缺口，正常使用预期两个插件一起装。同理 `guard-train-channel` 只在 `lf` 里，只装 `rf` 时训练启动通道保护不生效。通过 Bash 间接写入仍依赖 Claude Code 权限模式和用户确认。
- **共享 skill 的分叉**：`init`/`config`/`update-workflow`/`audit-workflow` 在 `rf`、`lf` 里各有一份完整复制，功能等价，但文字里的自引用前缀分别是 `/rf:` 和 `/lf:`——这是有意为之的分叉，不是不一致；两个插件都装时，同名 skill 会在两个命名空间下各出现一次，属预期行为。
- **重复触发**：两个插件都装时，`session-init-check`（SessionStart）会各自触发一次，多打印一行提示；该 hook 只读、无副作用，重复触发是可接受的噪音。
- **维护漂移风险**：共享的 skill/agent/模板内容以真实文件复制而非符号链接的方式存在于 `rf/` 和 `lf/` 两棵目录树下（公开分发的插件仓库不适合依赖符号链接,详见 CHANGELOG）。改动共享内容时需要同时改两处,不会自动同步。
- **平台要求**：hook 依赖 bash。Windows 环境建议使用 WSL 或 Git Bash。
- **配置提交策略**：项目配置可能包含内网路径、端点和执行句柄。公开仓库不应提交包含敏感信息的项目配置。

## 8. 许可证

MIT，见 [LICENSE](LICENSE)。本插件只包含 Claude Code 工作流脚手架，不包含任何模型框架或训练框架源码。

## 9. 设计原则

- **通用方法与项目配置分离**：skill 和 agent 描述通用流程，项目专属值集中在配置文件。
- **机器可读与人可读分离**：hook 需要读取的值放在 frontmatter manifest，其余说明放在正文配置段。
- **意图与执行分离**：skill 负责交互和委托，关键操作通过 `operator` 按 ISA 执行。
- **模块化启用**：基础能力来自 `core`，执行、数据、跟踪、方向、维护和方向发现能力按需启用。
- **职责边界清晰**：分析、执行、审计、策略、审查和维护分别由不同 agent 承担。
- **保护机制不可自动削弱**：修改保护机制、检查标准或权限配置时必须显式说明并获得用户确认。
