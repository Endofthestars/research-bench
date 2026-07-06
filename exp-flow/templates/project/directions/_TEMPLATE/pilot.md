<!-- 骨架文件 | 模块:directions(+discovery;exec 可选) | 关卡 2(pilot)产出;
     当前批次 pilot 的通过/失败由人工判定,执行约定(预算 env、tracking pilot 标记)见 config §12.3;
     跳过本关时在此记理由,并向同目录 gates.jsonl 追加 {"gate":"pilot","verdict":"skip",…} 行
     (schema 见 direction.md 末尾注释)。 -->

# 试点结果:<slug>

- **结论**:有信号 / 无信号 / 跳过(理由:<例:纯理论论证充分 / 无 exec 环境,人工判定放行>)
- **预算**:<例:PILOT_MAX_HOURS=2,实际用时 <N>h>(env 名见 config §12.3)

## 试点实验
> pilot 结果只进本文件 + gates.jsonl,**不进论文级消融表**;tracking 记录须带 `pilot` 标记(§12.3)。

| run(tracking id,含 pilot 标记) | config | 关键指标(config §3) | 观察 |
|---|---|---|---|
| | | | |

## 解读
<实证信号支持 / 否定 direction.md 里的哪条 claim;信号强弱与置信度;对下一关(review)的提示>
