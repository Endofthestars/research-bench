# 新插件提案:pub-flow(pf,论文写作工作流)

> 状态:**已被用户决策取代(2026-07-08)**——pf 不走本提案的「自研最小闭环」路线,
> 改为**完整 fork ARS + 本土改造**(见下方「v2 决议」;落地记录见 `pub-flow/UPSTREAM.md`)。
> 正文(§1–§10)保留作为对 ARS 的机制调研记录,其中自研实施细节(§4–§6、§9)不再执行。

## v2 决议(fork 方案要点,2026-07-08)

- **引入方式**:把 ARS v3.15.0(commit `becfcc40c6e9e93c187cf4a088333f83373e002d`)完整
  fork 进 `pub-flow/`,保留英文原版 skill 与上游目录布局(skills/ 符号链接),排除
  tests/evals/audits/examples/CI 等非运行时内容;版本号跟随上游(3.15.0),
  排除集与同步流程见 `pub-flow/UPSTREAM.md`。
- **许可证边界**:本提案 §2「只借鉴机制、零文本复制」的前提随 fork 决策失效——
  改为 `pub-flow/` 子树整体沿用 CC-BY-NC 4.0(禁商用,署名 Cheng-I Wu),
  仓库其余部分仍 MIT;README §9 已改为混合许可声明。
- **本土改造原则**:新增文件优先,尽量不改上游原文(唯一必改项 plugin.json 的
  name/description);pf 不参与 shared/ 单一事实来源体系,也不新增 config §13 分片。
- **桥接层**:新增中文原创 skill `dossier-bridge`(+ 同名 command 薄壳),把 rf 方向
  dossier 的 claims / novelty / review 素材整理成英文素材包写入
  `docs/paper/<paper-slug>/materials.md`,再交给 ARS 的 `/pf:ars-plan`、`/pf:ars-outline`、
  `/pf:ars-full` 等入口消费。
- **与 rf 的接口不变**:仍是本提案 §7 的契约——pf 只读 dossier(路径从 config §10 读,
  Zotero 集合约定从 §12.1 读,缺席降级为手填素材),只写稿件工作区;引用一律带
  Zotero key,无 key 标 `[UNVERIFIED]`。

---

## 1. 目标重述与 DESIGN 的关系

DESIGN.md §1.1 原文:「能力范围:**暂不扩展**——论文产出支持、多人协作等留待后续版本」。
**本提案正式推翻其中「论文产出支持」一条**(用户已拍板):direction-first 落地后,
方向 dossier 已经积累了 claims 表、新颖性档案、对抗审查记录和 Zotero 文献库——
「够发表的证据」有了机器可读的账本,却没有把它变成稿件的通道。缺口不再是「要不要做」,
而是「证据链的最后一公里」。

| 缺口 | 后果 | 借鉴来源 |
|---|---|---|
| 起草通道 | claims 表攒齐了,论文仍要人从零手写,dossier 的结构化优势用不上 | ARS 写作流水线(大纲 → 逐节 → 自查) |
| 稿件忠实性 | 稿子里的主张可能悄悄超出证据(主张漂移),无人核对 claims 表 | ARS L3 主张忠实性审计 |
| 引用防伪(稿件侧) | 查新阶段引用有 Zotero 关卡,写作阶段新引入的引用没有 | ARS 完整性关卡 2.5(引用防伪) |
| 投稿前关卡 | audit-results 查的是实验完整性,没人在投稿前把稿件整体过一遍 | ARS 不可跳过的完整性关卡 |

**边界**:pf 只做「写与审」;实验证据的生产(ef)、方向与查新(rf)不动。
本提案确认后需同步修订 DESIGN §1.1(改为「论文产出支持由 pf 插件承担」),
并在 PROPOSAL-direction-first §2 归档时注明其「维持 §1.1 暂不扩展」括注已被本提案取代。

## 2. 许可证约束(硬)

本仓库 MIT,ARS 是 CC-BY-NC 4.0,两者不兼容。约束与执行方式:

- **只借鉴机制设计,零文本复制**:全部 skill / agent / 模板 / 协议文档中文原创重写;
  不复制 ARS 的任何 prompt 文本、清单条目原文、代码或 schema 字段名。
  机制思想(流水线阶段划分、审计维度、反谄媚规则)不在版权保护范围,借鉴合法。
- **致谢**:README 许可证节(现第 451 行附近)与本文档标注「pf 的机制设计借鉴
  ARS(CC-BY-NC 4.0,仅借鉴机制、无文本复制)」并附仓库链接;不进插件运行文件。
