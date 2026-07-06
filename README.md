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
有 §8 边界说明里列出的保护机制缺口。

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

也可以先克隆仓库，再把本地目录添加为 marketplace 后安装（与 GitHub 安装同一套机制，仅来源不同）：

```bash
git clone git@github.com:Endofthestars/research-bench.git
```

```text
/plugin marketplace add /绝对路径/research-bench
/plugin install rf@research-bench
/plugin install lf@research-bench
```

开发调试时也可以不安装、按次加载：

```bash
claude --plugin-dir /绝对路径/research-bench/rf --plugin-dir /绝对路径/research-bench/lf
```

> 注意：不支持在 `.claude/settings.json` 中以 `"plugins": [路径]` 的形式引用插件——该字段不存在，
> 这样写插件不会被加载，skill 也不会获得 `rf:` / `lf:` 命名空间，`/init` 会命中 Claude Code
> 自带的同名命令而不是本插件的 `rf:init`。请使用上述两种方式之一。

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

## 6. Skill 参考

本节为两个插件全部 skill 的规范说明。两个插件共提供 14 个 skill，其中 4 个（`init`、`config`、`audit-workflow`、`update-workflow`）在 `rf`、`lf` 中各存在一份功能等价的副本。

每个 skill 同时附带一份同名的 `commands/<skill>.md` 薄壳,与 skill 共用 `插件名:skill 名` 的调用名——功能一致,仅为保证各版本 Claude Code 下斜杠补全均可用。

所有 skill 在执行前均读取 `.claude/research-bench.config.md` 的 frontmatter manifest 以确认模块启用状态，并遵循统一的门控规则：配置文件不存在时终止执行并提示运行 `init`；必需模块未启用时终止执行并提示通过 `init` 启用；可选模块未启用时降级执行，并显式说明被省略的步骤。

### 6.1 总览

| Skill | 所在插件 | 必需模块 | 可选模块 | 执行方式 |
|---|---|---|---|---|
| `init` | rf、lf | — | — | 主流程（交互式） |
| `config` | rf、lf | — | — | 主流程 |
| `analyze-architecture` | rf | core | — | 委托 `architect` |
| `modify-architecture` | rf | core | exec | 主流程；smoke 测试委托 `operator` |
| `propose-hypothesis` | rf | core | tracking、directions | 委托 `strategist` |
| `refine-direction` | rf | core、directions | — | 主流程（多轮交互） |
| `check-novelty` | rf | core、discovery | directions、maintenance | 主流程；交叉验证委托 `reviewer` |
| `audit-results` | rf | tracking | directions | 委托 `auditor` |
| `run-experiment` | lf | exec | data、tracking、directions | 主流程；关键操作委托 `operator` |
| `build-env` | lf | exec（docker 运行时） | — | 委托 `operator`；仅限手动触发 |
| `deploy-env` | lf | exec（remote-docker 档案） | data | 委托 `operator`；仅限手动触发 |
| `test-workflow` | lf | maintenance | exec | 主流程（调用测试脚本） |
| `audit-workflow` | rf、lf | maintenance | 其余模块 | 主流程（只读） |
| `update-workflow` | rf、lf | maintenance | — | 两阶段委托 `steward` |

### 6.2 共享 skill

以下 4 个 skill 在 `rf`、`lf` 中各携带一份，功能等价，调用时使用所装插件对应的命名空间。

#### `init` — 初始化与模块管理

**功能**：将插件内置的分段配置模板装配为项目配置文件 `.claude/research-bench.config.md`，并实例化项目侧骨架文件（方向模板、研究路线图、工作流检查清单、测试脚本、本地启动脚本）。

**行为特性**：幂等且可重入。对已初始化的项目再次执行时，进入模块增删或执行档案切换模式；已存在的骨架文件不予覆盖，仅执行契约探测。完整初始化流程见 §3。

**适用场景**：首次在项目中启用插件；新增或删除模块；切换执行档案（exec-profile）。

#### `config` — 配置管理

**功能**：项目配置的查看与定点修改入口，遵循「配置文件为单一事实来源」原则。提供四种调用形式：

- 无参数调用：输出 manifest、启用模块、关键配置值及占位符残留统计；
- `set <键> <值>`：定点修改单个配置值，写入前展示修改前后的值；
- `config init <键值对>`：非交互方式完成配置初始化与骨架实例化；
- `set env.RW_TRAIN_PATTERNS <模式>` / `set env.RW_EXEC_PATTERN <模式>`：经用户确认后写入项目 `.claude/settings.json` 的 `"env"` 字段。

**职责边界**：仅处理配置段内单值的修改。模块装配与执行档案变更归属 `init`；涉及跨文件同步的脚手架修改归属 `update-workflow`。

#### `audit-workflow` — 工作流审计

**功能**：检查工作流配置、提示词与脚本之间的一致性。该 skill 为只读操作，仅输出报告，不实施任何修改。提供两种模式：

- **快照模式**：输出当前工作流结构的只读快照，内容按 manifest 裁剪，未启用模块对应的章节予以省略并注明；
- **清单模式**：以配置 §11 指定的工作流检查清单为唯一标准逐条核对，报告配置漂移、内容冗余、职责重叠及保护机制缺口。

