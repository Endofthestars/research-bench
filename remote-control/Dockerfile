FROM python:3.12-slim

# claude-agent-sdk 底层通过 subprocess 调用 Node 版的 Claude Code CLI(@anthropic-ai/claude-code),
# 不是纯 Python 实现,所以镜像里必须装 Node/npm,而不只是 Python 依赖。
# git:被触发的 Claude Code 会话很可能需要在挂载的项目目录里跑 git 命令。
# ca-certificates:调用 Anthropic API 需要 HTTPS 信任链。
RUN apt-get update && apt-get install -y --no-install-recommends \
        nodejs npm git ca-certificates \
    && npm install -g @anthropic-ai/claude-code \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 10001 remotectl \
    && useradd --uid 10001 --gid remotectl --create-home --shell /usr/sbin/nologin remotectl

WORKDIR /app

COPY server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY server/ server/
COPY web/ web/

ENV REMOTE_CONTROL_DATA_DIR=/data
RUN mkdir -p /data && chown -R remotectl:remotectl /data /app

USER remotectl
VOLUME ["/data"]
EXPOSE 8000

# 只绑 0.0.0.0:8000 是安全的,前提是这个端口不直接发布到公网,只在 compose 的内部网络里
# 被 Caddy 访问——发布规则见 docker-compose.yml(backend 没有 ports:,只有 expose:)。
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