- 实施期间自查:任何「照着 ARS 某文件改写」的动作都不允许——只允许照着**本提案的中文描述**实现。

## 3. 借鉴机制 ↔ 设计哲学对照

沿用 direction-first §2 的原则:只引进与现有哲学同构的机制,载体一律落在已有原语上。

| 借鉴 | 机制 | 对齐的哲学 | 载体 |
|---|---|---|---|
| Material Passport | 跨会话账本:文献库、主张清单 + 实验溯源、合规历史 | 状态文件是完整事实来源 | **不新建账本**——方向 dossier(claims 表 + gates.jsonl + Zotero 集合)就是我们的 passport;pf 稿件 manifest 只存指针(见 §7) |
| 四索引引用防伪 | Semantic Scholar / OpenAlex / Crossref / arXiv 交叉核验 | 裁决交给脚本(引用可解析性是机械判定) | 已有的 **Zotero 落库即验证** + `[UNVERIFIED]` 降级(novelty-protocol §2),pf 引用关卡直接复用同一判定,不再造第二套 |
| L3 主张忠实性审计 | 取回被引来源,判断是否真的支撑主张(quote/page/section 三层锚点) | 证据协议「记忆/印象禁止作为证据」 | `audit-manuscript`:稿件主张 ↔ claims 表行 ↔ 证据指针(汇总表行 / tracking run)逐条对账;文献主张对 Zotero 条目(锚点简化为 key + 可选章节,见 §6.2) |
| EIC + 3 动态审稿人 + Devil's Advocate | 多角色对抗评审,0–100 分映射 Accept/Minor/Major | 角色最小集;冷上下文盲评已有先例(rf reviewer 两段式) | pf 自带**一个**同族对抗角色(critic,见 §6.3),后续批次的 review-paper 复用;不搞 12-agent 流水线 |
| 完整性关卡 2.5 / 4.5 | 不可跳过的主张审计 + 回归检测 | 关卡制 + 跳关必须留痕(config §12.4 既有条款) | `audit-manuscript` = 投稿前关卡;裁决行追加进稿件侧账本(见 §13 待确认),跳过须记理由 |
| 反谄媚审稿 | 审稿人先给 rebuttal 评分才能让步,禁止连续让步 | reviewer「推翻初判须说明原因,不得静默改口」同族 | 后续批次(review-paper / rebuttal)采纳,首批不实现 |
| R&R 追踪矩阵 | 审稿意见 → 修改 → 回应逐行追踪 | markdown 表 + 脚本行解析先例(§7.2 ops 表、claims 表) | 后续批次 track-revision 的 markdown 矩阵 |
| 写作质量自查 | 检测机器味行文模式;风格校准(学用户既往作品) | 判断交给模型,清单进协议文档不内联 | `references/writing-protocol.md` 自查清单;风格样本路径进 config §13,未配置整键缺席 |
| 时间完整性审计 | 5 类时间性失效(回溯算术、时代错置引用等) | 同上 | writing-protocol 的一节检查维度,audit-manuscript 引用,不单独成 skill |

**明确不引进**(逐条理由):

- **Python + SQLite 运行时**:违背零依赖与 git 可审计路线(direction-first 对 vibe-science
  npm+SQLite 的同一处置);数据量级用 markdown 表 + JSONL 足够。
- **4 巨型 skill / 27 模式铺开**:违背「职责单一」与三件套约定;模式选择成本转嫁给用户。
  我们按动宾命名一事一 skill,模块化启用。
- **12-agent 评审流水线**:冷上下文两段式盲评已覆盖对抗价值的核心(防锚定、防谄媚),
  多审稿人角色扮演是 token 成本的线性放大,无证据表明裁决质量随之线性提升。
- **VLM 图表核验**:图表与数据的一致性没有稳定的机械判定,「判断交模型、裁决交脚本」拆不开;
  我们的图表事实来源是 tracking / 结果汇总表,核对入口在数据侧(audit-results)而非像素侧。
- **0–100 评分映射 Accept/Minor/Major**:已有 X/10 分数线体系(config §12.4),不并存两套评分制。
- **ARS 任何原文**:见 §2 许可证硬约束。

## 4. 插件形态与 shared 参与度

### 4.1 目录结构(与 rf / ef 同构)

