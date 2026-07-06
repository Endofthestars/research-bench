<!-- 模块:tracking | 吸收段:§9 实验跟踪
     依赖它的 skill/agent:run-experiment 的记录步骤、audit-results(auditor)、propose-hypothesis(strategist)。 -->

## 9. 实验跟踪(run-experiment / auditor / strategist 用)
- 工具:`<例:MLflow>`
- 写入/tracking 端点:`<例:内网 IP http://10.0.0.10:58383(走内网快通道,artifact 上传快)>`
- 人工查看地址:`<例:公网 https://mlflow.example.internal>`
- 凭据 env:`<例:MLFLOW_TRACKING_USERNAME / MLFLOW_TRACKING_PASSWORD,写 .env 不提交>`
  (凭据 env 名同时登记进 §7.2 敏感 env 名清单,operator 回执按它脱敏)
- 记录封装:`<例:CLI 不发指标 → experiments/train_wrapper.py 调 框架训练函数 + mlflow.log_metric>`
- **每次必记(复现必需项)**:源码 git hash(submodule)+ 数据集版本指针(DVC git hash + .dvc md5)+ 完整超参 + 数据划分 + 开启的 flag + seed
- 产出存 artifact:`<例:best + last + 关键 epoch checkpoint、评估可视化>`;输入不存(另管)
