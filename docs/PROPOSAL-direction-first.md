# 重构提案:方向优先(direction-first)

> 状态:**提案,待逐条确认**。整合 2026-07 对同类项目的调研
> (ARIS / vibe-science / claude-scholar / autoresearch-claude-code / Zotero MCP 生态),
> 在不推翻 v0.4 四层模型与 DESIGN.md v2 已确认决策的前提下,围绕新的目标重排优先级。
> 经用户确认后,「已确认」条目并入 DESIGN.md,本文件归档。

---

## 1. 目标重述

原目标:把「改架构 → 执行实验 → 记录 → 审计」流程管好。
**新核心目标:找到一个新颖、有实证信号、经得起审稿人攻击的研究方向,并沿它积累够发表的证据。**

诊断:现有方向链路(propose-hypothesis → refine-direction → 注册表)是**内生**的——
假设只从自己的实验证据里长出来,方向从卡片直接进注册表。对发论文目标缺三样**外生**输入:

| 缺口 | 后果 | 借鉴来源 |
|---|---|---|
| 文献地图 | 「对我们的模型有效」≠「值得发论文」,不知领域缺口在哪 | claude-scholar literature-reviewer |
| 新颖性验证 | 可能花数月做出已发表的东西,无任何机制拦截 | ARIS novelty-check 四阶段协议 |
| 廉价实证信号 | 实验只有 smoke(能跑)和 launch(全量)两档,方向定错要全量代价才知道 | ARIS pilot 预算封顶 |
| 对抗审查 | auditor 只查完整性,没人扮演审稿人攻击方向价值 | ARIS research-review / vibe-science R2 |

Experiment Flow (operator / ISA / 租约 / guard)是相对同类项目的独有优势,**不动**。

## 2. 借鉴机制 ↔ 设计哲学对照

只引进与现有哲学同构的机制;载体一律落在已有原语上,不引进新运行时。

| 借鉴 | 机制 | 对齐的哲学 | 载体 |
|---|---|---|---|
| ARIS novelty-check | 四阶段查新:主张提取 → 多源检索(≥3 种表述,近 6 月 arXiv)→ 跨模型交叉验证 → 分级判定 + 最接近前期工作表 | 判断交给模型,**裁决与执行交给脚本**(引用可解析性是机械判定) | 新 skill + 协议文档 |
| ARIS 反幻觉协议 | 引用必须可解析验证,否则标 `[UNVERIFIED]` | 同上;证据协议「记忆/印象禁止作为证据」的既有条款 | **Zotero 落库即验证**(见 §6) |
| ARIS pilot | 预算封顶的试点实验,按实证信号淘汰弱想法 | 意图与执行分离;plugin 只带接口约定,预算裁决在项目训练封装中完成 | run-experiment 的 pilot 变体(见 §7) |
| ARIS IDEA_REPORT | 单一 canonical 档案折叠所有关卡产出,淘汰想法也记录 | 机器可读与人可读分离;教训库既有理念 | 方向档案目录(见 §5) |
| ARIS 跨模型审查 | 外部模型家族做对抗审查,避开自我偏好局部最优 | 职责边界清晰;**能「否」不能「准」**(auditor→strategist 单向流的既有先例) | reviewer 角色 + Codex 通道(见 §8) |
| vibe-science claim 账本 | 定量声明有生命周期,关卡通过/失败留痕,hook/脚本可机械查询 | 状态文件是完整事实来源(DESIGN §3.2 会话策略) | claims 表 + gates.jsonl(见 §5、§9) |
| vibe-science 权力分离 | 审查者产出裁决但不能写入账本 | 保护机制不可自动削弱 | reviewer 无写工具 |
| claude-scholar Zotero 集合化 | 检索结果持久化进文献库,按主题建集合,下次不重查 | 通用方法与项目配置分离(集合约定进 config) | Zotero MCP(见 §6) |
| claude-scholar 证据晋升门槛 | 弱来源/假设/缺失证据显式标注,不达标不晋升 | 证据协议过期判定的同族规则 | 方向状态机(见 §4) |
| autoresearch JSONL | 追加式状态,git 可 diff、jq 可查、bash 可读 | 机器可读与人可读分离;零依赖 | gates.jsonl / DESIGN §3.5 状态文件 |