```
pub-flow/
├── .claude-plugin/plugin.json     # name: pf, version 0.1.0
├── commands/                      # 薄壳:draft-paper、audit-manuscript + shared 渲染的 init/config/settings/update-workflow
├── skills/                        # draft-paper/、audit-manuscript/ + shared 渲染的四件
├── agents/                        # writer.md、critic.md(见 §6.3)
├── hooks/                         # hooks.json + shared 渲染的 session-init-check.sh
├── references/                    # writing-protocol.md(机器味清单 + 时间完整性清单 + 引用规则引 novelty-protocol)
└── templates/                     # shared 渲染的 config 分片全套 + pf 特有 paper 骨架
```

marketplace.json 增加第三个条目(`"name": "pf", "source": "./pub-flow"`),
metadata 描述改为三插件措辞。

### 4.2 shared 参与度(通读 sync-shared.sh 后的判断)

`scripts/sync-shared.sh` 的插件清单是脚本内一行 pair 列表(`"rf:res-flow" "ef:exp-flow"`),
**加入 pf = 加一个 `"pf:pub-flow"` 条目,改造成本一行**;但脚本现状是「shared 全集渲染到每个插件」,
无按文件适用范围的机制。逐类评估 shared 全集(30 文件)对 pf 的意义:

| shared 内容 | pf 要不要 | 理由 |
|---|---|---|
| skills/commands:init、config、settings、update-workflow | **要** | config 契约三插件共用一份 `.claude/research-bench.config.md`,pf 单独安装时也要能初始化/改值 |
| hooks/session-init-check.sh | **要** | 会话入口检查 config 存在性,插件通用 |
| templates/config/ 全套分片 + ops-presets | **要(全套)** | init 是「装配任意模块」的通用入口,任一插件的 init 都可能被用来启用任意模块段——rf 现状也带着 10-exec 与 ops-presets,先例一致 |
| templates/project/ 骨架 | **要** | 同上,init 实例化需要 |
| agents:operator、steward;skills/commands:audit-workflow | **不要** | 纯 exec / maintenance 执行件,pf 无消费方;steward 被排除则委托它的 audit-workflow 一并排除 |

**建议方案**:pf 加入 shared,sync-shared.sh 增加**最小排除机制**——脚本内一个
per-plugin 排除清单变量(如 `EXCLUDE_pf="agents/operator.md agents/steward.md
skills/audit-workflow/ commands/audit-workflow.md"`),渲染循环跳过命中项,`--check` 同步跳过;
改动约 10 行。备选是全量加入零排除(先例:rf 目录里本来就渲染着 operator.md),
代价是 pf 用户的 agent 列表出现两个永远用不上的角色——两案都可行,取舍列入 §13。

shared 的 init/SKILL.md 模块一览表需加 `publication` 一行(标注其 skill 属 pf 插件,
与 discovery 行标注 rf 的先例一致);这是对 shared 的修改,随本提案实施、三插件同步渲染。

## 5. 配置契约:§13 publication

沿用项目侧 `.claude/research-bench.config.md`。现有段号 §1–§12 已满
(§12 = discovery,templates/config/60-discovery.md),**下一个可用编号为 §13**,
新增分片 `shared/templates/config/70-publication.md`;00-core.md 头部注释的
「§ 编号是全局稳定锚点(§1–§12)」同步改为 §1–§13。未启用 publication 模块时整段缺席,不重排。

- **模块依赖**:`core` 必需;`directions` + `discovery` 强烈建议(素材与引用验证的来源);
  均缺席时走 §8 降级路径。
- **§13.1 投稿目标**:目标 venue / 页数限制 / 匿名要求 / venue 模板指针。
- **§13.2 稿件工作区**:路径约定(默认 `docs/paper/<paper-slug>/`);素材来源声明
  (方向 dossier 清单,或降级的手填素材清单路径)。
- **§13.3 写作约束与风格**:语言;风格校准样本路径(用户既往作品,未配置整键缺席,
  writer 则只按 writing-protocol 通用规则);引用规则指针(= §12.1 Zotero 约定,
  未启用 discovery 时降级三层核验 + `[UNVERIFIED]`)。
- **§13.4 格式产物(可选依赖)**:Pandoc / LaTeX 命令与模板路径;未配置 → 只产 markdown,
  export 类动作提示缺依赖(与 tracking 端点、Zotero MCP 的「外部依赖」待遇一致:
  端点写 config、缺席必须有降级路径)。
- **§13.5 审计标准(保护条款,不可自动削弱)**:audit-manuscript 的判定标准与跳关记录要求;
  修改须显式说明并经用户确认,沿用 §12.4 措辞族。

