# UPSTREAM(fork 溯源与同步手册)

`pub-flow/`(插件名 `pf`)是 **academic-research-skills(ARS)的完整 fork + 本土改造**。
本文件是 fork 边界的单一事实来源:上游是谁、拷了什么、我们改了什么、以后怎么跟。

## 上游信息

- **上游仓库**:https://github.com/Imbad0202/academic-research-skills
- **作者**:Cheng-I Wu(https://github.com/Imbad0202)
- **fork 基点 commit**:`becfcc40c6e9e93c187cf4a088333f83373e002d`(上游 v3.15.0)
- **拷贝日期**:2026-07-08
- **本插件 version 策略**:跟随上游版本号(当前 `3.15.0`),**不用**本仓库 rf/ef 的 0.x 序列;
  跟上游同步后随之更新。

## 拷贝时排除的内容

从上游根目录拷入 `pub-flow/` 时排除了(以后同步沿用同一排除集):

- `tests/`、`evals/`、`audits/`、`examples/`
- `.github/`(CI workflow;因此上游的 lint/gate 在本仓库**不会自动运行**,见「已知偏差」)
- 多语言 README(仅保留英文 `README.md` 与 `README.zh-CN.md`)
- `CONTRIBUTING.md`、`SECURITY.md`、`requirements-dev.txt`
- 上游的 `.claude-plugin/marketplace.json`(本仓库根有自己的 marketplace.json)

保留:`docs/`、`scripts/`、`tools/`、四个 skill 目录、`agents/`、`commands/`、`hooks/`、
`shared/`、`README.zh-CN.md`、`LICENSE`、`NOTICE.md`、`CITATION.cff`、`CHANGELOG.md`、
`MODE_REGISTRY.md`、`.claude/CLAUDE.md` 等运行时文件。

> **`skills/` 目录布局**:`pub-flow/skills/` 下 academic-paper、academic-paper-reviewer、
> academic-pipeline、deep-research 是指向上游根目录四个 skill 真身的**符号链接**,
> 与上游布局一致,skill 内部相对引用依赖它——**不要改成真目录或反向**。
> 我们新增的 `skills/dossier-bridge/` 是真目录,与四个符号链接并列。

## 本土改造文件清单

改造原则:**新增文件优先,尽量不改上游原文**(利于同步)。当前全部改动:

| 动作 | 文件 | 说明 |
|---|---|---|
| 修改 | `.claude-plugin/plugin.json` | `name` → `pf`;`description` 加 fork + 桥接说明。**author / homepage / repository / license / version 原样保留**(署名义务 + 版本跟随)。这是唯一被修改的上游文件 |
| 新增 | `UPSTREAM.md` | 本文件 |
| 新增 | `skills/dossier-bridge/SKILL.md` | 桥接 skill(中文原创):rf 方向 dossier → ARS 英文素材包 |
| 新增 | `commands/dossier-bridge.md` | 桥接 skill 的 5 行薄壳 |

`plugin.json` 未加自定义 `forkedFrom` 字段(Claude Code 对 plugin.json 未知字段的校验行为
无保证,不冒险)——fork 基点以本文件为准。

## 跟上游同步的操作步骤

1. `git clone https://github.com/Imbad0202/academic-research-skills /tmp/ars-upstream`
   并 checkout 目标 tag/commit;
2. `rsync -av --delete` 上游根目录 → `pub-flow/`,**带上文同一排除集**
   (`--exclude` tests/ evals/ audits/ examples/ .github/ CONTRIBUTING.md SECURITY.md
   requirements-dev.txt .claude-plugin/marketplace.json 以及英文/zh-CN 以外的多语言 README),
   并 **exclude 本土改造文件**(上表「新增」各项),防止被 `--delete` 清掉;
3. 检查 `.claude-plugin/plugin.json` 是否被上游覆盖——被覆盖则按上表重做 name/description
   两处修改,version 采上游新值;
4. 逐项核对本土改造文件与上游新版是否冲突:重点是 `commands/` 命令名有无增删改
   (dossier-bridge SKILL.md 第 4 步提示的入口 `/pf:ars-plan`、`/pf:ars-outline`、`/pf:ars-full`
   要与 `commands/` 与 `MODE_REGISTRY.md` 实际清单一致)、`skills/` 符号链接是否完好;
5. 更新本文件的 fork 基点 commit / 版本 / 日期;同步根 `.claude-plugin/marketplace.json`
   里 pf 的 version;
6. `python3 -c "import json;json.load(open('pub-flow/.claude-plugin/plugin.json'))"` 与
   `ls -la pub-flow/skills/` 自查。

## 已知偏差(相对上游)

- 上游 `.command-invariants.toml` + `tools/release-discipline` 的 lint 断言
  `commands/*.md` 与 SessionStart announce 清单(`scripts/announce-ars-loaded.sh`,16 条
  `ars-*` 命令)完全一致。我们新增的 `commands/dossier-bridge.md` 不在 announce 清单里
  (原则上不改上游 announce 脚本);该 lint 只在上游 CI 运行,`.github/` 已排除,
  故本仓库不受影响——但**若日后把该 lint 接进本仓库 CI,须给 dossier-bridge 加豁免**。
- 上游 marketplace.json 为兼容 symlink-blind 的 GitHub API 导入器声明了显式 `skills` 路径;
  本仓库根 marketplace.json 未声明(Claude Code 本地/ git 安装可正常解析符号链接)。
  若发现经 GitHub API 导入 pf 丢 skill,参照上游 v3.14 #480 的做法补 `skills` 数组。

## 许可证边界

- **本子树(`pub-flow/` 全部内容,含我们的新增文件)采用 CC-BY-NC 4.0**
  (见本目录 `LICENSE`、`NOTICE.md`):**禁止商业使用**,再分发须署名 **Cheng-I Wu**
  并附上游链接与修改说明。我们的本土改造文件随子树同样按 CC-BY-NC 4.0 提供,
  避免子树内许可证碎片化。
- 仓库其余部分(rf / ef / shared / remote-control 等)仍为 MIT,见仓库根 `LICENSE`
  与 README 许可证节的混合许可声明。
- pf **不参与** 本仓库 `shared/` 单一事实来源体系与 `scripts/sync-shared.sh`
  (它有自己的目录结构与上游同步流程)。
