---
description: 调用 plugin-dev 子代理开发 res-flow/exp-flow 插件模块(skill、agent、command、hook、template)。
---

使用 Agent 工具启动 `plugin-dev` 子代理(subagent_type: plugin-dev)完成以下任务,并向用户转述其结果:$ARGUMENTS

若 $ARGUMENTS 为空,先询问用户要 plugin-dev 处理什么任务,再启动子代理。
