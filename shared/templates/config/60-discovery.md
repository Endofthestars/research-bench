<!-- 模块:discovery | 吸收段:§12 方向发现
     依赖它的 skill/agent:check-novelty、reviewer;propose-hypothesis / refine-direction 的三关链路、
     strategist 的文献证据基座(evidence-protocol.md 的 §12 条目)也读本段。
     依赖模块:core 必需;directions 强烈建议(关卡产出的落点是方向 dossier);exec 可选(pilot 关卡)。
     启用本模块 + directions 时,init 把方向骨架实例化为 dossier 目录形态(directions/_TEMPLATE/)。 -->

## 12. 方向发现(check-novelty / reviewer / refine-direction 用)

### 12.1 Zotero 文献库(MCP;引用验证的机械载体)
- Zotero MCP 端点:`<例:cookjohn/zotero-mcp(.xpi,MCP server 内置于 Zotero);项目 .mcp.json 里登记的
  server 名,如 zotero>`
- 集合约定:`<例:directions/<slug>——每方向一个集合;查新/调研检出的文献按 DOI/arXiv id 导入对应集合,
  导入成功即「已验证」(见 rf 插件 references/novelty-protocol.md §2)>`
- **未配置时的降级**:引用核验降级为 arXiv / CrossRef / Semantic Scholar 三层核验,验不过标
  `[UNVERIFIED]`;对照表的 Zotero key 列改填「核验来源 + id」。

### 12.2 Codex 通道(跨模型交叉验证)
- Codex MCP 调用方式:`<例:项目 .mcp.json 里登记的 codex server;工具名与参数按其文档,
  主流程按固定问题清单(新颖吗/最接近工作/差异何在/评分 X/10)调用取回裁决,再交给 reviewer 合并>`
- **未配置时的降级**:跨模型交叉验证降级为独立 `reviewer` agent 冷上下文审查
  (同一问题清单,裁决注明「单签(降级)」)。

### 12.3 pilot 预算(env;由项目训练封装读取)
- 预算 env 名:`<例:PILOT_MAX_HOURS=2 / MAX_TOTAL_GPU_HOURS=24>`——plugin 只带接口约定,
  预算裁决在项目训练封装中完成(读 env、超预算自停);启用 exec 时把该封装登记进 §7.2 对应 op 行。
- pilot 结果只进方向 dossier 的 pilot.md + gates.jsonl,**不进论文级消融表**;
  tracking 记录加 `pilot` 标记:`<例:MLflow tag stage=pilot>`,防止混入正式结果。

### 12.4 查新参数(check-novelty / reviewer 用;判定流程见 rf 插件 references/novelty-protocol.md)
- 检索源清单:`<例:arXiv / Semantic Scholar / CrossRef + WebSearch>`
- 近月窗口:`<例:6(强制检索近 N 个月 arXiv,拦未刊预印本)>`
- 新颖性分级门槛:`<例:总分 ≥7/10 建议继续,4–6 谨慎,≤3 放弃>`
- review 分数线:`<例:reviewer 评分 ≥8/10 过关卡 3(默认)>`
- **保护条款(不可自动削弱)**:本节各阈值属于检查标准,修改必须显式说明并经用户确认,
  任何 skill/agent 不得代改。
- **关卡与档位正交**:三关制(证据够不够)与档位(每步谁确认)是两个轴——`auto` / `loop(n)` 档下
  三关照过;跳过任一关卡必须在该方向 gates.jsonl 留 `"verdict":"skip"` 记录(含理由)
  并计入下轮审计,不允许静默跳关。
