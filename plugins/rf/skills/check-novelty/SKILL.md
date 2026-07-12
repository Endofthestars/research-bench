---
name: check-novelty
description: 对一个候选研究方向执行四阶段查新：核心主张提取、多源检索、跨模型交叉验证和分级判定，产出新颖性档案与关卡记录。适用于方向进注册表前的撞车拦截，或为已有方向补查新颖性。
---

# 查新（关卡 1：四阶段新颖性验证）

> **宿主兼容（必读）**：开始前读取 `../../references/host-compatibility.md`；委托 `reviewer` 时
> 按该协议选择子代理或主流程回退。

对**一个**候选方向执行查新。流程、反幻觉规则与判定标准**以
`<PLUGIN_ROOT>/references/novelty-protocol.md` 为唯一依据**（四阶段 / 引用可验证性 /
「应用 X 于 Y 不构成创新」等判定标准均在协议里，本 skill 只做编排，不重复内联）。

> **所属模块**:discovery;必需 `core`、`discovery`;可选 `directions`(未启用则产出只回对话文本,
> 无 dossier 落点,建议先启用再查)、`maintenance`(未启用则写入文件不走 update-workflow,
> 改为逐文件经用户确认)。
> **执行方式**:主流程执行检索与判定;阶段三交叉验证委托 `reviewer` 服务。
> **开场三步**:① 读项目 `.claude/research-bench.config.md` 顶部 frontmatter manifest,确认 `modules`;
> ② 无 config → 停止,提示先运行 `rf:init` 初始化(Claude Code 中为 `/rf:init`);
> ③ `modules` 不含 `discovery` → 停止,提示先用 init 启用该模块。
> 确认后读 §12.1(Zotero 端点与集合约定)、§12.2(reviewer 通道)、§12.4(检索源/近月窗口/分级门槛);
> 启用 directions 时再读 §10(方向文件目录,dossier 落点)。

## 使用时机
- `propose-hypothesis` 选中一张卡片后、`refine-direction` 收敛前(三关链路的关卡 1)
- 用户直给一个种子想法,想在投入前确认没撞车
- 已有方向档案缺 novelty.md(如 discovery 模块后启用),补查存档

## 流程
1. **确定送审对象**:一个候选方向(选中的假设卡片 / 种子想法 / 已有 dossier 的 direction.md)。
   多个候选 → 逐个执行,不合并查新。
2. **阶段一、二(主流程执行)**:按 novelty-protocol.md §1 提取 3–5 个核心主张 → 多源检索
   (每主张 ≥3 种查询表述,强制查近 6 个月 arXiv,窗口与检索源按 config §12.4)。
   检出条目按协议 §2 验证:经 Zotero MCP 按 DOI/arXiv id 导入 config §12.1 约定的
   `directions/<slug>` 集合,记下 Zotero key。
   未配置 Zotero → 说明一句「未配置 Zotero MCP,降级为 arXiv/CrossRef/Semantic Scholar 三层核验」,
   验不过的引用标 `[UNVERIFIED]`;禁止凭记忆编 DOI。
3. **阶段三(主流程取外部裁决 + 委托 reviewer 服务)**:
   - 若 config §12.2 已配置 Codex 通道,主流程先按固定问题清单取得外部裁决:
     新颖吗 / 最接近的工作是什么 / 差异何在 / 评分 X/10。
   - 未配置 Codex → 记录降级原因,进入 reviewer 单签审查。
   按兼容协议加载 `../../agents/reviewer.md`,并传入
   `<主张清单 + 阶段二检出的最接近工作(含 Zotero key/核验 id) + Codex 裁决文本(若有)
   + 任务:新颖性交叉验证>`。
   reviewer 只做独立检索与裁决合并;有 Codex 裁决时**双签**返回,无 Codex 裁决时返回单签审查。
4. **阶段四(主流程判定)**:按协议 §1/§3 输出——每主张高/中/低分级、最接近前期工作对照表
   (每行带 Zotero key 或降级核验标记)、0–10 总分与建议(继续 / 谨慎 / 放弃,门槛按 config §12.4)。
5. **产出落档**(启用 directions 时):novelty.md 内容(主张分级表 / 对照表 / 双签裁决原文,
   骨架见方向模板 `_TEMPLATE/novelty.md`)+ 一行 gates.jsonl 记录
   `{"gate":"novelty","verdict":…,"score":…,…}`(schema 见 `_TEMPLATE/direction.md` 末尾注释)。
   **写入走 update-workflow**(启用 maintenance 时),否则把待写内容完整展示、经用户确认后写入;
   未启用 directions → 只输出文本并说明「未启用 directions 模块,跳过 dossier 落档」。
6. **转述与转接**:向用户转述总分、建议与最大威胁项;判「放弃」时建议把
   「已被某论文做过」条目(附 Zotero key)回写教训库(经 update-workflow);
   判「继续/谨慎」→ 转关卡 2(pilot,当前批次人工判)与关卡 3(reviewer 价值审查),再进 `refine-direction`。

## 约束
- **门槛与窗口以 config §12.4 为准**:修改属于削弱检查标准,须显式说明并经用户确认,本 skill 不代改。
- **引用可验证性遵 novelty-protocol.md §2**:对照表每行必带 Zotero key(或降级核验标记);
  验不过标 `[UNVERIFIED]`,不得作为判定依据;禁止凭记忆编 DOI / arXiv id。
- **只产出文本与经确认的档案写入**:novelty.md / gates.jsonl 走 update-workflow 或经用户确认;
  不写注册表(登记走三关后的 update-workflow + 用户确认),不改源码。
- **能「否」不能「准」**:查新通过只是进入下一关的条件;方向登记仍需后续关卡与用户确认。
- 跳过本关(用户显式要求)必须在 gates.jsonl 留 `"verdict":"skip"` 记录(含理由),不允许静默跳。
