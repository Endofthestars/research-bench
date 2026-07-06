---
name: settings
description: 交互式设置面板。以菜单形式浏览 research-bench 全部配置项(manifest、各配置段、保护机制 env),选中即可修改,写入规则与 config 一致。适合不记得键名、想逐项浏览调整配置的场景。
---

# 设置面板(交互式浏览与修改)

`.claude/research-bench.config.md` 的**交互式**管理入口,体验对标 Claude Code 内置 `/config`
设置面板:不需要记键名,用 `AskUserQuestion` 菜单逐层选择要看/要改的配置项。
与 `config` 的关系:**同一套数据与写入规则,不同交互形态**——`config` 面向"知道要改什么"
的定点命令式调用,本 skill 面向"浏览着改"的菜单式调用。

> **所属模块**:—(管理配置,同 config);**执行方式**:主流程执行(多轮交互)。
> **开场**:读项目 `.claude/research-bench.config.md` 顶部 frontmatter manifest;
> 无 config → 提示先运行 `/rf:init`(交互)或 `/rf:config init <键值对>`(非交互),终止。

## 面板结构(菜单循环)

每轮用 `AskUserQuestion` 呈现,选完执行,再回主菜单,直到用户选「退出」。

**第 1 层:主菜单**(按 manifest 只列已启用模块的段,未启用的不出现):

| 选项 | 内容 |
|---|---|
| 总览 | 等价 `config` 查看模式:manifest + 各段关键值 + 占位残留统计(只读) |
| manifest(modules / exec-profile) | 只展示当前值;要改 → 说明后**转介 `init`**(牵连装配,面板不代改) |
| §N <段名>(每个已启用段一项) | 进入第 2 层 |
| 保护机制 env | 进入 env 子面板(见下) |
| 退出 | 结束面板 |

**第 2 层:段内键列表**:列出该段可定点修改的键,每项附**当前值**(占位未填的标注
`<未填>`);选项超过 4 个时分页(`AskUserQuestion` 加「下一页」项)。选中一个键进入第 3 层。

**第 3 层:改值**:
1. 展示该键的说明(取自 config 内该行的注释/上下文)与当前值;
2. 有限取值的键(如布尔、枚举)用 `AskUserQuestion` 列选项;自由文本键让用户直接输入
   (提供本地扫描到的候选时列为选项 + 「其他(手动输入)」);
3. **展示 旧值 → 新值,确认后写入**——写入规则、机器可读字段同步(如 `source-dir` 双处一致)、
   职责边界与 `config` 的模式二**完全一致**,不另立标准。

**env 子面板**:列 `RW_EXEC_PATTERN` / `RW_TRAIN_PATTERNS` 当前值(读项目
`.claude/settings.json` 的 `"env"` 与 config §7.1);修改走 `config` 模式二特例的全部规则
(展示 JSON 片段确认、回填 §7.1、guard hook 二次确认属设计行为、放宽拦截面显式风险提示)。

## 直达参数(可选)

`settings <段号或关键词>`(如 `settings 5`、`settings tracking`)→ 跳过主菜单直接进对应
段的第 2 层;`settings env` → 直达 env 子面板。无法匹配 → 回主菜单。

## 边界与转介(与 config 同表)

| 想做什么 | 走哪 |
|---|---|
| 增删模块 / 换 exec-profile | `init`(面板内选中时说明并转介,不代改) |
| 改脚手架/脚本/skill/hook/checklist | `update-workflow`(steward 两段式) |
| 知道键名的定点改值 / 非交互初始化 | `config`(更快);本面板也能改,规则同源 |

## 规则

- 只写 `.claude/research-bench.config.md` 与(env 子面板,经确认)`.claude/settings.json`
  的 `"env"`;**其余内容均不修改**。
- 每次写入前展示旧值→新值并等待确认;浏览/总览绝对只读。
- 一次会话可连续改多个值,但**每个值单独确认单独写入**,不做批量静默写。
- 不删模块段、不动用户未选中的其他值。
