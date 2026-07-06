<!-- 模块:core(必装)| 吸收段:§1 项目性质、§2 源码布局、§3 指标、§4 提交规范
     依赖它的 skill:analyze-architecture、modify-architecture、architect agent(以及所有 skill 的开场三步)
     装配:init 按选中模块把 templates/config/ 各分段拼成项目的 .claude/research-bench.config.md;
     本文件永远排最前。§ 编号是全局稳定锚点(§1–§12),模块未启用时对应编号整段缺席、不重排。 -->
---
# ↑ 装配后 config 顶部即此 frontmatter(机器可读层,manifest)。init 生成并维护;
#   凡需要被 hook 机械读取的值(modules、source-dir)必须放这里,其余项目值写正文各段。
config-version: 2              # manifest 格式版本;plugin 做不兼容变更时递增
plugin-version: 0.5.0          # 生成本 config 的 plugin 版本
modules: [core]                # 已启用模块列表,init 增删;取值:core / exec / data / tracking / directions / maintenance / discovery
source-dir: <模型源码根相对路径,例:mymodel/src/>   # guard-protected-write hook 用;与 §2 SOURCE_DIR 保持一致
exec-profile: <remote-docker|remote-venv|local-docker|local-venv>   # 执行档案(位置×运行时;仅启用 exec 模块时有意义,
                               # 未启用 exec 时 init 不写本行):init 两问定档写入;guard-train-channel hook
                               # 据它取默认通道模式(RW_EXEC_PATTERN 未设时);换档案走 init(牵连装配),不手改
---

# 研究工作流配置(项目专属事实来源)

> 这是 **research-bench(rf + lf 插件)** 的项目配置,由 `/rf:init` 或 `/lf:init` 按选中模块装配生成。
> plugin 里的 skill/agent 只写通用方法论,所有项目专属的**主机、路径、端点、文件名、指标名**都在这里填。
> 换项目只改这一份;增删模块用 init,不手工拼段。
>
> **约定路径**:项目根的 `.claude/research-bench.config.md`。每个 skill 开头先读顶部 manifest 查表,
> 读不到 config 就提示运行 init。
>
> 下面的示例值均为占位/示意,**示例值不可直接使用**——按你的项目替换。

---

## 1. 项目性质
- 一句话定位:`<例:fork 的某模型,改网络架构/loss 源码做可复现研究、发论文>`
- 硬约束:`<例:只支持微调、不支持从头训练 → 任何破坏预训练权重加载的改动都是高风险>`
- 两层 git:源码改动提交到 `<SOURCE_VCS,例:mymodel/ submodule>`(论文引这里的 commit hash);
  实验配置/文档/plugin 配置提交到 `<外层工作区>`

## 2. 模型源码布局(architect / analyze-architecture / modify-architecture 用)
- `SOURCE_DIR`:`<模型源码根,例:mymodel/src/>`(与顶部 frontmatter 的 `source-dir` 保持一致)
- 关键源文件与职责(按你的框架替换文件名):
  | 角色 | 文件 | 备注 |
  |---|---|---|
  | backbone(预训练核心·高危区) | `<例:backbone.py>` | 改它默认避免,先评估权重兼容性 |
  | 网络组装 / decoder / 输出头 / 权重加载 | `<例:model.py>` | |
  | 训练循环 / loss | `<例:train.py 的 train_loop>` | |
  | 目标/流场表示 | `<例:targets.py 的 labels_to_targets(流场/热图等中间表示)>` | 无则删 |
  | 评估指标 | `<例:metrics.py>` | |
- 预训练权重名:`<例:pretrained-v1 / pretrained-v2>`
- 创新优先区(保住预训练):`<例:decoder / 输出头 / loss / 流场>`
- 架构地图产出文档:`<例:docs/ARCHITECTURE.md>`(architect 维护)

## 3. 指标(禁止自行定义,只用框架已有)
- 主指标:`<例:AP@IoU(ap50 / ap90 / map)>`
- 次指标:`<例:f1_at50 / count_mae>`
- OOD / 泛化:`<例:ap50_ood>`
- 计算来源:`<例:src/metrics.py 的标准 AP@IoU>`

## 4. 提交规范
- `<例:commit 不加 Co-Authored-By 署名、不加 "Generated with" 脚注;一个架构改动一个 commit>`
