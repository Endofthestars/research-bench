# 威胁模型与缓解措施

这个服务把"能触发 Claude Code 执行任意 prompt"的入口挂在公网域名下。这是一个真实的远程代码执行
风险面——token 泄露 = 攻击者可以在你的服务器上以你的名义跑任意 Agent 任务。以下是缓解措施和对应的
代码落点,方便审查是否名副其实(不是文档写了但代码没做到)。

| # | 风险 | 缓解措施 | 代码落点 |
|---|---|---|---|
| 1 | 无鉴权访问 | Bearer token,常量时间比较防时序攻击 | `server/auth.py` `verify_token` |
| 2 | 任意路径触发 | `project_key` 必须命中白名单,不接受原始路径 | `server/config.py` `_load_project_dirs`;`server/main.py` `create_trigger` |
| 3 | 权限升级 | `permission_mode` 硬编码在 `runner.py`,API 请求体(`TriggerRequest`)里**没有**这个字段,客户端无从传入 | `server/config.py` `FIXED_PERMISSION_MODE`;`server/runner.py` |
| 4 | 高危 Bash 命令(即使权限模式允许) | `can_use_tool` 回调按黑名单模式拦截(`rm -rf /`、`sudo`、`curl \| sh`、`git push --force` 等) | `server/runner.py` `_can_use_tool`;模式列表在 `server/config.py` `DANGEROUS_BASH_PATTERNS` |
| 5 | token 泄露后被刷爆资源 | 每分钟请求数限流(按来源 IP) | `server/auth.py` `_check_rate_limit` |
| 6 | 资源耗尽(并发/失控任务) | 并发上限(信号量)+ 单次运行超时 + `max_turns`/`max_budget_usd` 硬顶 | `server/main.py` `_semaphore`;`server/config.py` `MAX_CONCURRENT_RUNS`/`RUN_TIMEOUT_SECONDS`;`server/runner.py` |
| 7 | 事后无法追溯 | 每次触发追加写审计日志(时间、来源 IP、project_key、prompt 全文) | `server/main.py` `_audit` → `data/audit.log` |
| 8 | 进程权限过大 | 裸机:systemd 用专用低权限用户跑,`ProtectSystem=strict` 收紧文件系统访问面。容器:镜像内建了非 root 用户 `remotectl`(UID 10001),`USER` 指令切过去后才跑 uvicorn | `deploy/remote-control.service`;`Dockerfile` |
| 9 | 后端直接暴露公网 | 后端只监听 `127.0.0.1`,只有 Caddy 监听公网端口并做 TLS 终止 | `deploy/remote-control.service`(`--host 127.0.0.1`)、`deploy/Caddyfile.example` |

## 已知的残留风险(没有完全解决,使用前要知道)

- **黑名单式的 `can_use_tool` 拦截不是白名单,天然会有漏网之鱼**:能想到的高危命令特征都拦了,但
  黑名单永远拦不完所有变体(比如命令拼接、编码绕过)。如果你的使用场景允许,考虑把 `allowed_tools`
  收得更紧(比如干脆不给 Bash 权限,只给 Read/Grep/Edit),而不是依赖黑名单兜底。
- **单一共享 token,没有多用户/多权限概念**:适合个人使用,如果要给多人用,应该扩展成每个 token
  对应一个身份 + 各自的 project_key 白名单,而不是一个 token 通吃。
- **`max_budget_usd`/`max_turns` 是软上限**:能限制单次运行的开销,但不能完全杜绝被反复触发导致的
  账单增长(第 5 条的限流是主要防线,但限流窗口内仍可能跑掉小几次)。
- **audit.log 只是本地文件,没有做防篡改或异地留存**:如果攻击者拿到了服务器权限,可以直接改这个
  文件掩盖痕迹。生产环境建议转发到独立的日志系统。

## 部署前检查清单

- [ ] `REMOTE_CONTROL_TOKEN` 是用 `secrets.token_urlsafe(32)` 或等价强度生成的,不是手打的短密码
- [ ] `.env` 文件权限收紧(`chmod 600`),没有被提交进 git
- [ ] `REMOTE_CONTROL_PROJECT_DIRS` 只列了真的需要远程触发的目录,不是整个 `/home` 或 `/`
- [ ] systemd unit 里的 `ReadWritePaths`(裸机部署)或 `docker-compose.yml` 的 volumes(容器部署)
      覆盖了 `.env` 里配置的每一个项目目录
- [ ] Caddy 已经用真实域名跑通一次 HTTPS(不是明文 HTTP 对外)
- [ ] 防火墙只放行 80/443(Caddy),后端端口(默认 8000)没有对公网开放;容器部署下确认
      `docker-compose.yml` 里后端服务只有 `expose:` 没有 `ports:`
- [ ] `ANTHROPIC_API_KEY` 已经配置(容器/服务器上无法走 claude.ai 交互式 OAuth 登录)
- [ ] 容器部署:确认镜像不是以 root 跑的(`Dockerfile` 里已经切到 `remotectl` 用户,不要在
      `docker-compose.yml`/`docker run` 里用 `--user root` 覆盖掉)
