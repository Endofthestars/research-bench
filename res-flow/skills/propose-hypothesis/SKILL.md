---
name: propose-hypothesis
description: 综合实验结果与文献，提出新的研究方向或架构改动假设，并输出结构化"假设卡片"。适用于探索下一阶段实验方向、解释局部最优或结合文献规划后续实验。
---

# 提出研究假设（委托 strategist）

将发散探索委托给 **strategist 服务**（只读、隔离上下文），并转述其假设卡片。
方法论(输入收集 / 教训库先行比对 / 假设卡片格式 / 输出规范 / 方向落地块)全在 strategist 定义里,
本 skill 不重复。

> **所属模块**:core;必需 `core`;可选 `tracking`(未启用则定量证据以用户粘贴为准)、
> `directions`(未启用则跳过教训库比对、重复检查与「方向落地块」,只产假设卡片)。
> **执行方式**:委托 `strategist` 服务。
> **开场三步**:① 读项目 `.claude/research-bench.config.md` 顶部 frontmatter manifest,确认 `modules`;
> ② 无 config → 停止,提示先运行 `/rf:init` 初始化;
> ③ 可选模块缺哪个就按上述降级,说明跳过了什么。

## 开场提示
**如果已有新的 auditor 报告（audit-results 产出），请一并提供**。「现状总览 + 缺口清单」是
strategist 的可选输入，可以让假设更直接地对应真实缺口；没有报告时也可执行，strategist 会按证据协议自行读取汇总表。
报告过期或缺失时 strategist 会建议先执行 `/rf:audit-results`,如实转达。

## 流程
1. **委托 strategist 服务**:
   ```
   Agent(subagent_type="strategist", description="propose-hypothesis 假设卡片生成",
         prompt="<用户的探索意图/研究困境 + auditor 报告(若有)+ 用户提供的论文/摘要(若有)>")
   ```
   strategist 自行按 `references/evidence-protocol.md` 读证据基座(架构地图、注册表、教训库、汇总表)。
2. **转述产出**:3–5 张假设卡片(按优先级)+ 执行路线建议表;高优卡片的「方向落地块」原文保留。
   主对话只接收摘要,不重复拉文件内容。
3. 用户选中一张卡片要收敛细化 → 转 `refine-direction`(主流程多轮);
   要写入文件方向文件 + 登记注册表 → 走 `update-workflow`。
   **启用 `discovery` 时,选中的卡片先过三关再收敛**:`check-novelty`(关卡 1)→ pilot
   (关卡 2,当前批次由人工判定,跳过须留 gates.jsonl 记录)→ `reviewer` 审查(关卡 3,
   分数线见 config §12.4)→ `refine-direction` 收敛(吸收 novelty.md / review.md 产出)→
   `update-workflow` 落方向档案 + 登记注册表;未启用则维持上一行的原链路。

## 与 run-experiment 对接
"建议验证方案"的 `flags:` 块可**直接复制**进新 config YAML;新 config 顶层**必填 `direction: <slug>`** 等方向轴字段(启用 directions 时)。
链路:`propose-hypothesis → 用户确认 → [三关:check-novelty → pilot(人工判)→ reviewer(启用 discovery 时)] → [update-workflow 落方向文件 + 注册表] → [modify-architecture(若需改源码)] → run-experiment`。

## 约束(与 strategist 一致,主流程也须尊重)
- **只读、只建议**:不改任何源码、配置或 docs 文档;执行与否由用户判断。
- strategist 提假设前必比对教训库、不得重新审计完整性;主流程不得替它越界。
- 引用可查、不创造指标(config §3 已有指标为限)。