**明确不引进**:vibe-science 的 npm+SQLite 运行时(违背零依赖与 git 审计路线;其数据模型抄、载体换 JSONL,量级不够不迁库)、ARIS 的 74-skill 铺开与论文全链(写作/rebuttal/海报等,维持 DESIGN §1.1「暂不扩展」)。

## 3. 新模块:discovery

按模块化启用哲学,新增第 7 个模块,不塞进 directions:

- **依赖**:`core` 必需;`directions` 强烈建议(关卡产出的落点);`exec` 可选(pilot 关卡)。
- **配置段**:新增 **§12 方向发现**(§ 编号锚点规则不变,未启用整段缺席):
  - Zotero MCP 端点与集合约定(`directions/<slug>` 每方向一集合);未配置时的降级声明
  - Codex 通道:主流程调用方式;未配置时降级为独立 reviewer agent 冷上下文审查
  - pilot 预算:`PILOT_MAX_HOURS` / `MAX_TOTAL_GPU_HOURS` 等 env 名(登记进 §7.2 由训练封装读取)
  - 查新参数:检索源清单、近月窗口、判定阈值
- **新 skill**(沿用动宾命名):
  - `survey-literature`:结构化文献调研 → 文献地图 + Zotero 集合落库(委托 strategist,扩展其证据协议)
  - `check-novelty`:四阶段查新 → 新颖性档案(主流程检索 + Codex 交叉验证)
  - `close-direction`:方向关闭 + 教训库回写(顺带解决 DESIGN §7 已知问题「方向生命周期缺关闭动作」)
- **新协议文档**:`references/novelty-protocol.md`(四阶段流程、反幻觉规则、判定标准——
  含「应用 X 于 Y 不构成创新」等;与 evidence-protocol 同级,被 skill/agent 引用不内联)

## 4. 方向生命周期:登记制 → 关卡制

新方向进注册表前必须过三关;关卡裁决写入方向档案的 `gates.jsonl`,**裁决判定交脚本**:

```
种子(propose-hypothesis 发散 / 用户直给)
  → survey-literature   文献地图,Zotero 集合建立
  → 关卡 1 check-novelty  新颖性分级 + 最接近前期工作表(每行带 Zotero key)
  → 关卡 2 pilot          预算封顶试点,实证信号分级(可跳过,跳过须记录理由)
  → 关卡 3 review         对抗审查评分(Codex 通道,阈值可配)
  → refine-direction      收敛(吸收三关产出,现有八维流程不变)
  → update-workflow       落方向档案 + 登记注册表(仍需用户确认——外部裁决能「否」不能「准」)
  → modify-architecture → run-experiment 全量 → audit-results(按 claims 查缺口,见 §5)
  → close-direction       成立并回 / 证伪关闭,教训回写
```

- 状态机(方向档案 frontmatter `status`):`seed → surveyed → novelty-checked → piloted → reviewed → active → closed(published | falsified | superseded)`。
- **机械强制点**:`select_direction.py`(config §10 已有)扩展为同时检查 `gates.jsonl`——
  全量实验选方向时,方向未过三关(或无跳过记录)则拒绝。复用「驱动层脚本裁决」,**不加新 hook**。
- 关卡阈值写在 config §12,修改属于「削弱检查标准」,受既有「显式说明 + 用户确认」约束。
- 任何一关淘汰的想法:淘汰理由 + 依据(撞车论文的 Zotero key / pilot 数据 / 审查意见)回写教训库。
  「已被某论文做过」正式成为教训库条目类型。

## 5. 方向档案:单文件 → 目录(dossier)

`docs/directions/<slug>.md` 升级为 `docs/directions/<slug>/`:

```
docs/directions/<slug>/
├── direction.md      # 主档案(原 _TEMPLATE 字段 + 新增节,注册表锚点)
├── novelty.md        # 新颖性档案(关卡 1 产出:主张分级、前期工作表、Codex 交叉验证原文)
├── review.md         # 对抗审查记录(关卡 3 产出:评分、薄弱论点、逐轮迭代)
├── pilot.md          # 试点结果(关卡 2 产出;跳过时记理由)
└── gates.jsonl       # 关卡账本(机器可读:{gate, verdict, score, ts, evidence_ptr})
```

`direction.md` 在现有字段(核心诊断三件套 / slug / flag / baseline_group / access_level)上新增:

- **claims 表**(论文接口,vibe-science claim 账本的 markdown 形态):
  `| claim | 支撑实验(config 名) | 状态(planned/running/done) | 证据指针(汇总表行/tracking run) |`
  ——格式沿用 §7.2 ops 表被 `test-workflow.sh` 行解析的先例,脚本可机械读。
