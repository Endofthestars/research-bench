<!-- 模块:data | 吸收段:§8 数据集/权重管理
     依赖它的 skill/agent:run-experiment 的 pull-data 步骤(经 operator)、deploy-env 的预下载权重步骤。 -->

## 8. 数据集 / 权重管理(run-experiment / deploy-env / operator 用)
- 管理方式:`<例:DVC + RustFS S3;输入侧另管,与实验跟踪管产出对称>`
- 数据集仓:`<例:my_datasets(无 git origin,靠 provision 脚本拷元数据)>`
- 容器内挂载点:`<例:/datasets>`
- 权重本地路径 env:`<例:MODEL_WEIGHTS_PATH=/datasets/models/pretrained(不联网取权重)>`
- 存储端点:内网 `<例:http://10.0.0.10:9000>` / 公网 `<例:https://s3.example.internal>`
- 凭据来源:`<例:AWS_ACCESS_KEY_ID/SECRET 从数据集仓 .dvc/config.local 复制进 .env,不提交 git>`
  (凭据 env 名同时登记进 §7.2 敏感 env 名清单,operator 回执按它脱敏)
- 同步脚本:`<例:scripts/provision-datasets.sh(拷元数据到远程)、scripts/sync-datasets.sh(容器内 dvc pull)>`
