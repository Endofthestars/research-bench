<!-- 骨架文件 | 模块:directions(+discovery) | 关卡 1(check-novelty)产出,格式遵 rf 插件的
     references/novelty-protocol.md(discovery 的执行方是 rf);reviewer 交叉验证裁决原文由主流程代笔写入;
     写入经 update-workflow 或用户确认,并向同目录 gates.jsonl 追加 {"gate":"novelty",…} 行
     (schema 见 direction.md 末尾注释)。 -->

# 新颖性档案:<slug>

- **检索时间**:<ISO 日期>;**检索源**:<config §12.4 清单>;**近月窗口**:<N 个月>
- **总分**:<0–10> → **建议**:继续 / 谨慎 / 放弃(门槛见 config §12.4)

## 主张分级
| # | 主张(claim) | 层(方法 / 实验设置) | 分级(高/中/低) | 依据(检索式 + 命中情况) |
|---|---|---|---|---|
| 1 | <一句话主张> | <层> | <级> | <3 种表述与命中摘要> |

## 最接近前期工作对照表
> 每行必须带 Zotero key(novelty-protocol.md §2);无 Zotero 时降级填「核验来源 + id」,
> 验不过标 `[UNVERIFIED]`(不得作为判定依据)。

| 前期工作(Zotero key) | 重合点 | 差异点 | 威胁等级(高/中/低) |
|---|---|---|---|
| <key:引用> | | | |

## 交叉验证裁决(原文区)
> 双签:Codex 通道裁决 + reviewer 自身检索结论,矛盾处如实并列;
> 未配置 Codex 时单签并注明「降级」。

### Codex 裁决原文
<原文粘贴;未配置则写「未配置 Codex 通道,降级为单签」>

### reviewer 盲评初判(第一段:仅核心主张)
<原文粘贴>

### reviewer 检索结论(第二段:全档终判)
<原文粘贴;初判被终判推翻时须含原因说明>

## 衍生种子(可选)
> 仅当建议为「谨慎/放弃」:查新过程暴露的相邻空白点(如撞车论文未覆盖的设置),记 1–2 行;
> 可经 update-workflow 登记进 RESEARCH_ROADMAP「种子池」。

| 种子(一句话) | 触发来源(撞车论文 Zotero key) |
|---|---|
| | |