- **Zotero 集合指针** + 关键引用 key 清单。

`audit-results` 升级:在现有完整性核查外,新增「**投稿缺口报告**」模式——按 claims 表逐行核对
证据状态,输出「离能投稿还差哪些实验」。auditor 职责不变(核查,不提方向),单向流不变。

## 6. Zotero 集成(文献证据基座)

- **接入**:cookjohn/zotero-mcp(.xpi,MCP server 内置于 Zotero,零外部进程,全读写)起步;
  需要语义检索再叠 54yyyu/zotero-mcp。接入方式属项目事实,写 config §12,plugin 只写方法论。
- **反幻觉的机械化**:引用「验证」的定义 = **按 DOI/arXiv id 成功导入 Zotero**
  (导入即解析验证)。novelty.md 前期工作表每行必须带 Zotero key,幻觉引用物理过不去。
  无 Zotero 时降级为 ARIS 三层核验(arXiv/CrossRef/Semantic Scholar)+ `[UNVERIFIED]` 标记。
- **evidence-protocol.md 扩展**:读取清单新增「§12 Zotero 文献库(经 MCP 检索)」;
  数据源优先级补文献维度:**用户粘贴 > Zotero 库内已验证条目 > web 检索结果(未落库前视为未验证)**。
- strategist 假设卡片的文献支撑优先引库内条目;survey-literature 的检索产出以落库为完成标志。

## 7. pilot 档位(exec 模块扩展)

- **不新增 ISA op**。pilot = run-experiment 的一种实验 config 约定:小 epochs、
  预算 env(`PILOT_MAX_HOURS` 等,config §12 定义、§7.2 登记),走**同一受控通道、同一 op 序列**,
  租约与 guard 照常生效——「可复现的廉价试点」是相对 ARIS 裸 SSH 的差异化优势。
- 预算裁决在项目训练封装中完成(读 env 超时自停),plugin 只在接口约定文档里写契约
  ——遵「plugin 不内置项目运行时」。
- pilot 结果不进论文级消融表,只进 pilot.md + gates.jsonl;tracking 记录加 `pilot` 标记以防混入。

## 8. reviewer:第 6 个服务角色

| 服务 | 职责 | 工具范围 | 记忆策略 |
|---|---|---|---|
| `reviewer` | 以顶会审稿人立场攻击方向:新颖性交叉验证 + 价值/薄弱论点评分 | 只读 + WebSearch/WebFetch,**无写工具**;Codex 裁决由主流程传入 | 无记忆;裁决写入档案由主流程代笔 |

- 与现有角色的边界:strategist **生成**(建设立场)、auditor **核查完整性**(内部证据)、
  reviewer **攻击价值**(外部对标)。reviewer 不提新方向、不重查完整性;
  裁决可作为 strategist/refine-direction 输入——单向流扩展为 `auditor → strategist ← reviewer`。
- **跨模型加强**:config §12 配了 Codex 通道时,主流程把新颖性档案/方向档案发给 Codex
  按固定问题清单(新颖吗/最接近工作/差异何在/评分 X/10)取回裁决,再交给 reviewer 与自身结论**双签**进档案;
  未配置时独立冷上下文执行。裁决只是输入,注册表写入仍走 update-workflow + 用户确认。

## 9. 与 DESIGN.md v2 的关系

- 不冲突:v2 编排层(迭代①骨干/②探针看门狗/③闭环)照旧;discovery 关卡链就是编排层
  「调研 → plan」阶段的具体实现,`loop(n)` 档下 strategist 建议自动进下一轮时,三关照过。
- gates.jsonl 与 §3.5 状态文件(`plan.md + todo.yaml`)同族:前者是方向级、后者是流水线级,
  都服务「冷启动恢复 + 审计」。
- **优先级调整建议**:对发论文目标,discovery 先于迭代②(探针/看门狗)——方向错了,
  看护自动化只是更高效地烧错误的实验。建议插入为「迭代 D」,置于迭代①之后、②之前。

## 10. 文件级改动清单

