---
name: run-experiment
description: 按执行档案(exec-profile)执行训练实验，包含 baseline 对照、实验跟踪记录和复现信息。交互判断由主流程完成，关键 op 序列一次性委托 operator 执行。适用于启动训练、对比改动效果和执行消融实验。
---

# 执行实验（可复现、可对照；关键操作委托 operator）

> **宿主兼容（必读）**：开始前读取 `../../references/host-compatibility.md`；委托 `operator` 时
> 按该协议选择子代理或主流程回退，Codex 下每条 shell 命令先做 train-channel 预检。

> **所属模块**:exec;必需 `exec`;可选 `data`(pull-data 步骤)、`tracking`(记录步骤)、
> `directions`(选方向步骤)。**执行方式**:交互判断主流程执行;关键 op 序列委托 `operator` 服务;
> 轻 op(status / collect)主流程直接执行。
> **开场三步**:① 读项目 `.claude/research-bench.config.md` 顶部 frontmatter manifest,
> 确认 `modules` 与 `exec-profile`(执行档案:remote-docker / remote-venv / local-docker / local-venv);
> ② 无 config → 停止,提示先运行 `ef:init` 初始化(Claude Code 中为 `/ef:init`);
> ③ `modules` 不含 `exec` → 停止,提示先用 init 启用该模块;可选模块缺哪个就跳对应步骤,
> 跳过可选步骤时需说明原因，例如："未启用 X 模块，跳过 Y"。
> 确认后按启用模块读 §5(执行环境:§5.0 档案与工作目录,及本档案适用的小节)、§6(实验脚手架)、
> §7(保护机制 + ops 映射表 + 租约),以及 §8(数据,若启用 data)、§9(跟踪,若启用 tracking)、
> §10(方向,若启用 directions)。
> 下文用 `<占位>` 指代配置里的:执行句柄(remote 档案)、工作目录、镜像名(docker 运行时)、
> 权重路径 env、跟踪写入端点 `<tracking-uri>`、查看地址 `<tracking-view>`、脚本名。

## 轻重分级(config §7.2)
- **关键 op**(sync-code / install-editable / pull-data / smoke / launch):必须经 operator,
  本 skill 一次性传整段序列,不逐个拉起。
- **轻 op**(status / collect,只读或幂等):主流程直接执行 §7.2 映射的命令,照样受 guard 管。

## 流程

### 一、主流程:实验定义(交互判断,不修改执行环境)
1. **选择方向(slug,交互式)**(仅当启用 `directions`,见配置 §10;未启用则说明
   "未启用 directions 模块,跳过选方向,config 不带方向轴字段"):
   1. 列出可选方向(如 `select_direction.py --list`)
   2. **用宿主提问机制与用户确认所选 slug**(呈现 目标 / baseline_group / access_level / 状态)
   3. 取该 slug 字段块(如 `--slug <选中>`),把 `direction`/`baseline_group`/`access_level` 粘进新 config 顶层
      - slug 不在注册表 → 报错,先 propose-hypothesis / refine-direction + update-workflow 立项
   4. 公平性 lint(如 `check_configs.py`:同 baseline_group 内 data/eval/seed 一致)
2. **对照设置(与用户确认后再执行)**:通过 config 的 `flags:` 块一键切换
   - baseline:官方未改的模型(`flags: {}`,所有自定义 flag 关闭)
   - 你的改动:在 `flags:` 里打开对应开关
   - 两者用**同数据、同划分、同 seed、同指标**;实验 config 写好后向用户复述一遍对照设计再往下走

### 二、委托 operator:关键 op 序列(一次性)
按兼容协议加载 `../../agents/operator.md`,**把整段 op 序列 + 本次实验上下文一次传入**:
`执行 op 序列:sync-code → install-editable → (启用 data 时)pull-data → smoke → launch <exp>；
实验 config:experiments/<exp>.yaml；源码/外层 git hash:<hash>；按 config §7.2 映射执行、验证各 op
后置条件、遵 §7.3 租约互斥并回传回执。`
- 源码有改动才需要 install-editable;没改动可让 operator 跳过(在 prompt 里说明)。
- **local 档案下的 sync-code**:ops 表标「不适用」,由 operator 自然跳过并在回执注明
  "该 op 于当前档案不适用"——序列照传不用改,不算失败。
- **复现保真**:真实 commit hash 在主流程本地求值(`git -C <源码目录> rev-parse HEAD` 与外层
  `git rev-parse HEAD`)后写进 prompt,由 operator 作为 env 注入启动命令(env 名见 config §5/§9)。
- smoke 失败 → operator 会返回现场信息,**立即停止并修复,不继续 launch**。
- 未启用 `tracking` 时在 prompt 里说明:去掉 tracking 相关 env,并向用户说一句
  "未启用 tracking 模块,跳过跟踪记录——复现信息请自行留档"。

### 三、主流程:转述回执 + 收尾
1. 收到 operator 回执后,向用户转述:**脱敏后的启动命令**(敏感 env 值已是 `***`)、
   各 op 退出码、日志路径、**tracking run id**、查看地址 `<tracking-view>`(若启用 tracking)。
2. 回执「环境事实」字段非空 → 建议用户走 update-workflow(steward)把环境问题记录到 config 对应段。
3. 之后随时用轻 op 跟进(主流程直接执行):
   - `status`:查训练状态 / tail 日志(§7.2 映射的命令)
   - `collect`:训练结束后汇总结果进结果汇总表;并按 §7.3 在确认 run 终态后清理租约
4. **结果解读留主流程**:collect 后对照实验预期给用户讲结论;要系统核查完整性 → audit-results。

## 实验跟踪记录(仅当启用 `tracking`;每次必记,为复现;字段见配置 §9)
- 若 CLI 不发指标 → 用配置 §6 的训练封装调框架训练函数,把 train/test loss 用跟踪 API 记录
- **方向轴字段**(若启用 directions,§10):`direction`/`baseline_group`/`access_level` 由选 slug 自动带出,不手填、防 typo;缺省记 `unspecified`
- 同时记录:**源码 git hash + 完整超参 + 数据划分 + 开启的 flag + seed**
- **数据集版本指针**(若启用 data 且用 DVC,§8):自动记数据集 git hash + .dvc md5 + 数据集名 + 划分,复现靠它锁定输入版本
- **产出存跟踪 artifact**:best + last + 关键 epoch checkpoint;评估可视化若有则上传
- **输入不存跟踪**:数据集/权重另管(见 §8),只记版本指针;中间 checkpoint 不全存,定期清理失败实验
- 评估用配置 §3 的标准指标,不自行定义

## GPU 选卡(共享多卡机;见配置 §6)
- 启动时自动选择**显存最空**的 GPU 并记入跟踪;config 可固定 GPU;并行多实验时由用户显式分配 GPU

## 复现固定项(见配置 §6)
- 固定 seed、确定性算法、cudnn deterministic
- checkpoint:best + last 必存;关键 epoch 节制存;中间不全存

## 约束
- **训练必须走受控启动通道**(Claude hook 或 Codex 主流程预检会阻止直接启动,见配置 §7.1):远程句柄 exec / ssh /
  docker exec / `scripts/run.sh`,由执行档案决定——不得绕开通道直接执行训练
- **关键 op 不得绕过 operator**:主流程不直接执行 sync-code/install-editable/pull-data/smoke/launch
- 正式训练必须后台执行（`-d` 或 nohup + 日志文件），不得以前台方式阻塞；执行全量训练前先执行 smoke test
- operator 带歧义现场返回时,**把问题原样呈给用户确认**,不替它选
