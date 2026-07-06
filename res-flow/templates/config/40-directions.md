<!-- 模块:directions | 吸收段:§10 方向/路线注册表
     依赖它的 skill/agent:propose-hypothesis(strategist)、refine-direction、audit-results(auditor)、
     run-experiment 的选方向步骤。启用本模块时,init 会实例化 directions/_TEMPLATE/ dossier 目录模板
     与 RESEARCH_ROADMAP.md 骨架。 -->

## 10. 方向 / 路线注册表(strategist / refine-direction / auditor 用)
- 活跃方向注册表(单一事实来源):`<例:docs/RESEARCH_ROADMAP.md §活跃方向注册表>`
- 方向文件目录 + 模板:`<例:docs/directions/<slug>/——每方向一个 dossier 目录(direction.md 主档案 +
  novelty.md / review.md / pilot.md 关卡产出 + gates.jsonl 关卡账本);模板 docs/directions/_TEMPLATE/
  (init 从 plugin 的 templates/project/directions/_TEMPLATE/ 实例化,direction.md 字段即「方向落地块」,
  gates.jsonl schema 见其末尾注释)>`
- 教训库(已关闭方向的硬约束):`<例:docs/RESEARCH_ROADMAP.md §已关闭方向的硬约束>`
- 结果汇总表:`<例:docs/ablation_table.csv(experiments/collect_results.py 输出,即 §7.2 collect op)>`
- 消融设计记录:`<例:docs/ARCHITECTURE.md>`
- slug 约定:`<例:slug=kebab,贯穿 config 名 / tracking direction tag / commit 前缀 / 文件名;新 flag=<slug>_<param>,默认 off,flags:{} 复现基线>`
- 方向轴字段与取值:
  - `baseline_group`:`<例:standardized(lr1e-4/bs4,新方向默认)/ baseline-legacy(lr1e-5/bs1)>`
  - `access_level`:`<例:api-only / training-loop / fork-source>`
- 选方向脚本:`<例:experiments/select_direction.py(--list / --slug)、experiments/check_configs.py 公平性 lint>`
  - 启用 discovery 时:全量实验选方向,select_direction 应校验该方向 dossier 的 gates.jsonl
    (三关未过且无跳过记录则拒绝),契约见 §12——契约扩展本身属后续批次,当前先以此为约定。
