<!-- 骨架文件 | 模块:directions(discovery 关卡产出的落点) | init 实例化到 config §10 指定的方向文件目录
     dossier 目录形态:docs/directions/<slug>/{direction.md, novelty.md, review.md, pilot.md, gates.jsonl}
     调用方:propose-hypothesis(strategist)/ refine-direction 产出的「方向落地块」按本文件字段生成,
     update-workflow 据此写入文件;audit-results(auditor)按「子任务表/结果表/claims/状态」核查漂移;
     check-novelty / reviewer 的关卡产出分别落 novelty.md / review.md,裁决行追加进 gates.jsonl。
     接口契约:字段名(slug/目标/拥有 flag/baseline_group/access_level/核心诊断/claims/子任务/结果/状态)
     与各 skill/agent 引用一致,不可改名;取值与说明按项目改。 -->
---
status: seed   # 状态机:seed → surveyed → novelty-checked → piloted → reviewed → active → closed
               # (closed 细分:published | falsified | superseded);与注册表行保持一致。
               # 跳过某关(如 pilot)允许越级推进,但必须在 gates.jsonl 留 "verdict":"skip" 记录(含理由)。
---

# 方向:<slug>

- **slug**:`<kebab,贯穿 config 名 / tracking direction tag / commit [<slug>] 前缀 / 目录名>`
- **目标**:<一句话>
- **拥有 flag**:`<slug>_<param>`(默认 off,`flags:{}` 复现基线)
- **baseline_group**:`<config §10 的取值之一>`
- **access_level**:`<config §10 的取值之一>`
- **状态**:见顶部 frontmatter `status`(与注册表行保持一致)

## 核心诊断
- **现状瓶颈**:<引架构地图文档行号/模块>
- **改动假设**:<作用模块 + 为什么能够改善瓶颈>
- **可证伪预测**:<config §3 指标的预期方向与量级;以及失败模式>

## claims(论文接口:一行一条可发表主张)
| claim | 支撑实验(config 名) | 状态(planned/running/done) | 证据指针(汇总表行 / tracking run) |
|---|---|---|---|
| <一句话定量主张> | `config_<slug>_<v>.yaml` | planned | |

## 文献(Zotero;仅当启用 discovery,否则删除本节)
- **Zotero 集合指针**:`<例:directions/<slug>(config §12.1 集合约定)>`
- **关键引用 key 清单**:
  | Zotero key | 引用(作者, 年份) | 角色(最接近工作 / 方法来源 / 对比基线) |
  |---|---|---|
  | | | |

## 子任务
| # | 任务 | config / flag | 类型(eval/训练/改源码) | 依赖 | 完成 |
|---|---|---|---|---|---|
| 1 | <任务> | `config_<slug>_<v>.yaml` / `<flag>` | <类型> | <依赖> | ☐ |

## 结果
| 实验(run 名) | config | seed | 主指标 | 次指标 | OOD | 结论 |
|---|---|---|---|---|---|---|
| | | | | | | |

## 结论 / 论文落点
<方向关闭或并入时填写:核心结论、进入论文哪一节;若证伪,提炼硬约束并回写教训库
(撞车关闭的,条目类型「已被某论文做过」,附 Zotero key)>

<!-- gates.jsonl schema(同目录 gates.jsonl,追加式关卡账本,一行一条裁决;不建实体模板文件):
     每行:{"gate":"novelty|pilot|review","verdict":"pass|fail|skip","score":<数值或 null>,
           "ts":"<ISO8601>","evidence_ptr":"<相对路径或 run id>","reason":"<跳过/失败理由>"}
     约定:verdict=skip 时 reason 必填(auto/loop 档跳关不允许静默,见 config §12.4);
     score:novelty / review 填 0–10 总分,pilot 可为 null;
     evidence_ptr 指向 novelty.md / review.md / pilot.md 或 tracking run id;
     写入经 update-workflow 或用户确认;test-workflow 的 ops 层断言本文件行行是合法 JSON。 -->
