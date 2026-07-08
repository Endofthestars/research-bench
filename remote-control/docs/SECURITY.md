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
| 10 | SSE 流认证时长期 token 进 URL(浏览器 `EventSource` 不能带 Authorization 头,若把 token 放 query 会进浏览器历史/反代 access log) | 不放 token:先用 Bearer token `POST /triggers/{id}/stream-ticket` 换一张**短时(60s)、单次使用、绑定该 run_id** 的随机 ticket,只有它出现在 query string 里;被记录/泄露的 ticket 要么已被消费要么已过期,换不回长期凭证。带头的客户端(curl)仍可直接用 Bearer 访问流端点 | `server/auth.py` `issue_stream_ticket`/`verify_stream_access`;`server/main.py` `create_stream_ticket`/`stream_trigger_log` |
| 11 | 停止接口被滥用/探测 | `POST /triggers/{id}/stop` 与其他端点一样要求 Bearer token + 限流;run_id 不存在返回 404、已结束返回 409,不泄露白名单外信息;每次 stop 也写审计日志 | `server/main.py` `stop_trigger` |
| 12 | 续聊接口绕过白名单/权限 | `POST /triggers/{id}/continue` 请求体**只收 prompt**:project_key/cwd 沿用原 run(客户端换不了项目),且原 run 的 project_key 若已被移出白名单则拒绝续聊;permission_mode/预算/超时/Bash 黑名单与首次触发完全一致;续聊同样走并发上限、限流与审计日志 | `server/main.py` `continue_trigger`;`server/runner.py` `execute_run`(resume 参数) |
| 13 | Web Push 面被滥用(灌垃圾订阅/泄露内容) | 订阅/退订端点要求 Bearer token + 限流;订阅数量有上限(默认 20);endpoint 必须 https;VAPID 未配置时整个 push 面关闭(端点返回 409/enabled=false);payload 只带事件类型 + run_id + 短标题,**不带 prompt/命令全文**(消息体本身经 aes128gcm 端到端加密,只有订阅浏览器能解);失效订阅(404/410)自动清理 | `server/push.py`;`server/main.py` `add_push_subscription`;`server/config.py` `MAX_PUSH_SUBSCRIPTIONS` |
| 14 | 确认中继被用作权限放宽通道 | 判定顺序硬编码:**黑名单命中 → 硬拒绝,永远不产生确认请求**(不存在人工放行黑名单命令的路径);中继只作用于灰区(默认:`rm -rf` 变体/`git push`/包管理器 install——不可逆删除、向远端发布、供应链引入三类);**超时默认拒绝**(默认 120s,`REMOTE_CONTROL_APPROVAL_TIMEOUT_SECONDS`);服务重启后遗留的 pending 无等待者,同样落空拒绝(fail closed);裁决端点要求 Bearer token + 审计,approval_id 为不可猜的 uuid4,已裁决/过期的请求不可再改(409) | `server/runner.py` `_build_can_use_tool`(判定顺序);`server/approvals.py`;`server/main.py` `decide_approval`;`server/config.py` `CONFIRM_BASH_PATTERNS` |
| 15 | 预设命令被当成自动执行入口 | `GET /config/presets` 要求 Bearer token;预设**只填充输入框、不自动提交**(前端点击后仍需人工点「触发」),服务端不因预设而放宽任何触发路径;预设内容来自服务器 env(`REMOTE_CONTROL_PRESETS`),客户端无法注入 | `server/config.py` `_load_presets`;`server/main.py` `list_presets`;`web/app.js` `loadPresets`(只 `promptInput.value=`,不提交) |
| 16 | 探针端点被用来读任意文件 | `GET /probes` 要求 Bearer token;**只读 env 白名单(`REMOTE_CONTROL_PROBE_FILES`)里显式登记的路径**,请求方无法指定任意路径(与第 2 条同一道防线);单文件有大小上限(默认 64KB)防内存滥用;文件缺席/非法 JSON/超大只在该项返回 `error`,不整体失败,也不泄露文件系统信息;**只读,绝不写探针文件** | `server/config.py` `_load_probe_files`/`PROBE_MAX_BYTES`;`server/main.py` `list_probes` |

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
