---
name: deploy-env
description: 将本地已构建的环境镜像传输到远程 daemon，并按需预下载权重。仅适用于 remote-docker 档案，并应在依赖变化重新 build 后由用户手动触发。
disable-model-invocation: true
---

# 部署环境镜像（传输 + 部署，不负责 build）

**职责边界：** 只负责把**已 build 好**的镜像传输到远程，并准备预训练权重。
本地构建由 `build-env` skill 负责。运行本 skill 前，必须先用 `build-env` 完成本地 build。
完整链路：**build-env（本地 build）→ deploy-env（传输到远程）**。

> **所属模块**:exec;必需 `exec` 且 **exec-profile = remote-docker**(位置 remote × 运行时 docker,
> "本地 build → 传输到远程"只在这一档存在）；可选 `data`（未启用则跳过下方「预训练权重」一节，
> 并说明"未启用 data 模块，跳过权重预下载，请确认远程已有权重"）。
> **执行方式**:传输段委托 `operator` 服务(push 是 operator 约束里注明的唯一 ISA 例外:
> 命令均取自配置 §5.2 的 deploy 脚本,不自行定义;回执契约与保护机制同样生效);权重预下载走 `pull-data` op。
> **开场三步**:① 读项目 `.claude/research-bench.config.md` 顶部 frontmatter manifest,
> 确认 `modules` 与 `exec-profile`;
> ② 无 config → 停止,提示先运行 `/ef:init` 初始化;
> ③ `modules` 不含 `exec` → 停止,提示先用 init 启用该模块;`exec-profile` 非 remote-docker →
> **明确降级**："当前档案 <exec-profile> 不涉及镜像远程传输（local 档案镜像本地可用，
> venv 档案无镜像概念），deploy-env 不适用；如需切换档案请使用 init"，不强制执行。
> 确认后读 §5.1(远程句柄、本地 build 句柄)、§5.2(镜像分层、deploy 脚本)、
> §8(若启用 data:DVC/存储端点、权重路径 env、同步脚本)。下文用 `<占位>` 指代这些值。

## 传输到远程(base | dev | run)
主流程与用户确认要传输哪些层后,委托 operator 用配置 §5.2 的 deploy 脚本 push-only 入口执行
(与 build 解耦,只传输不 build):
```bash
<deploy 脚本> push base   # 只 push 底座
<deploy 脚本> push dev     # 只 push 开发
<deploy 脚本> push run     # 只 push 运行
<deploy 脚本> push all     # 依次 push base→dev→run
```
等价底层命令(脚本内部就是这条管道;远程网络差可改为落地文件 + 分块传输):
```bash
<本地 build 句柄> save <base镜像> | gzip | <远程句柄> load
<本地 build 句柄> save <dev镜像>  | gzip | <远程句柄> load
<本地 build 句柄> save <run镜像>  | gzip | <远程句柄> load
```
operator 完成传输后验证远程镜像到位(作为后置条件写进回执):
```bash
<远程句柄> images | grep <镜像名前缀>
```
> **一步到位(build+push):** deploy 脚本的 `base|dev|run|all` 入口仍会**同时** build+push。
> 要 build 与传输分离,用 build-env(`build <layer>`)→ deploy-env(`push <layer>`)两段式。

## 预训练权重(关键:避开远程联网下载;见配置 §8)
- 权重由配置 §8 的数据集管理机制(如 DVC + S3)管理,经 operator 执行 `pull-data` op
  (config §7.2 映射)在容器内同步拉取
- 落到配置 §8 的权重本地路径
- 运行容器时设配置 §8 的权重路径 env,让框架不联网取权重

## 注意
- 有副作用且耗时，仅手动触发（已设 `disable-model-invocation: true`）
- 只在依赖变化时执行；日常修改源码不需要重新执行
- operator 回执(脱敏命令 / 退出码 / 环境事实)如实转述;发现新环境问题建议经 update-workflow 落 config
