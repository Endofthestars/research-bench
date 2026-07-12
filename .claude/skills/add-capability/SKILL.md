---
name: add-capability
description: 为 rf 或 ef 插件新增一个 skill/command/agent 能力的脚手架流程。一次性生成三件套并同步所有关联物(README、shared/),杜绝"加了 skill 忘了 command"。用法:/add-capability <rf|ef|shared> <name> [说明]。
disable-model-invocation: true
---

# 新增插件能力(脚手架流程)

参数:`<target> <name> [一句话说明]`。`target` ∈ `rf`(`plugins/rf` 特有)/ `ef`(`plugins/ef` 特有)/
`shared`(两插件共有)。缺参数时询问。

## 步骤

1. **查重**:确认 `plugins/rf/`、`plugins/ef/`、`shared/` 下不存在同名 skill/command/agent;
   存在则停止并报告。
2. **确认设计**:向用户确认三点后再动手——
   - 该能力是否需要专属 agent(需要独立上下文干活/有独立工具边界才建,否则只建 skill);
   - 是否仅允许显式调用;若是,正文加入显式触发约束,并为 Codex 增加
     `skills/<name>/agents/openai.yaml` 的 `policy.allow_implicit_invocation: false`;
   - 所属模块与 config 依赖(参考现有 SKILL.md 开头的「所属模块 / 执行方式」惯例)。
3. **生成三件套**(target=shared 时写入 `shared/`,前缀用 `{{P}}`;否则写入对应插件目录):
   - `skills/<name>/SKILL.md`:frontmatter(name/description)+ 正文骨架,
     参照 `plugins/rf/skills/config/SKILL.md` 的结构惯例(开场先读 host compatibility 与 config manifest、模块要求、规则段);
   - `commands/<name>.md`:5 行薄壳,参照现有 `commands/init.md` 的格式;
   - (如需要)`agents/<name>.md`:参照现有 agent 的 frontmatter 惯例(name/description/tools)。
4. **同步关联物**:
   - target=shared → 运行 `scripts/sync-shared.sh`,确认 `--check` 通过;
   - 更新 README:「Skill 参考」章节加条目、「目录结构」章节加文件;
   - CHANGELOG 未发布段落加一行;
   - 提醒用户(不代做):wiki 的 Modules.md 需要加对应条目。
5. **验收输出**:列出创建/修改的全部文件路径,运行 Claude 本地加载检查与 Codex plugin validator,
   并给出两种宿主的本地安装自测命令。

## 规则

- 版本号不 bump(发版走 `/release`)。
- 生成的 SKILL.md 里 TODO 占位要显式标注 `<!-- TODO -->`,不要生成看似完整实则空洞的正文。