**后续动作**：审计发现的问题统一通过 `update-workflow` 修复。

#### `update-workflow` — 工作流脚手架修改

**功能**：对工作流脚手架（`.claude/` 配置、`scripts/`、容器构建文件、`experiments/`、工作区文档）实施修改的统一入口，为 `steward` 服务的正式调用通道。

**流程**：采用两阶段确认机制。第一阶段由 `steward` 产出改动计划、逐文件 diff 及关联同步清单，此阶段不写入任何文件；第二阶段由主流程将计划完整呈现给用户预览；用户确认后，由同一 `steward` 实例应用改动并按检查清单执行同步自检。

**约束**：不得自动削弱保护机制、约束条件或检查标准；模块的增删不属于本 skill 职责范围，须经由 `init` 执行。

### 6.3 `rf` 专属 skill（研究方向侧）

#### `analyze-architecture` — 架构分析

**功能**：将源码调研任务委托给 `architect` 服务（只读、隔离上下文）执行，产出物包括：相关文件与函数定位、当前数据流描述、改动点及其对预训练权重加载的影响评估，以及「可安全改造」与「高危改动」的分类标注。

**产出管理**：分析结论沉淀至配置 §2 指定的架构地图文档；主对话仅接收摘要，不引入完整源码内容。

**适用场景**：架构理解、改动位置定位、改动风险评估；作为 `modify-architecture` 的前置分析步骤。

#### `modify-architecture` — 架构修改

**功能**：对配置 §2 `SOURCE_DIR` 下的模型源码实施受控修改（decoder 结构、新增模块、loss 函数、目标表示等），全部改动须满足可控、可回滚、可对照、可复现四项要求。

**核心规则**：改动必须实现为可开关的 flag（默认关闭时行为等价于原版），禁止将改动实现为不可关闭的默认行为；消融实验与回滚均以此为前提。

**流程要求**：改动前须经 `analyze-architecture` 确认改动点与权重兼容性影响，并执行一次 smoke 测试作为对照基线。启用 `exec` 模块时，smoke 测试委托 `operator` 执行；未启用时提示用户自行验证前向与反向传播。

#### `propose-hypothesis` — 研究假设生成

**功能**：将发散性探索委托给 `strategist` 服务执行，综合实验结果与文献，产出结构化的「假设卡片」。

**模块降级行为**：启用 `tracking` 时，定量证据取自实验跟踪系统，且建议先执行 `/rf:audit-results` 以提供缺口清单作为输入；未启用时以用户提供的数据为准。启用 `directions` 时，先与教训库比对并附带「方向落地块」；未启用时仅产出假设卡片。

**定位**：与 `refine-direction` 构成互补关系——本 skill 负责发散生成候选方向，`refine-direction` 负责单一方向的收敛细化。

#### `refine-direction` — 研究方向细化

**功能**：以单个种子想法（或 `propose-hypothesis` 产出中选定的一张卡片）为输入，在主流程中通过多轮交互逐维收敛，最终产出一个以 slug 标识的正式方向（包含核心诊断、flag 定义与对照组设计）及可交付 `update-workflow` 写入的「方向落地块」。

**执行方式**：不委托任何服务，全程在主流程中进行；每轮聚焦一个待定维度，提供候选选项与推荐，经用户确认后进入下一维度。

**约束**：只读、仅产出文本，不修改任何代码或文档；文件写入统一经由 `update-workflow` 完成。

#### `check-novelty` — 新颖性验证（方向关卡 1）

**功能**：对单个候选方向执行四阶段查新：核心主张提取、多源检索、跨模型交叉验证、分级判定，产出新颖性档案（方向 dossier 中的 `novelty.md`）与关卡记录。

**规范依据**：流程、反幻觉规则与判定标准以 `rf/references/novelty-protocol.md` 为唯一依据，skill 本身仅负责编排。交叉验证阶段委托 `reviewer` 服务执行，可接入 Codex MCP 进行跨模型验证。

**适用场景**：候选方向进入注册表前的撞车拦截；为已有方向档案补充新颖性记录。

#### `audit-results` — 实验结果审计

**功能**：将结果核查任务委托给 `auditor` 服务（只读、无状态）执行，依据实验计划从完整性、方向漂移、可信度、论文必要性四个维度核对现有结果，输出结构化的「待办实验清单」，标注缺失实验及不可信实验（如随机种子数量不足、未从 smoke 规模升级至全量、OOD 评估未执行等情形）。

**适用场景**：一批实验完成后的缺口盘点；论文实验章节撰写前的完备性检查。审计报告同时作为 `propose-hypothesis` 的推荐输入。

### 6.4 `lf` 专属 skill（实验执行侧）

#### `run-experiment` — 实验执行

**功能**：按执行档案（remote-docker / remote-venv / local-docker / local-venv）执行训练实验，涵盖 baseline 对照、实验跟踪记录与复现信息留存。

