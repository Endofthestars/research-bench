---
name: config
description: 项目配置管理入口。支持查看 manifest 和占位统计、定点修改配置值、非交互初始化配置，以及经确认写入 .claude/settings.json 的保护机制 env。适用于快速查看或修改 research-bench.config.md。
---

# 配置管理(查看 / 定点改值 / 非交互初始化)

`.claude/research-bench.config.md` 的配置管理入口。原则：**config 是单一事实来源**。
如果只修改配置段内的单个值，可由本 skill 处理；凡是涉及模块装配、脚手架或跨文件同步的改动，均转交 `init` 或 `update-workflow`。

> **所属模块**:—(管理配置,同 init);**执行方式**:主流程执行。
> **开场**:读项目 `.claude/research-bench.config.md` 顶部 frontmatter manifest;
> 无 config 且非 `config init …` 调用 → 提示先运行 `/rf:init`(交互)或
> `config init <键值对>`(非交互)。

## 边界(先查表再动手)

| 想做什么 | 走哪 |
|---|---|
| 交互式初始化 / 增删模块 / 换执行档案(exec-profile) | `init`(牵连装配:拼删段、嵌 ops 预设、实例化骨架) |
| 查看配置 / 定点改一个配置值 / 非交互初始化 / 代写保护机制 env | **本 skill** |
| 改脚手架、脚本、skill、hook、checklist(有跨文件同步面) | `update-workflow`(steward 两段式) |

## 模式一:查看(无参数)

轻量只读,输出两块:
1. **manifest**:`modules` / `exec-profile`(若有)/ `source-dir` / `config-version` / `plugin-version`。
2. **各段状态**:对每个已启用的 §,列已填的关键值(执行句柄、工作目录、端点、脚本名等)+
   占位残留统计(`grep -n '<' <config>`,示例说明行除外)——哪一段还有几处 `<占位>`,便于查看。

## 模式二:set <键> <值>(定点改值)

1. 定位该键在 config 的哪一段哪一行,**展示 旧值 → 新值,等用户确认再写**;键不存在则说明,不猜。
2. **机器可读字段同步**:改 `source-dir` → frontmatter 与 §2 `SOURCE_DIR` 两处一起改(它们必须一致)。
3. **拒绝并转介**（职责边界）:
   - 改 `modules` 或 `exec-profile` → 拒绝,转 `init`——这两个键牵连装配
     (拼删 § 段、重嵌 §7.2 ops 预设、补删骨架),定点改值会留下配置与装配脱节的不完整状态;
   - 要改的是脚手架/脚本/skill/hook/checklist(不在 config 里,或改 config 值必须连带改脚本)→
     拒绝,转 `update-workflow`(steward 会执行"修改→自检→同步"一体流程)。
4. 改完提一句:若该值被 §7.2 映射的脚本引用,建议执行 `scripts/test-workflow.sh ops` 核对。

### 模式二特例:env 收编(set env.<名> <值>)

`config set env.RW_EXEC_PATTERN <模式>`(或 `env.RW_TRAIN_PATTERNS`)——经用户确认后**代写项目
`.claude/settings.json` 的 `"env"` 键**(只修改 `"env"` 下对应条目,其余原样保留):
- 写前展示将写入的 JSON 片段(旧值→新值)等确认;同时把同一模式回填 config §7.1 散文段,保持两处一致。
- **机制协同，不是故障**：guard-protected-write hook 会对"写 `.claude/settings.json`"这一操作
  **再次向用户请求确认**。这是保护机制不可自动削弱的设计行为，需如实告知用户。
- **放宽拦截的改动额外提示风险**:新模式明显比旧值/内置默认更宽(如通道模式改成 `.*`、
  训练特征清空)→ 在确认问句里显式标注"此改动会放宽保护机制拦截面,请确认这是有意的"。

## 模式三:非交互初始化(config init <键值对>)

`config init modules=core,exec exec-profile=local-venv source-dir=src/ …` —— **非交互装配**,
提供一条快速入口:跳过向导与预扫描,按给定键值直接生成 config + 骨架。
- 装配规则与 init 完全一致(同一套模板,不另起标准):按 `modules` 拼接
  `${CLAUDE_PLUGIN_ROOT}/templates/config/` 分段、剥装配注释;含 `exec` 时按 `exec-profile`
  裁剪 §5 小节、把 `templates/config/ops-presets/<exec-profile>.md` 的映射表嵌入 §7.2、
  local 档案实例化 `scripts/run.sh`;选了 maintenance 或 exec 实例化 `scripts/test-workflow.sh`
  (替换 `__PLUGIN_ROOT__`,加执行位);directions / maintenance 骨架同 init 的骨架表
  (directions 的方向模板为 `_TEMPLATE/` dossier 目录形态)。
- `modules` 取值(与 manifest 注释一致):core / exec / data / tracking / directions /
  maintenance / discovery(discovery 吸收 §12,依赖 core、强烈建议搭配 directions)。
- 键值对已提供则写入,未提供的值均保留 `<占位>`;`modules` 未给 → 只装 core;含 `exec` 但未给
  `exec-profile` → 停止要求补上(guard 的默认通道模式依赖它,不代选)。
- 已有 config 时拒绝(避免覆盖),提示走 init 的增删模块模式。
- **收尾校验照旧**(同 init 步骤 8):占位清单提醒;若含 exec 实际运行 `scripts/test-workflow.sh guards`。

## 规则
- 只写 `.claude/research-bench.config.md`、(模式三)骨架实例化目标、(env 收编,经确认)
  `.claude/settings.json` 的 `"env"`;**其余内容均不修改**。
- 每次写入前都展示旧值→新值（或将写入内容）并等待确认；不属于本 skill 的键当场转介。
- 不删模块段、不动用户已填的其他值;查看模式绝对只读。