## 6. 首批范围 = 最小闭环(起草 + 审计)

### 6.1 skill `draft-paper`(委托 writer)

- **输入**:方向 dossier(status: active,claims 表含 done 行)+ novelty.md + review.md
  + Zotero 集合;多方向合一篇时输入为 dossier 清单。无 rf 时走 §8 降级。
- **三阶段,阶段间用户确认**(不一口气生成全文):
  1. **大纲**:从 claims 表反推论文骨架(每条 done claim 落到哪一节、用哪个证据指针),
     产出 `outline.md`,用户确认后才进下一阶段;
  2. **逐节起草**:一节一轮,引用**必须带 Zotero key**(格式沿 novelty.md 前期工作表先例),
     写作时新引入而未落库的引用标 `[UNVERIFIED]`;定量陈述只允许来自 claims 表证据指针
     指向的数据,禁止「印象值」;
  3. **自查**:按 `references/writing-protocol.md` 过机器味清单(借鉴 ARS 写作质量自查,
     清单中文原创)与时间完整性清单,逐条标注命中与修改。
- **产出**:`docs/paper/<paper-slug>/{paper.md(manifest,frontmatter 存方向指针), outline.md, draft.md}`。
- **约束**:writer 只写稿件工作区,不碰源码 / dossier / 注册表(dossier 回写仍走 update-workflow)。

### 6.2 skill `audit-manuscript`(投稿前关卡,委托 critic)

三个维度,产出**投稿前缺口报告**(`docs/paper/<paper-slug>/audit.md`):

1. **主张忠实性**(借鉴 ARS L3):稿件逐条定量/贡献主张 ↔ claims 表行 ↔ 证据指针,
   三种裁决:有据 / 超出证据(主张漂移,标原文与超出部分)/ 无对应 claim(要么补实验要么删句)。
   锚点用我们已有的证据指针(汇总表行 / tracking run),不引进 quote/page/section 三层
   ——实验论文主张的证据是自家实验;文献性主张对 Zotero 条目核对,锚点 = key + 可选章节。
2. **引用存在性关卡**:draft.md 每个引用 key ↔ Zotero 库条目逐一比对;`[UNVERIFIED]`
   与查无此 key 的引用逐条列出。key 提取与比对是机械动作,可由脚本断言(后续并入
   test-workflow 的一层,首批先由 skill 内固定步骤执行)。
3. **时间完整性**:按 writing-protocol 清单轻量过一遍(引用年代 vs 主张时序等)。

报告格式衔接 rf audit-results 的「投稿缺口报告」模式(direction-first §5 规划、
**尚未实施**):audit-results 从方向侧答「离能投稿还差哪些实验」,audit-manuscript 从稿件侧答
「稿子里哪些话没有证据/引用撑腰」,两侧共用 claims 表这一个接口。分工与单向流:
稿件附带 auditor 结论时 critic 只消费不复核,互不越界。

### 6.3 最小 agent 集合:writer + critic

| 服务 | 职责 | 工具范围 | 记忆策略 |
|---|---|---|---|
| `writer` | 三阶段起草;风格校准;自查清单执行 | 只读证据基座 + **写稿件工作区**(仅 §13.2 路径) | 无记忆;素材由主流程按证据协议喂入 |
| `critic` | pf 版对抗审稿人:首批承担 audit-manuscript 的忠实性/引用裁决;后续批次承担 review-paper 盲评 | 只读 + WebSearch/WebFetch,**无写工具** | 无记忆,冷上下文;裁决文本交回主流程代笔 |

critic 完整复用 rf reviewer 的设计族:两类任务由委托时指定、两段式盲评协议(后续批次启用)、
能「否」不能「准」、权力分离(裁决不碰账本)、引用可验证。不复用 rf reviewer 本体
——pf 须自包含安装,且送审对象(稿件 vs 方向)与判定标准(§13.5 vs §12.4)不同。
两角色单向流:critic 产出 → writer 消费修订,writer 不反向评审 critic。

## 7. 与 rf 的接口(跨插件契约)

**只做文件路径约定,不做代码级耦合**——pf 读 rf 的产物文件,不调用 rf 的 skill/agent:

- **输入契约**:`docs/directions/<slug>/`(路径从 config §10 读)下
  `direction.md`(frontmatter `status: active`;claims 表 `status=done` 行且证据指针非空)、
  `novelty.md`、`review.md`、`gates.jsonl`;Zotero 集合约定从 §12.1 读。
  字段名(slug / status / claims 列结构)是既有接口契约(direction.md 模板头部已声明不可改名),
  pf 成为其新增消费方。
