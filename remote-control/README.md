# remote-control

remote-control 是 research-bench 的可选远程触发服务,用于在自己的域名和云服务器上触发、查看和管理
Claude Code 会话。它不依赖 Anthropic 的 `--remote-control`(那个是 claude.ai 云端专用,不能自建,
详见 `docs/SECURITY.md` 之外的调研结论)。

Web 面板支持在 Edge/Chrome 里"安装为应用"(PWA manifest + service worker),装完像个独立 App 一样用。

**在暴露到公网之前,先看一遍 [`docs/SECURITY.md`](docs/SECURITY.md)**——这是一个"自由输入 prompt
远程执行 Agent 任务"的服务,安全配置不是可选项。

## 目录

```
remote-control/
├── server/               FastAPI 后端(Claude Agent SDK 驱动)
├── web/                  静态 Web 面板(含 PWA manifest/service worker/图标)
├── deploy/               systemd unit、Caddyfile(裸机/docker 两版)、.env 模板
├── docs/                 安全设计说明
├── Dockerfile            打包镜像(Python + Node,SDK 底层要调 Node 版 Claude Code CLI)
├── docker-compose.yml    backend + Caddy 两个容器
└── .dockerignore
```

镜像也会由 GitHub Actions 自动构建,见「用 GitHub Actions 自动构建镜像」一节。

## 本地跑起来(不涉及域名/服务器)

```bash
cd remote-control
python3 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt

export REMOTE_CONTROL_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
export REMOTE_CONTROL_PROJECT_DIRS="demo=$(pwd)/.."

uvicorn server.main:app --reload --port 8000
```

浏览器打开 `http://localhost:8000`,在页面顶部填入上面生成的 token 并保存,就能提交 prompt 了。

用 curl 验证鉴权和白名单:

```bash
# 缺 token → 401
curl -i -X POST localhost:8000/triggers -d '{"project_key":"demo","prompt":"hi"}'

# project_key 不在白名单 → 400
curl -i -X POST localhost:8000/triggers \
  -H "Authorization: Bearer $REMOTE_CONTROL_TOKEN" -H 'Content-Type: application/json' \
  -d '{"project_key":"not-registered","prompt":"hi"}'
```

流式日志与停止(P0 新增端点):

```bash
# 触发一个 run,记下返回的 run_id
curl -s -X POST localhost:8000/triggers \
  -H "Authorization: Bearer $REMOTE_CONTROL_TOKEN" -H 'Content-Type: application/json' \
  -d '{"project_key":"demo","prompt":"只回答一个词:pong"}'

# SSE 流式跟随日志(从头回放 + 实时新行,run 结束时收到 event: end 后连接关闭)
# curl 能带 Authorization 头,直接访问即可;浏览器 EventSource 走 stream-ticket 换票。
curl -N localhost:8000/triggers/<run_id>/stream \
  -H "Authorization: Bearer $REMOTE_CONTROL_TOKEN"

# (可选)换一张 60 秒一次性 ticket,模拟浏览器 EventSource 的认证方式
curl -s -X POST localhost:8000/triggers/<run_id>/stream-ticket \
  -H "Authorization: Bearer $REMOTE_CONTROL_TOKEN"
curl -N "localhost:8000/triggers/<run_id>/stream?ticket=<ticket>"

# 停止运行中的 run(取消任务并终止底层 CLI 子进程,状态变 stopped)
curl -i -X POST localhost:8000/triggers/<run_id>/stop \
  -H "Authorization: Bearer $REMOTE_CONTROL_TOKEN"

# 对已结束的 run 再 stop → 409
# 运行列表现在带 finished_at / duration_seconds / total_cost_usd / num_turns / usage /
# session_id / parent_run_id 字段;详情(GET /triggers/<run_id>)还带 children(对话链后继)
curl -s localhost:8000/triggers -H "Authorization: Bearer $REMOTE_CONTROL_TOKEN"
```

会话续聊(P1 新增端点):

```bash
# 在已结束 run 的会话上下文里继续对话(SDK resume;沿用原 run 的项目,不允许换)。
# 原 run 未结束或没有 session_id → 409。返回新的 run_id(记录 parent_run_id 指回原 run)。
curl -s -X POST localhost:8000/triggers/<run_id>/continue \
  -H "Authorization: Bearer $REMOTE_CONTROL_TOKEN" -H 'Content-Type: application/json' \
  -d '{"prompt":"接着上面的话题,再补充一点"}'
```

通知与权限确认(P2 新增):

```bash
# 推送配置(VAPID 没配则 enabled=false,面板"通知"按钮会提示未启用;配置方法见 deploy/.env.example)
curl -s localhost:8000/push/config -H "Authorization: Bearer $REMOTE_CONTROL_TOKEN"

# 灰区 Bash 命令(默认 rm -rf 变体 / git push / 包管理器 install)会挂起等确认:
# 详情页 SSE 里出现 approval_request 事件(带 approval_id),面板显示允许/拒绝按钮;
# 已订阅推送的浏览器同时收到"等待确认"通知。用 curl 裁决:
curl -s -X POST localhost:8000/approvals/<approval_id> \
  -H "Authorization: Bearer $REMOTE_CONTROL_TOKEN" -H 'Content-Type: application/json' \
  -d '{"decision":"allow"}'     # 或 {"decision":"deny"}

# 超时(默认 120s,可调 REMOTE_CONTROL_APPROVAL_TIMEOUT_SECONDS)没人裁决 → 默认拒绝;
# 已裁决/已过期再裁决 → 409。黑名单命令(sudo、rm -rf / 等)直接硬拒,不产生确认请求。
```

## 部署到云服务器

