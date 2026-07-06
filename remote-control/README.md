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
