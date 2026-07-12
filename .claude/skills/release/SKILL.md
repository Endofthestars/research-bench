---
name: release
description: rf/ef 插件发版流程。先跑一致性审计,再统一 bump 各处版本号、整理 CHANGELOG、提示 wiki 更新、可选打 git tag。用法:/release <version>(如 /release 0.1.2)。
disable-model-invocation: true
---

# 发版流程

参数:目标版本号 `<version>`(rf、ef 当前同步发版,共用一个版本号)。
无参数时按惯例建议:**小的增量改动 patch,新能力 minor**,给出建议值让用户确认。

## 步骤

1. **前置审计**:委托 `consistency-auditor` agent 全仓审计;有 ❌ 级问题 → 停止,
   报告问题清单,让用户决定先修还是强行继续。
2. **版本 bump**(全部统一为 `<version>`):
   - `.claude-plugin/marketplace.json`:rf、ef 两个 `version`
   - `plugins/rf/.claude-plugin/plugin.json`、`plugins/ef/.claude-plugin/plugin.json`
   - `plugins/rf/.codex-plugin/plugin.json`、`plugins/ef/.codex-plugin/plugin.json`
   - README 中出现的版本号(如有)
3. **CHANGELOG**:把「未发布」段落标题改为 `rf <version> / ef <version>(YYYY-MM-DD)`;
   若内容与实际改动不符(git log 对照),补齐后向用户展示确认。
4. **提醒项**(列出,不代做,除非用户要求):wiki 相关页更新;remote-control 若有改动,
   其 Docker 镜像发布由 CI 处理。
5. **收尾**(逐项经用户确认后执行):
   - `git add` 相关文件并提交,提交信息 `rf/ef <version>: <一句话摘要>`;
   - 可选 `git tag v<version>`;
   - push 仅在用户明确要求时执行。

## 规则

- 两个平台的 manifest 版本必须一次改齐,改完 grep 旧版本号确认活动清单无残留。
- 不引入本次发版范围之外的内容改动。
