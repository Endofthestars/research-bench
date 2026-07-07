---
name: init
description: 初始化或调整项目的 research-bench 配置。流程包括本地只读预扫描、模块选择、exec-profile 定档、配置装配、项目骨架实例化、关键值填写和收尾校验。适用于首次使用、增删模块或切换执行档案。
---

# 初始化与模块管理（交互式）

将插件的分段 config 模板装配为项目内的 `.claude/research-bench.config.md`，并实例化项目工作区骨架文件。
**幂等可重入**：已初始化项目再次执行时，进入增删模块或切换执行档案模式；已存在的骨架文件不覆盖，只做契约探测。

> **所属模块**:—(init 本身不属于任何模块,它管理模块);**执行方式**:主流程执行(交互式)。
> 与 `config` skill 的分界:**交互初始化 / 增删模块 / 换执行档案 = init**;查看配置、定点改一个值、
> 非交互非交互初始化 = `config`;改脚手架/脚本/skill = `update-workflow`。

## 模块一览(core 强制,其余按需)

| 模块 | 解锁什么 | config 段 |
|---|---|---|
| `core`(必装) | analyze/modify-architecture、architect、strategist(降级态)、源码写保护 | §1–4 |
| `exec` | run-experiment、operator、guard-train-channel 保护机制、ops 映射表;build-env(docker 运行时)、deploy-env(remote-docker) | §5–7 |
| `data` | run-experiment 的 pull-data、deploy-env 预下载权重 | §8 |
| `tracking` | run-experiment 记录、audit-results(auditor)、propose-hypothesis 的定量证据源 | §9 |
| `directions` | 方向注册表:propose-hypothesis / refine-direction / audit-results / run-experiment 选方向 | §10 |
| `maintenance` | audit/update/test-workflow、steward | §11 |
| `discovery` | 方向发现三关:check-novelty 查新、reviewer 对抗审查;Zotero / Codex MCP 接入与降级(survey-literature / close-direction 属后续批次) | §12 |

**discovery 的依赖**:`core` 必需;`directions` 强烈建议(关卡产出的落点是方向 dossier);
`exec` 可选(pilot 关卡,当前批次人工判)。

**exec 的执行档案(exec-profile)**:选了 exec 还要**两问定档**(步骤 4)——
位置(local | remote)× 运行时(docker | venv)= `remote-docker` / `remote-venv` /
`local-docker` / `local-venv`。四档案共享同一条保护机制不变量:**训练必须走受控启动通道**
(通道形态随档案变:远程句柄 exec / ssh / docker exec / `scripts/run.sh`)。

## 流程

1. **检测现状**:读项目 `.claude/research-bench.config.md`。
   - 不存在 → 全新初始化,走下面全部步骤。
   - 存在 → 读顶部 frontmatter manifest 的 `modules` / `exec-profile`,进入**增/删模块或换档案模式**:
     只拼接新增段 / 删除弃用段(删除前把该段现有内容展示给用户确认),frontmatter 同步更新;
     换执行档案 = 重走步骤 4 定档 + 重嵌 §7.2 ops 预设(旧映射表内容展示给用户确认后替换)+
     按新档案补实例化骨架;已填的正文值原样保留。
2. **环境预扫描(只读,产候选与推荐)**:提问前先做一轮本地扫描,把结果变成后续问答的候选选项与推荐。
   三条规则：**只读不写**；**只扫描本地，不联网**（端点可达性由 test-workflow `connectivity` 层验证）；
   **扫描结果只作为候选，写入 config 前必须由用户确认**。
   | 扫什么 | 怎么扫(本地、秒级) | 喂给哪一问 |
   |---|---|---|
   | 模块推荐 | `.gitmodules`;`Dockerfile`/`docker/`;`.dvc/`;依赖文件(requirements/pyproject)含 mlflow/wandb 类;`docs/directions/` | 步骤 3:命中的模块在选项说明里标推荐及依据 |
   | 位置候选(exec 定档第一问) | `nvidia-smi` 是否可用且有卡(本地 GPU → 推荐 local);`docker context ls` 有非 default 远程 context、`.ssh/config` 有主机项(→ 推荐 remote) | 步骤 4 第一问 |
   | 运行时候选(exec 定档第二问) | `command -v docker` + `Dockerfile`/`docker/`(→ 推荐 docker);`.venv/`、`environment.yml`、`conda-lock`/`.conda` 痕迹、`uv.lock`(→ 推荐 venv) | 步骤 4 第二问 |
   | `source-dir` 候选 | `.gitmodules` 的 submodule 路径;含 `pyproject.toml`/`setup.py` 的顶层目录 | 步骤 7 |
   | 远程/本地句柄候选 | `docker context ls`(本地命令,不连接远程);`.ssh/config` 主机名 | 步骤 7(仅 remote 档案问) |
   | tracking 端点候选 | `.env` 与环境变量中的 `*_TRACKING_URI` 类;依赖文件中的跟踪工具名 | 步骤 7(不连网验证) |
   - 无候选或扫描失败 → 该问退回开放提问,静默降级、不报错不阻塞。