| 动作 | 路径 | 说明 |
|---|---|---|
| 新增 | `agents/reviewer.md` | §8 |
| 新增 | `skills/survey-literature/` `skills/check-novelty/` `skills/close-direction/` | §3 |
| 新增 | `references/novelty-protocol.md` | 四阶段 + 反幻觉 + 判定标准 |
| 新增 | `templates/config/60-discovery.md` | 配置 §12 |
| 修改 | `references/evidence-protocol.md` | 文献层 + 优先级(§6) |
| 重构 | `templates/project/directions/_TEMPLATE.md` → dossier 目录模板 | §5;init 实例化逻辑随之改 |
| 修改 | `skills/propose-hypothesis` `skills/refine-direction` | 接入三关产出;refine 八维流程不变 |
| 修改 | `skills/run-experiment` + `templates/config/10-exec.md` | pilot 约定(§7);select_direction 契约扩展(查 gates) |
| 修改 | `skills/audit-results` + `agents/auditor.md` | 投稿缺口报告模式(§5) |
| 修改 | `agents/strategist.md` | 文献基座 + 教训库新条目类型 |
| 修改 | `skills/init` `skills/config` | discovery 模块装配;§12 关键值 |
| 修改 | `templates/project/scripts/test-workflow.sh` | ops 层补 gates.jsonl 存在性/格式断言 |
| 不动 | `hooks/*` `agents/operator.md` `skills/build-env` `deploy-env` 等 Experiment Flow 组件 | 护城河 |

## 11. 实施顺序建议

| 批次 | 内容 | 理由 |
|---|---|---|
| P0 | `check-novelty` + novelty-protocol + Zotero 接入(config §12 最小版) | 性价比最高:立即防撞车,当天可用于筛现有候选方向 |
| P1 | `reviewer` 角色 + Codex 通道 + dossier 目录 + gates.jsonl(关卡制最小版:查新+审查两关,pilot 关人工判) | 三关制成形 |
| P2 | pilot 约定 + select_direction 契约扩展 | 依赖 exec,涉及项目训练封装 |
| P3 | claims 表 + audit-results 投稿缺口报告 | 收尾论文接口 |
| P4 | `close-direction` 教训回写 + survey-literature 完整版 | 闭环 |

## 12. 分层归位(已确认)

**不为 discovery 新增架构层**,四层模型直接吸收:

| 层 | discovery 新增 |
|---|---|
| L3 意图层 | `survey-literature` / `check-novelty` / `close-direction` |
| L2 服务层 | `reviewer`(第 6 角色);strategist 扩证据基座 |
| L1 驱动层 | `select_direction.py` 扩 gates 检查;训练封装读 pilot 预算 env |
| L0 机制层 | `gates.jsonl`(与 manifest 同类:被脚本机械读取的事实,schema 稳定、受「不可自动削弱」约束)+ 配置 §12 |

三条附属结论:

1. **外部依赖类别显性化**:Zotero MCP / Codex MCP 沿用 tracking 系统与远程 daemon 的既有待遇
   ——端点写 config、connectivity 层只读探测、缺席必须有降级路径;不是新层,是「外部依赖」类别的新成员。
2. **场景预设**:模块轴继续承担功能档次分层;init 新增三个组合预设(选完可微调)——
   「找方向包」core+directions+discovery(无 exec,pilot 关降级人工判)/「执行包」core+exec+data+tracking /
   「全家桶」全模块。服务阶段二 onboarding:第一问从「要哪 7 个模块」变成「处在研究哪个阶段」。
3. **关卡与档位正交**:三关制(证据够不够)与 DESIGN §3.1 四档位(每步谁确认)是两个轴,不合并。
   `loop(n)` 全自动档下三关照过;auto/loop 档下跳关必须留 gates.jsonl 记录并计入下轮审计,不允许静默跳。

## 13. 待确认事项

> 2026-07-05:用户确认按提案默认值动工(P0→P1 先行);下列项按提案推荐取默认,实施后仍可调。

- [ ] 模块名 `discovery` 与配置段号 §12
- [ ] 方向档案由单文件改目录(牵连 init/registry/现有项目迁移)
- [ ] reviewer 立为第 6 角色(vs 并入 strategist 的一个模式)
- [ ] 三关阈值默认值(novelty 分级门槛 / review 分数线,ARIS 用 ≥9/10)与「跳过 pilot」的允许条件
- [ ] gates.jsonl 字段 schema
- [ ] Zotero MCP 选型最终定夺(xpi 起步?)与无 Zotero 降级体验的验收标准
- [ ] 迭代 D 插入 v2 路线的位置(①后②前?)