**操作分级**：依据配置 §7.2 的 ISA 映射，操作分为两级。关键操作（`sync-code`、`install-editable`、`pull-data`、`smoke`、`launch`）以完整序列一次性委托 `operator` 执行；轻量操作（`status`、`collect`）由主流程直接执行，同样受保护机制约束。

**并发保护**：`launch` 成功后写入租约文件；`sync-code` 与 `install-editable` 执行前检查租约，防止干扰正在进行的训练任务。

#### `build-env` — 环境镜像构建

**功能**：按配置 §5.2 定义的镜像分层（底座镜像、项目层镜像）在本地构建环境镜像。职责限定为构建，不包含远程传输。

**适用范围**：仅适用于 docker 运行时档案（remote-docker、local-docker）。venv 档案下调用时明确提示不适用并指引至配置 §5.3。

**触发方式**：仅限用户手动触发（`disable-model-invocation: true`），适用时机为依赖、CUDA 或框架版本发生变化。与 `deploy-env` 构成两阶段链路；local-docker 档案下构建完成即可在本机使用。

#### `deploy-env` — 环境镜像部署

**功能**：将 `build-env` 构建完成的镜像传输至远程 docker daemon；启用 `data` 模块时，同时通过 `pull-data` 操作预下载预训练权重。

**适用范围**：仅适用于 remote-docker 档案；其余档案下调用时明确提示不适用。传输命令取自配置 §5.2 的 deploy 脚本，经 `operator` 执行。

**触发方式**：仅限用户手动触发，适用时机为依赖变化并重新构建镜像之后。

#### `test-workflow` — 工作流回归测试

**功能**：调用配置 §11 指定的确定性测试脚本（约定为 `scripts/test-workflow.sh`），验证保护机制拦截行为、本地健康检查、ISA 映射 dry-run 及远程只读连通性，并对脚本输出进行解读。测试结论由脚本断言决定，skill 不自行判定。

**定位**：与 `audit-workflow` 构成互补关系——audit 检查配置一致性（读取与推理，不执行），test 验证脚本实际行为（执行断言）。

**适用场景**：修改 guard hook、`.claude/settings.json`、脚本或容器构建文件之后的回归确认。
## 7. 目录结构

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
│   ├── commands/                  # 每个 skill 一份同名薄壳,保证 /rf: 斜杠补全可靠
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
│   ├── commands/                   # 每个 skill 一份同名薄壳,保证 /lf: 斜杠补全可靠
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

## 8. 边界说明

- **模型策略**：所有 agent 默认继承主会话模型，不在 frontmatter 中声明 `model`。如需固定模型，可在对应 agent frontmatter 中添加 `model` 字段。
- **写保护边界**：`guard-protected-write` 只覆盖 Claude Code 的 `Edit`、`Write`、`MultiEdit` 工具写入，且**只在 `rf` 插件里**。只装 `lf`、不装 `rf` 时，源码写保护不生效——这是拆分后接受的缺口，正常使用预期两个插件一起装。同理 `guard-train-channel` 只在 `lf` 里，只装 `rf` 时训练启动通道保护不生效。通过 Bash 间接写入仍依赖 Claude Code 权限模式和用户确认。
- **共享 skill 的分叉**：`init`/`config`/`update-workflow`/`audit-workflow` 在 `rf`、`lf` 里各有一份完整复制，功能等价，但文字里的自引用前缀分别是 `/rf:` 和 `/lf:`——这是有意为之的分叉，不是不一致；两个插件都装时，同名 skill 会在两个命名空间下各出现一次，属预期行为。
- **重复触发**：两个插件都装时，`session-init-check`（SessionStart）会各自触发一次，多打印一行提示；该 hook 只读、无副作用，重复触发是可接受的噪音。
- **维护漂移风险**：共享的 skill/agent/模板内容以真实文件复制而非符号链接的方式存在于 `rf/` 和 `lf/` 两棵目录树下（公开分发的插件仓库不适合依赖符号链接,详见 CHANGELOG）。改动共享内容时需要同时改两处,不会自动同步。
- **平台要求**：hook 依赖 bash。Windows 环境建议使用 WSL 或 Git Bash。
- **配置提交策略**：项目配置可能包含内网路径、端点和执行句柄。公开仓库不应提交包含敏感信息的项目配置。

## 9. 许可证

MIT，见 [LICENSE](LICENSE)。本插件只包含 Claude Code 工作流脚手架，不包含任何模型框架或训练框架源码。

## 10. 设计原则

- **通用方法与项目配置分离**：skill 和 agent 描述通用流程，项目专属值集中在配置文件。
- **机器可读与人可读分离**：hook 需要读取的值放在 frontmatter manifest，其余说明放在正文配置段。
- **意图与执行分离**：skill 负责交互和委托，关键操作通过 `operator` 按 ISA 执行。
- **模块化启用**：基础能力来自 `core`，执行、数据、跟踪、方向、维护和方向发现能力按需启用。
- **职责边界清晰**：分析、执行、审计、策略、审查和维护分别由不同 agent 承担。
- **保护机制不可自动削弱**：修改保护机制、检查标准或权限配置时必须显式说明并获得用户确认。