3. **选模块**:先用 `AskUserQuestion` 给**三个场景预设**(按"处在研究哪个阶段"提问,选完可微调):
   - **找方向包**:`core + directions + discovery`(无 exec,pilot 关卡降级人工判)
   - **执行包**:`core + exec + data + tracking`
   - **全家桶**:全部模块
   - 自定义:直接进下面的逐模块勾选
   选中预设后进入 `AskUserQuestion`(multiSelect)微调,预设模块预勾选、`core` 强制包含不可取消;
   每个选项一句话说明"解锁什么、要填什么"(照上表);有步骤 2 的扫描命中时,
   在该模块选项说明里标注推荐与依据(如「检测到 `.dvc/`,推荐」),但不替用户勾选。
4. **两问定档(仅当选了 exec)**:用 `AskUserQuestion` 分两问确定 `exec-profile`,各带扫描推荐:
   - **第一问·位置**:训练在哪台机器执行?`local`(本机;有 `nvidia-smi` 命中则标"(推荐)"附依据)/
     `remote`(远程机;有远程 context / ssh 主机命中则标推荐)。
   - **第二问·运行时**:环境如何管理?`docker`(镜像;有 Dockerfile/docker 可用命中则标推荐)/
     `venv`(venv/conda;有 `.venv`/`environment.yml` 等痕迹则标推荐)。
   - 两问答案拼成 `exec-profile`,并据它**裁剪后续问答与装配**:remote 才问远程句柄(§5.1),
     docker 才问镜像分层(§5.2),venv 才问激活方式(§5.3);§7.2 嵌入对应 ops 预设;
     local 档案实例化 `scripts/run.sh`。
5. **装配 config**:按选中模块,依序拼接 `${CLAUDE_PLUGIN_ROOT}/templates/config/` 下的
   `00-core.md`、`10-exec.md`、`20-data.md`、`30-tracking.md`、`40-directions.md`、
   `50-maintenance.md`、`60-discovery.md` → 写入项目 `.claude/research-bench.config.md`。
   - 剥掉各分段文件头部的 `<!-- 模块:… -->` 装配注释(那是给模板维护者看的)。
   - **按档案裁剪 §5**:删掉不适用的小节(local 删 §5.1;venv 删 §5.2;docker 删 §5.3),
     §5.0 的档案声明填成选定值。
   - **嵌入 ops 预设**:用 `templates/config/ops-presets/<exec-profile>.md` 的映射表替换 §7.2 的
     OPS-PRESET 占位行(剥预设文件头部装配注释)。
   - 生成顶部 frontmatter(整份文件第一行必须是 `---`):
     `config-version: 2`、`plugin-version`(读 plugin.json)、`modules: [<选中列表>]`、
     `source-dir: <步骤 7 的答案>`;选了 exec 再写 `exec-profile: <步骤 4 的答案>`(未选则不写该行)。
