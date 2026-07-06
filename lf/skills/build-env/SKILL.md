---
name: build-env
description: 在本地构建一个或多个环境镜像，仅负责 build，不负责远程传输。仅适用于 docker 运行时档案，并应在依赖、CUDA 或框架版本变化时由用户手动触发。
disable-model-invocation: true
---

# 构建环境镜像（只 build，不传输）

**职责边界：** 只在本地构建镜像（remote-docker 使用配置 §5.1 的本地 build 句柄；local-docker 使用本机
docker）。远程传输由 `deploy-env` skill 负责（仅 remote-docker 需要），形成 **build-env → deploy-env** 两阶段流程；local-docker 档案构建完成后即可在本机使用。

> **所属模块**:exec;必需 `exec` 且 **运行时 = docker**(exec-profile 为 remote-docker / local-docker);
> 可选 无。**执行方式**:执行段委托 `operator` 服务(build/push 是 operator 约束里注明的唯一 ISA 例外:
> 命令均取自配置 §5.2 的 build 脚本,不自行定义;回执契约与保护机制同样生效)。
> **开场三步**:① 读项目 `.claude/research-bench.config.md` 顶部 frontmatter manifest,
> 确认 `modules` 与 `exec-profile`;
> ② 无 config → 停止,提示先运行 `/lf:init` 初始化;
> ③ `modules` 不含 `exec` → 停止,提示先用 init 启用该模块;`exec-profile` 为 *-venv → **明确降级**:
> "当前档案 <exec-profile> 无镜像概念，build-env 不适用；环境管理见配置 §5.3(venv/conda)，
> 如需切换档案请使用 init"，不强制执行。
> 确认后读 §5.1(本地 build 句柄,仅 remote-docker)、§5.2(镜像分层与角色、build/deploy 脚本、
> 容器构建文件位置)。下文用 `<占位>` 指代这些值。

## 镜像分层(见配置 §5.2)
按配置 §5.2 的镜像表:底座镜像(CUDA/py/框架/依赖,**依赖/CUDA/框架版本变化时重建这层**)、
开发镜像(FROM 底座,开发 / smoke)、运行镜像(FROM 底座,正式训练)。

> 约定：镜像**只包含运行环境**，模型源码**不**写入镜像；运行时从同步后的源码执行 `pip install -e .`，
> 所以日常改源码不用重建镜像,只有**依赖**变了才需要重 build。

## build(base | dev | run | all)
**规则(remote-docker):build 只在配置 §5.1 的本地 build 句柄执行(通常本地网络更稳定),不得在远程 build。**
(local-docker 只有本地执行环境,无需区分。)

主流程与用户确认要 build 哪些层后,把序列委托 operator 执行(用配置 §5.2 的 build 脚本
build-only 入口,与 push 解耦):
```bash
<build 脚本> build base   # 只 build 底座
<build 脚本> build dev     # 只 build 开发(FROM base)
<build 脚本> build run     # 只 build 运行(FROM base)
<build 脚本> build all     # 按 base → dev → run 顺序依次 build
```
等价底层命令(脚本内部就是这几条,镜像名/Dockerfile 路径见配置 §5.2;local-docker 的
`<本地 build 句柄>` 就是本机 `docker`):
```bash
<本地 build 句柄> build -t <base镜像> -f <base Dockerfile> .
<本地 build 句柄> build -t <dev镜像>  -f <dev Dockerfile>  .
<本地 build 句柄> build -t <run镜像>  -f <run Dockerfile>  .
```
- `all`:按 **base → dev → run** 顺序(dev/run 都 FROM base,必须 base 先就位)
- 单层:只 build 改动涉及的那层
- operator 回执含逐条命令与退出码;失败层的现场信息原样转述用户,不擅自更换命令重试

## 下一步
build 完成后镜像只在**本地**:
- **remote-docker**:要让远程环境使用该镜像,**接着用 deploy-env skill** 把对应镜像传输到远程。
  即完整链路:**build-env(本地 build)→ deploy-env(搬到远程)**。
- **local-docker**:训练在本机容器中执行,镜像已就位,无需 deploy。

## 注意
- 有副作用且耗时，仅手动触发（已设 `disable-model-invocation: true`）
- 只在依赖变化时执行；日常修改源码不需要重新 build
- build-only 与 push-only 已拆分;如需一次完成 build+push,仍可使用脚本的 `base|dev|run|all` 入口