前提:域名的 DNS A/AAAA 记录已经指向服务器公网 IP。

1. 装 Caddy(自动 TLS,不用手动 certbot):参考你所用发行版的官方安装方式。
2. 把这个仓库(或至少 `remote-control/`)放到服务器上,比如 `/opt/research-bench/`。
3. `cp deploy/.env.example deploy/.env`,按 `docs/SECURITY.md` 的"部署前检查清单"填好并 `chmod 600`。
4. `python3 -m venv .venv && .venv/bin/pip install -r server/requirements.txt`。
5. 建一个专用低权限用户跑服务(见 `deploy/remote-control.service` 顶部注释),把该 unit 复制到
   `/etc/systemd/system/remote-control.service`,按实际路径改 `WorkingDirectory`/`ExecStart`/
   `ReadWritePaths`,然后:
   ```bash
   systemctl daemon-reload
   systemctl enable --now remote-control
   ```
6. `cp deploy/Caddyfile.example /etc/caddy/Caddyfile`,把域名换成真实值,`systemctl reload caddy`。
7. 浏览器访问 `https://你的域名`,走一遍触发 → 查看运行记录 → 查看日志的完整流程。
8. Edge/Chrome 地址栏或菜单里选"安装此站点为应用",确认能正常安装、图标和名称正确。

## 用 Docker 部署(替代上面裸机 systemd 的方式)

镜像里除了 Python 依赖,还装了 Node.js + `@anthropic-ai/claude-code`——Agent SDK 底层是 shell 出去调
这个 Node CLI 的,不是纯 Python 实现,漏装 Node 会导致触发全部失败。

```bash
cd remote-control
cp deploy/.env.example deploy/.env   # 填 ANTHROPIC_API_KEY / REMOTE_CONTROL_TOKEN / REMOTE_CONTROL_PROJECT_DIRS
cp deploy/Caddyfile.docker.example deploy/Caddyfile   # 换成真实域名
# docker-compose.yml 里把要挂载的项目目录取消注释,路径两边(宿主机:容器内)保持一致
docker compose up -d --build
```

- 后端容器**没有**发布端口到宿主机(`docker-compose.yml` 里只有 `expose:`),只有 Caddy 容器发布
  80/443——保持"后端只能通过反向代理访问"这条安全约束在容器化后依然成立。
- `ANTHROPIC_API_KEY` **必填**:容器里没有交互式登录的机会,只能用 API key 鉴权,和 claude.ai 的
  OAuth 登录是两回事。
- 容器以 `remotectl`(UID 10001)非 root 用户运行,`/data` 目录已经提前 `chown` 好。

单独 `docker build` / `docker run`(不用 compose)也可以,但要自己处理"后端不暴露公网""挂载
`/data`""挂载 `REMOTE_CONTROL_PROJECT_DIRS` 里的每个目录"这几件事,compose 已经把这些接好了。

## 用 GitHub Actions 自动构建镜像

`.github/workflows/remote-control-docker.yml`:`remote-control/**` 有改动 push 到 `main` 时自动构建
并推到 GHCR(`ghcr.io/<repo owner>/remote-control`),同时构建 `linux/amd64` 和 `linux/arm64`(不少便宜
的自建云服务器是 ARM 机型)。用 `GITHUB_TOKEN` 登录 GHCR,不需要额外配置 secrets。PR 只构建不推送。

- `latest` 标签:每次 `main` 分支构建都会更新
- 打 `remote-control-v1.2.3` 这样的 tag 会额外产出 `1.2.3` 标签,用于固定版本部署
- 部署时把 `docker-compose.yml` 里的 `build: .` 换成 `image: ghcr.io/<owner>/remote-control:latest`
  (或具体版本号),就不用在服务器上本地构建了

## 环境变量

见 `deploy/.env.example` 的注释;必填的是 `ANTHROPIC_API_KEY`、`REMOTE_CONTROL_TOKEN` 和
`REMOTE_CONTROL_PROJECT_DIRS`,其余都有默认值。

## research-bench 集成(预设命令 / 探针 / 看护链路对接)

配了 `REMOTE_CONTROL_PRESETS` / `REMOTE_CONTROL_PROBE_FILES` 后(见 `.env.example`),面板会多出
预设按钮和探针状态区。curl 验证:

```bash
T="$REMOTE_CONTROL_TOKEN"
# 预设命令列表(前端渲染成填充输入框的按钮)
curl -s localhost:8000/config/presets -H "Authorization: Bearer $T"
# 探针状态(只读 env 白名单里登记的 JSON;缺席/坏 JSON/超大只在该项返回 error)
curl -s localhost:8000/probes -H "Authorization: Bearer $T"
```

### 与看门狗 WAKE_CMD 对接

DESIGN §3.2 的看门狗在训练结束/异常时执行一条 `WAKE_CMD`。把它配成一次触发调用,就能实现
**训练结束 → 自动触发一轮分析 → 手机收 Web Push 通知**(需先在面板点「通知」订阅,并配好 VAPID):

```bash
# 看门狗脚本里的 WAKE_CMD 示例。token 从 600 权限的文件读,不要内联进命令行/进程表。
curl -sS -X POST https://你的域名/triggers \
  -H "Authorization: Bearer $(cat /etc/remote-control/token)" \
  -H 'Content-Type: application/json' \
  -d '{"project_key":"demo","prompt":"训练已结束,请从流水线状态文件恢复,分析最新结果并给出下一步建议"}'
```

配合探针页,你可以在手机上先看训练心跳(epoch/loss/是否卡死),收到"结束"推送后点进 run
详情看分析流式输出——不需要 SSH 上服务器。
