# 提案:remote-control v2(对标同类项目的功能完善)

> 状态:**提案,实施中(/loop 推进)**。整合 2026-07-08 对同类项目的调研
> (claudecodeui/CloudCLI、Happy、claude-code-webui、247-claude-code-remote、claude-remote),
> 在不改变「受控远程触发」定位的前提下补齐功能差距。批次实施,每批经自测后落盘。

---

## 1. 现状与差距

现状(server 329 行 + web 面板):提交 prompt → SDK 后台执行 → 轮询运行列表 / 纯文本日志。
token 鉴权 + 项目白名单 + 速率限制 + 反代约束(SECURITY.md)。

对标同类项目,普遍具备而我们缺失的:

| 能力 | 同类做法 | 我们的现状 |
|---|---|---|
| 实时流式输出 | claude-code-webui/AI Hub:WebSocket/SSE 流式 | 手动刷新拉全量日志 |
| 会话续聊 | CloudCLI/Happy:resume 同一会话继续对话 | 一次触发一个孤立 run |
| 停止运行 | 普遍有 | 无,只能等它跑完 |
| 推送通知 | Happy:需输入/待审核/出错时推手机 | 无(PWA SW 基座已有,差 Web Push) |
| 权限确认中继 | Happy:权限请求推到手机确认 | runner 的 can_use_tool 固定策略 |
| 结构化 transcript | 聊天气泡/工具调用分块渲染 | 纯文本 |

## 2. 定位约束(不变)

- **受控触发面板,不是远程 IDE**:不做文件树编辑、git 操作、内嵌终端
  (claudecodeui 的 IDE 化路线扩大攻击面,与 SECURITY.md 的白名单哲学冲突)。
- **不做 E2E 加密中继**(Happy 架构):自托管 + TLS + token 已覆盖我们的威胁模型,
  引入中继服务器反而增加运维面。
- 安全边界(认证要求、后端不直接暴露、项目白名单)只增不减。

## 3. 批次

| 批次 | 内容 | 要点 |
|---|---|---|
| **P0 流式与控制** | SSE 流式日志(`GET /triggers/{id}/stream`);`POST /triggers/{id}/stop`;run 记录补耗时/结束时间/token 用量;前端改增量渲染 + 停止按钮 | 纯增量,不动现有端点;SSE 过反代需 Caddy 配置核对 |
| **P1 会话续聊** | run 记录 SDK session_id;`POST /triggers/{id}/continue`(follow-up prompt,SDK resume);前端 run 详情页变对话视图,transcript 按 assistant/tool 块渲染 | 续聊沿用原 run 的 project_key,不允许换项目 |
| **P2 通知与确认** | Web Push(VAPID,订阅存 store,SW 已有):完成/失败/需确认三类事件;权限确认中继:can_use_tool 挂起 → 面板/推送确认 → 放行或拒绝(超时默认拒绝) | 确认中继是安全增强(现在是固定策略);超时拒绝保守默认 |
| **P3 research-bench 集成** | 预设命令按钮(config 声明常用斜杠命令如 /rf:audit-workflow);探针状态页(读探针 JSON,DESIGN §3.2);看门狗 WAKE_CMD 对接文档(唤醒即触发 run 并推送) | 补上 DESIGN §3.2「通知渠道待定」的开放项 |

## 4. 实施纪律

- 每批走 service-dev agent,遵其安全约束(SECURITY.md 边界只增不减)与部署物联动
  (.env.example / README / Dockerfile / Caddyfile 同步)。
- 每批自测:uvicorn 起服务 + curl 验证新端点 + `python -m compileall` + `node --check`。
- 版本/CHANGELOG 不自行 bump,统一走 /release。

## 5. 参考

- claudecodeui(CloudCLI):https://github.com/siteboon/claudecodeui —— 多会话管理、工具默认全禁
- Happy:https://happy.engineering/ —— 推送时机(需输入/待审核/出错)、确认中继
- claude-code-webui:https://github.com/sugyan/claude-code-webui —— 流式聊天
- 247-claude-code-remote:https://github.com/QuivrHQ/247-claude-code-remote —— tmux 持久化、隧道方案
