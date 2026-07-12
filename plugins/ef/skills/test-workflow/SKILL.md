---
name: test-workflow
description: 执行项目的确定性测试脚本，验证保护机制、本地健康检查、ops 映射 dry-run 和远程只读连通性，并解读脚本结果。适用于修改 hook、配置或脚本后的工作流回归检查。
allowed-tools: Bash, Read
---

# 测试工作流能力（执行断言 + 结果解读）

> **宿主兼容（必读）**：开始前读取 `../../references/host-compatibility.md`；Codex 下 `guards`
> 只验证 Claude hook 脚本断言，不得报告为 Codex 已挂载系统级 hook。

**职责边界：** 本 skill 只**调用**确定性测试脚本并**解读**结果，不自行判定对错；对错由配置 §11 的测试脚本（如 `scripts/test-workflow.sh`）断言决定。它与 audit-workflow 互补：**audit = 查配置一致性（读 + 推理，不执行）；test = 验证脚本实际行为（执行断言）**。

> **所属模块**:maintenance;必需 `maintenance`(测试脚本在 §11);可选 `exec`(未启用则
> §7 不存在、guard 处于静默放行,guards 层验证的就是"放行"这一行为;ops 层无映射表可查、跳过;
> connectivity 层无远程可探、跳过)。**执行方式**:主流程执行(调用脚本 + 解读)。
> **开场三步**:① 读项目 `.claude/research-bench.config.md` 顶部 frontmatter manifest,确认 `modules`;
> ② 无 config → 停止,提示先运行 `ef:init` 初始化(Claude Code 中为 `/ef:init`);
> ③ `modules` 不含 `maintenance` → 停止,提示先用 init 启用该模块(它会实例化测试脚本骨架)。
> 确认后读 §7(保护机制模式与 ops 映射,若启用 exec)、§11(测试脚本路径、检查清单)。

## 何时用
- 改了 guard hook、`settings.json`、`scripts/`、容器构建文件、`experiments/` 后,确认没破坏工作流
- 尤其改保护机制后:执行 `guards` 层回归,确认拦该拦、放该放
- 填/改了 §7.2 ops 映射后:执行 `ops` 层,确认每个 op 映射非占位、脚本存在可执行

## 执行方式
调用配置 §11 的测试脚本（约定 `scripts/test-workflow.sh`），子命令契约**固定**为
`guards | sanity | connectivity | ops | all`(init 实例化的骨架已锁定,实现随项目换、子命令名不可改):
- `scripts/test-workflow.sh guards` —— 保护机制断言(本地秒级,骨架可直接使用)
- `scripts/test-workflow.sh sanity` —— 本地健康检查(语法/构建文件/py/yaml)
- `scripts/test-workflow.sh ops` —— ops 映射 dry-run 断言(§7.2 每个已映射 op:映射非占位、
  引用的脚本存在且可执行;启用 discovery 时同时校验方向 dossier 的 `gates.jsonl` 逐行 JSON;
  **不实际执行训练**;本地秒级,骨架可直接使用)
- `scripts/test-workflow.sh all` —— 默认:**只执行本地层 guards+sanity+ops(+gates)**
- `scripts/test-workflow.sh connectivity` —— 远程只读探测(访问远程,**仅用户显式要求时才执行**)

**默认只执行本地快速层（guards+sanity+ops，启用 discovery 时包含 gates JSONL 校验）。** connectivity 会访问远程资源（remote 档案；local 档案通常探测本机 daemon/端点），需用户显式要求才执行；执行前确认运行环境已启动、`.env` 已 source（跟踪凭据）。

## 怎么解读
1. 读脚本输出的逐项 ✅/❌/⚠️SKIP 与末尾汇总。脚本退出码 0 = 全过。
2. 把**每个 ❌** 讲给用户:哪项、期望 vs 实际,并按严重度提建议:
   - 🔴 guards 层有 ❌ → **Claude 保护脚本回归**,最高优先级:直接启动训练未被拦截或受控通道被误拦,
     需立刻修 guard 脚本并重跑;Codex 的模型级预检规则还需按兼容协议单独审计
   - 🔴 ops 层有 ❌ → operator 会拒绝执行对应 op:去补 config §7.2 该行映射或修脚本(走 update-workflow)
   - 🟡 sanity 有 ❌ → 脚本语法/构建文件/yaml 坏了,会让后续步骤失败
   - ⚠️ SKIP 不是失败:多为本地缺重依赖、模块未启用、运行环境未起,或 op 映射标「不适用」
     (当前执行档案没有该动作,如 local 档案的 sync-code),据 SKIP 理由判断是否需补验
3. 不直接改任何文件——要修走 update-workflow(steward),且改完重新执行对应层确认。

## 约束
- connectivity **只读探测**:不得执行真实训练、不污染数据;跟踪系统仅只读查询,**不写任何实验**。
- ops 层只 dry-run:验证映射与脚本存在性,不得实际执行关键 op(关键 op 由 operator 在用户要求下执行)。
- 遵守 steward 通用约束:不修改模型源码(配置 §2)、不修改远程运维(只把跟踪/daemon 当外部依赖做健康检查)。