- **方向性**:pf 只读 dossier,不写;论文进度回写 dossier 的「结论 / 论文落点」节
  仍走 rf 的 update-workflow + 用户确认。paper.md manifest 存方向 slug 指针,不复制内容。
- **降级路径(无 rf / 未启用 directions)**:draft-paper 提示后改用**手填素材清单**
  ——pf 自带 `templates/paper/materials.md` 骨架(主张表:一行一主张 + 证据出处 + 引用 key,
  列结构与 claims 表同族),用户填好后同一流程照走;audit-manuscript 对账对象换成该清单。
  无 Zotero 时引用核验降级与 §12.1 条款一致。

## 8. 后续批次(按性价比排序)

| 批次 | 内容 | 理由 |
|---|---|---|
| P0(本提案首批) | draft-paper + audit-manuscript + writer/critic + config §13 + writing-protocol | 最小闭环:能起草、能对账,当天可用 |
| P1 | `review-paper` 审稿环:critic 两段式盲评稿件、X/10 分数线、反谄媚让步规则 | 投稿前自攻性价比最高;复用 critic,零新角色 |
| P2 | `track-revision`:R&R 追踪矩阵(markdown 表,审稿意见 → 修改 → 回应逐行),回归复查(改动是否引入新漂移,借鉴 ARS 关卡 4.5) | 收到审稿意见后才需要,时序靠后 |
| P3 | `export-paper`:Pandoc/LaTeX 格式转换(§13.4 可选依赖)+ 引用规范化 | 纯格式层,外部依赖,markdown 阶段可手工替代 |
| P4 | rebuttal 辅导 + 披露声明生成 | 频次最低;反谄媚规则在 P1 已进 critic,此处只是应用面扩展 |

## 9. 文件级改动清单(首批)

| 动作 | 路径 | 说明 |
|---|---|---|
| 新增 | `pub-flow/` 整目录 | §4.1;plugin.json name=pf |
| 新增 | `pub-flow/skills/draft-paper/` `audit-manuscript/` + 同名 commands 薄壳 | §6.1–6.2 |
| 新增 | `pub-flow/agents/writer.md` `critic.md` | §6.3 |
| 新增 | `pub-flow/references/writing-protocol.md` | 机器味 + 时间完整性清单(中文原创) |
| 新增 | `pub-flow/templates/paper/`(paper.md / materials.md 骨架) | §6.1、§7 降级 |
| 新增 | `shared/templates/config/70-publication.md` | §5(渲染进三插件) |
| 修改 | `scripts/sync-shared.sh` | pair 加 `pf:pub-flow` + 最小排除机制(§4.2) |
| 修改 | `shared/skills/init/SKILL.md`(模块表 + 装配清单)、`shared/templates/config/00-core.md`(锚点注释 §13) | §5 |
| 修改 | `.claude-plugin/marketplace.json`、`README.md`(第三插件 + ARS 致谢)、`.claude/agents/plugin-dev.md`(纳入 pf) | §2、§4 |
| 修改 | `docs/DESIGN.md` §1.1 | §1(经确认后) |
| 不动 | rf / ef 的全部现有 skill、agent、hook | pf 只读接口文件 |

## 10. 待确认事项

- [ ] 插件名 `pub-flow`(缩写 pf) vs `paper-flow`;命令前缀 `/pf:`
- [ ] 配置段号 §13、模块名 `publication`、分片文件名 `70-publication.md`
- [ ] shared 参与度:最小排除机制(推荐) vs 全量加入(rf 带 operator 的先例);排除集是否含 audit-workflow
- [ ] agent 命名:`writer` + `critic`(vs `referee`;以及 critic 与 rf reviewer 名称区分度是否足够)
- [ ] 稿件工作区 `docs/paper/<paper-slug>/` 与 paper-slug 语义(一篇论文可并多个方向,不等同方向 slug)
- [ ] 稿件侧关卡留痕:paper 目录自带 gates.jsonl(与方向侧 schema 同族) vs 只写 audit.md
- [ ] writing-protocol.md 初版收录的机器味模式与时间完整性检查范围
- [ ] 与 rf audit-results「投稿缺口报告」模式(direction-first P3,尚未实施)的实施先后与格式对齐
- [ ] 首批版本号 0.1.0 与 marketplace 三插件描述措辞
