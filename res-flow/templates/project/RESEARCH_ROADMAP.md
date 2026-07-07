<!-- 骨架文件 | 模块:directions | init 实例化到 config §10「活跃方向注册表/教训库」指定的路径
     调用方:propose-hypothesis(strategist)/ refine-direction 登记「注册表行」;audit-results(auditor)
     以本表为 plan-of-record 核查;run-experiment 选方向步骤从本表取 slug;
     propose-hypothesis(strategist)发散时另以「种子池」为输入之一。
     接口契约:三个节标题(「活跃方向注册表」「已关闭方向的硬约束」「种子池」)与各表列结构是
     skill/agent 引用锚点,不可改名;行内容随项目填。 -->

# 研究路线图

## 活跃方向注册表

> 单一事实来源:所有在研方向登记于此,一行一个 slug。状态与方向文件保持一致;
> 新方向由 propose-hypothesis / refine-direction 产出「方向落地块」后经 update-workflow 登记。

| slug | 目标 | 拥有 flag | baseline_group | access_level | 状态 | 方向文件 |
|---|---|---|---|---|---|---|
| `<slug>` | <一句话目标> | `<slug>_<param>` | <取值> | <取值> | `proposed` | `<方向文件目录>/<slug>.md` |

## 已关闭方向的硬约束(教训库)

> 已证伪/关闭方向沉淀的硬约束。**新假设的前提**:propose-hypothesis(strategist)/ refine-direction
> 提新方向前必须比对本节,要么避开约束、要么显式论证为何能突破。

| 约束 | 来源方向(slug) | 证据(run / 结果) | 含义(新方向不得……) |
|---|---|---|---|
| <例:纯加大 decoder 容量不提升 OOD> | `<slug>` | <run 名 / 指标对比> | <不得再次提出单纯扩容类方向> |

## 种子池

> 淘汰/谨慎裁决中抢救出的相邻空白点(衍生种子):check-novelty / reviewer 在 novelty.md / review.md
> 的「衍生种子」小节记 1–2 行,经 update-workflow 登记于此。本表是 propose-hypothesis(strategist)
> 发散的输入之一;种子被采纳后照常走三关,不得跳关。

| 种子(一句话) | 来源方向(slug) | 触发依据(撞车论文 Zotero key / 薄弱论点 #) | 状态(seed/adopted/dropped) |
|---|---|---|---|
| <例:撞车论文未覆盖的 OOD 评估设置> | `<slug>` | <key:引用 或 review.md 薄弱论点 #N> | seed |
