<!-- 模块:maintenance | 吸收段:§11 工作流自维护
     依赖它的 skill/agent:audit-workflow、update-workflow(steward)、test-workflow。
     启用本模块时,init 会实例化 workflow-checklist.md 与 scripts/test-workflow.sh 骨架。 -->

## 11. 工作流自维护(audit/update/test-workflow / steward 用)
- 一致性检查清单(唯一标准):`<例:docs/workflow-checklist.md,检查项 C1…Cn(init 从 plugin 的
  templates/project/workflow-checklist.md 实例化)>`
- 确定性测试脚本:`<例:scripts/test-workflow.sh。子命令契约固定:guards | sanity | connectivity | ops | all,
  不可改名(test-workflow skill 按此调用);实现随项目换>`
- 脚手架范围:`<例:.claude/ 配置、scripts/、docker/、experiments/、README.md、SETUP.md、docs/>`
- 结构树结构索引:`<例:README.md 的目录结构段>`
