# Claude Code / Codex 宿主兼容协议

所有 skill 开始执行前先应用本协议。它只适配宿主能力，不改变各 skill 的业务边界、模块门控和确认要求。

## 1. 名称与插件根

- 文档中的 `rf:<skill>` / `ef:<skill>` 是平台中性名称。Claude Code 中以 `/rf:<skill>` /
  `/ef:<skill>` 调用；Codex 中在提示里明确点名 `rf:<skill>` / `ef:<skill>`。
- 遇到历史文本中的 `/rf:<skill>` / `/ef:<skill>` 时，Codex 去掉前导 `/` 后按同名 skill 处理。
- `<PLUGIN_ROOT>` 是当前 skill 所在插件根，即当前 `SKILL.md` 的上两级目录。Claude Code 可使用
  `${CLAUDE_PLUGIN_ROOT}`；Codex 必须从已加载 skill 的实际路径解析。不得假设当前工作目录就是插件根。
- 项目配置仍统一存放在 `.claude/research-bench.config.md`。这是已有项目的共享兼容路径，Codex 也读写
  同一文件，不另建一份配置。

## 2. 交互

- 需要选择、确认或补充信息时，使用当前宿主提供的结构化提问能力：Claude Code 使用
  `AskUserQuestion`；Codex 使用可用的用户输入工具。若当前宿主没有结构化提问工具，就在对话中提出
  一个简短、阻塞式问题，不得替用户作高影响选择。
- 多选或一轮多问在宿主不支持时可拆成连续单问，但候选项、推荐依据和逐项确认语义必须保留。

## 3. 服务委托

- “委托 `<service>` 服务”时，先读取 `<PLUGIN_ROOT>/agents/<service>.md` 的完整定义。
- 宿主支持插件子代理时，创建对应服务并传入任务上下文；Claude Code 的 `Agent(subagent_type=...)`
  只是该路径的一种实现。
- Codex 或其他无对应子代理能力的宿主，由主流程在当前上下文中严格按服务定义执行，并保持其工具白名单、
  只读/可写边界和输出契约。不得因为没有子代理就跳过审计、保护或后置条件。
- 服务定义中的 `${CLAUDE_PLUGIN_ROOT}` 在 Codex 中一律解释为已经解析的 `<PLUGIN_ROOT>`。

## 4. 保护机制

- Claude Code 加载 `hooks/`，由 `guard-protected-write` 和 `guard-train-channel` 提供工具前拦截。
- Codex 插件当前不加载这些 Claude hooks。Codex 执行每次写入或 shell 命令前，必须把同一规则作为
  主流程预检：写 `source-dir`、`.claude/settings.json` 或 `.claude/hooks/` 前要求用户确认；匹配训练特征的
  命令必须走配置 §7.1 的受控启动通道和 §7.2 的 operator/ISA 映射，否则拒绝执行。
- Codex 的预检是模型级约束，不等价于系统级 hook。任何 skill 都不得宣称 Codex 已获得 hook 的强制保证。
- `.claude/settings.json` 中的 `RW_TRAIN_PATTERNS` / `RW_EXEC_PATTERN` 仅供 Claude hook 使用；Codex 从项目
  config §7.1 读取同一规则。Codex 下除非用户明确要求维护 Claude 兼容设置，否则不要新建或修改
  `.claude/settings.json`。
