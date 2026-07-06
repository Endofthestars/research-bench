---
name: modify-architecture
description: 安全修改模型网络架构或 loss 源码。适用于实现 decoder 修改、新模块、loss 修改或目标表示调整等架构研究改动。
---

# 修改架构（安全流程）

修改对象是配置 §2 `SOURCE_DIR` 下的模型源码。所有改动必须满足可控、可回滚、可对照和可复现。

> **所属模块**:core;必需 `core`;可选 `exec`(未启用则「改动后」第 2 步的 smoke test
> 无执行环境可执行时，提示用户自行验证前向/反向，其余要求不变）。**执行方式**:主流程执行
> (源码修改的判断与应用都留在主流程;若启用 exec,smoke 是关键 op,委托 `operator` 服务执行)。
> **开场三步**:① 读项目 `.claude/research-bench.config.md` 顶部 frontmatter manifest,确认 `modules`;
> ② 无 config → 停止,提示先运行 `/rf:init` 初始化;
> ③ 确认后读 §1–2(硬约束、`SOURCE_DIR`、关键源文件、预训练权重名、两层 git)与 §4(提交规范)取值。

## 改动前
1. 先用 analyze-architecture / architect 确认改动点与权重影响
2. 确认当前状态可执行:执行一次 smoke test 作为对照基线(启用 exec 时经 operator 执行 `smoke` op)

## 改动时
1. **模块化 + flag 开关**:把改动做成可开关(如 `--use_attention_decoder`、`--boundary_loss_weight 0.0`),
   默认关闭 = 等价原版。不得将改动写成不可关闭的默认行为；消融实验和回滚都依赖这一点
2. 改动尽量集中、边界清晰,便于审稿人理解和复现

## 改动后(每次必做)
1. **验证预训练权重加载**:确认官方预训练权重(配置 §2 的权重名)仍能正常加载;
   若某些层因结构改变不再加载，**明确列出哪些层以及原因**，不要静默忽略
2. smoke test 执行少量 step,确认前向/反向不报错(启用 exec 时经 operator 执行 `smoke` op,
   前置常需 `sync-code → install-editable`,见 run-experiment / config §7.2)
3. **提交到模型源码的 git 历史**(配置 §1 指定的那层,通常是 submodule,不是外层工作区):
   一个改动一个 commit,message 写清:改了什么、为什么、对预训练权重的影响、对应的 flag;
   格式遵配置 §4 提交规范

## 约束
- 改 backbone(配置 §2 标「高危」的文件)前必须显式评估权重兼容性,默认避免
- 训练验证不绕开受控启动通道(走 run-experiment;guard hook 会拦直接启动,见配置 §7)
- 不绕过 flag 直接改默认行为(会破坏 baseline 对照)