6. **实例化项目工作区骨架**(来自 `${CLAUDE_PLUGIN_ROOT}/templates/project/`,**已存在的文件不覆盖**):
   | 骨架 | 何时装 | 目标路径(约定,可在问答中改) |
   |---|---|---|
   | `directions/_TEMPLATE/`(dossier 目录:direction.md / novelty.md / review.md / pilot.md;gates.jsonl 无实体模板,schema 见 direction.md 末尾注释) | 选了 directions | `docs/directions/_TEMPLATE/` |
   | `RESEARCH_ROADMAP.md` | 选了 directions | `docs/RESEARCH_ROADMAP.md` |
   | `workflow-checklist.md` | 选了 maintenance | `docs/workflow-checklist.md` |
   | `scripts/test-workflow.sh` | 选了 maintenance 或 exec | `scripts/test-workflow.sh`(加执行位) |
   | `scripts/run.sh` | 选了 exec 且档案为 local-*(受控启动器,即 §7.1 通道) | `scripts/run.sh`(加执行位) |
   - 写 `test-workflow.sh` 时把其中的 `__PLUGIN_ROOT__` 占位替换为 `${CLAUDE_PLUGIN_ROOT}` 实际值。
   - **契约探测(目标文件已存在时)**:不覆盖,但探测它是否符合本 plugin 依赖的契约,不符则
     **明确警告"存在但不兼容契约"**(仍不覆盖,建议用户人工合并或改名保留):
     - `test-workflow.sh`:试执行一个子命令看行为(如 `bash <路径> guards`;若退出码 64 且用法串不含
       `guards|sanity|connectivity|ops|all` 五个子命令,即不兼容);
     - `run.sh`:查头注释是否声明受控启动通道契约、用法是否 `[--fg] <训练命令…>` 形态;
     - `workflow-checklist.md`:查是否有 `C1` 起的编号检查项表;
     - `RESEARCH_ROADMAP.md`:查是否含「活跃方向注册表」「已关闭方向的硬约束」两个节标题;
       缺「种子池」节时仅提示可按模板补加(后加的可选节,不构成不兼容);
     - `directions/_TEMPLATE/`:查 direction.md 是否含 slug / 状态 / claims / 子任务 / 结果 等契约字段;
       发现旧的单文件 `_TEMPLATE.md` 时警告"旧契约(单文件形态)",建议迁移为 dossier 目录,不覆盖不删除。
   - 目标路径写进 config 对应段(§10 / §11),保持 config 是事实来源。
7. **填关键值(当场问答,其余留 `<占位>`)**:用 `AskUserQuestion` 逐项问,只问选中模块**及选定档案**
   涉及的。**每一问若有步骤 2 的扫描候选**:候选列为选项、最可能的一项放首位标"(推荐)"并附扫描依据,
   同时始终保留"未确定/其他"出口;无候选才用开放提问。
   - `source-dir`(core,必问):模型源码根相对路径 → 写 frontmatter + §2 `SOURCE_DIR`。
   - 远程句柄(+ remote-docker 加问本地 build 句柄)(exec,仅 remote 档案)→ §5.1。
   - venv/conda 激活方式(exec,仅 venv 运行时)→ §5.3;镜像分层留 §5.2 占位(docker 运行时)。
   - 工作目录(exec,全档案)→ §5.0。
   - tracking 写入端点 + 查看地址(tracking)→ §9。
   - 用户答"未确定"就保留 `<占位>`，不继续追问。其余项目值（镜像名、指标、脚本名、§7.2 ops 映射等）
     均保留模板占位，后续由用户填写或交给 update-workflow 处理；需说明：ops 映射不填时，operator 会拒绝执行
     对应 op(标「不适用」的行除外——那是当前档案没有的动作,operator 会跳过)。
   - 提醒把 §7.1 两组模式写进项目 `.claude/settings.json` 的 `"env"`
     (`RW_TRAIN_PATTERNS` / `RW_EXEC_PATTERN`;未设时 guard 按 `exec-profile` 取内置默认通道模式);
     用户自行添加,或用 `/{{P}}:config set env.RW_EXEC_PATTERN <模式>` 经确认后代写。
8. **收尾校验**:
   - `grep -n '<' .claude/research-bench.config.md` 检查已启用段落的 `<占位>` 残留,
     有则**列清单提醒**（哪一段哪一行），不阻塞初始化；占位允许分批填写。
   - 若启用 exec:实际运行 `scripts/test-workflow.sh guards` 验证 guard hook 生效,
     解读 ✅/❌(❌ = 保护机制没起作用,须先修再用 run-experiment);ops 层此时多为占位,提醒即可
     (标「不适用」的 op 是 ⚠️SKIP,正常)。
   - 输出总结:启用的模块与执行档案 / 生成与跳过的文件(含契约探测警告)/ 待填占位清单 / 下一步建议
     (如"先执行 /rf:analyze-architecture 建架构地图"——该 skill 属于 rf 插件)。

## 规则
- **不覆盖已有内容**:已存在的骨架文件跳过(只做契约探测与警告);增/删模块模式下不动用户已填的正文值。
- **扫描三规则**(步骤 2):只读不写;只扫本地不得联网;结果只作候选与推荐,未经用户确认不进 config。
- 删模块 = 删 config 段 + 更新 frontmatter,**不删**已实例化的项目工作区骨架文件(用户数据);
  删 exec 模块时同时删 frontmatter 的 `exec-profile` 行。
- 本 skill 只写 config 与骨架,不改模型源码、不修改 `.claude/settings.json` 的 permission
  (提醒用户自行添加 env,或转 `/{{P}}:config set env.*` 经确认后代写)。
