---
name: audit-results
description: 根据实验计划核查当前结果完整性，标出缺失或不可信实验，并输出结构化"待办实验清单"。适用于确认消融完整性、结果可信度和论文支撑性。
---

# 审计实验结果（委托 auditor）

> **宿主兼容（必读）**：开始前读取 `../../references/host-compatibility.md`；委托 `auditor` 时
> 按该协议选择子代理或主流程回退。

将核查任务委托给 **auditor 服务**（只读、无状态、隔离上下文），并转述其报告。
核查方法论(完整性 / 方向漂移 / 可信度 / 论文必要性四维、待办卡片格式)全在 auditor 定义里,
本 skill 不重复。

> **所属模块**:tracking;必需 `tracking`;可选 `directions`(未启用则 auditor 跳过方向漂移维度,
> 计划来源改为用户提供的消融清单/论文草稿表格)。**执行方式**:委托 `auditor` 服务。
> **开场三步**:① 读项目 `.claude/research-bench.config.md` 顶部 frontmatter manifest,确认 `modules`;
> ② 无 config → 停止,提示先运行 `rf:init` 初始化(Claude Code 中为 `/rf:init`);
> ③ `modules` 不含 `tracking` → 停止,提示先用 init 启用该模块(没有跟踪记录就无从核查完整性);
> 缺 `directions` 则说明降级。

## 使用时机
- 完成一批实验后，需要确认还缺哪些支撑性实验
- 消融设计发生变化,需要重新核查哪些组合已执行过
- 准备撰写论文实验章节,需要完备性检查
- 盘点哪些结果不可信(seed 太少 / 未从 smoke 升全量 / OOD 未执行)

## 流程
1. **先保证数据新鲜**(可选但建议):若最近有 run 结束而汇总表未更新,主流程直接执行轻 op `collect`
   (config §7.2 映射,幂等)刷新结果汇总表,auditor 才有可靠数据源。
2. **委托 auditor 服务**:按兼容协议加载 `../../agents/auditor.md`,传入
   `<用户的问题/关注点 + 用户额外提供的实验计划或 run 详情(若有)>`。
   auditor 自行按 `references/evidence-protocol.md` 读证据基座,不需要主流程代读文件。
3. **转述报告**:现状总览 / 方向漂移 / 待办清单(按论文必要性降序)/ 可信度警告 / 执行路线建议。
   主对话只接收摘要，不重复返回文件内容。
4. auditor 标注的「值得探索，交由 strategist 评估」条目 → 提示用户可接 `rf:propose-hypothesis`
   (并把本次报告一并带给它)。

## 与 run-experiment 对接
每张待办卡片的"补做方案"可**直接复制**进新 config YAML。
链路:`audit-results → 用户确认优先级 → run-experiment`;若需先改源码则中间插 `modify-architecture`。

## 约束(与 auditor 一致,主流程也须尊重)
- **只读、只报告**:不改任何源码、配置或 docs 文档;方向文件/注册表的回写走 `update-workflow`。
- **不替用户决策**:哪些必须补、哪些可放弃由用户决定。
- auditor 不提出新方向；主流程转述时也不补充方向建议，探索归 strategist。
