# 阶段二细则（上）：检索策略、真实文献搜集与证据矩阵比较（任务 2.1 & 2.2）

本规程用于处理 **2.1 找搜索关键词和相关资料** 与 **2.2 比较读过的文献，确定自己要研究什么**。

---

## 一、 任务 2.1：把初步想法变成检索行动（联网 vs 离线双轨协议）

### 第一步：概念拆解与“正反双向”检索式构造（所有环境必做）
不要只顺着用户的预期结论搜同向文献！把用户的初步想法拆成 4 个槽位：
1. **研究对象与场景（Population / Context）**：如 `undergraduate` / `college students` / `course assignment`；
2. **核心干预、现象或技术（Intervention / Phenomenon）**：如 `generative AI` / `LLM` / `AI-assisted rewriting`；
3. **目标结果或关注变量（Outcome / Metric）**：如 `source verification` / `citation checking` / `fact-checking` / `epistemic vigilance`；
4. **反向证据、零结果与替代方法（Counter-evidence / Alternative Mechanism）**：专门加入可能推翻或修正原假设的检索词，例如：
   - 负面/促进两面性：既查 `overreliance / automation bias / citation hallucination`（削弱核对），也查 `critical AI literacy / scaffolding / verification behavior improvement`（促进核对或无显著影响）；
   - 不同研究方法：如实验对照、日志追踪、质性访谈或课堂观察。

默认输出 **精简可直接复制执行的方案**：核心中英文关键词对照表 + **2–4 条布尔检索式**（适配 Web of Science / Scopus / Google Scholar / CNKI 等常见语法）+ 明确的纳入/排除筛选标准（时间范围、文献类型、对象匹配度）。未要求写教程时，不要输出冗长的数据库使用说明书。

### 第二步：按联网与脚本能力分轨执行（严格隔离计划与结果）

#### 分支 A：允许联网且可执行 `lit_search_verify.py`（推荐自动化路径）
运行内置零依赖脚本同时检索正向与反向/替代视角文献：
```bash
python .agents/skills/paper-topic-literature/scripts/lit_search_verify.py search \
  --query "generative AI undergraduate source verification fact checking" \
  --counter-query "AI writing literacy critical evaluation null effect scaffolding" \
  --since 2023 \
  --max-results 8 \
  --out-ledger 02_literature_ledger.json \
  --out-bib verified_refs.bib
```
- **按纳入/排除标准筛除跨领域噪声后再汇报**：开放 API 关键词检索常混入跨学科同名术语噪声。请先交代脚本去重检出的总条数，再依据第一步制定的纳入/排除标准筛出真正切题的核心文献，逐条列出标题、作者、年份、标准 `https://doi.org/<doi>` 或 `arXiv` 链接、核验源、**实际读取深度**（`ABSTRACT_READ` 或 `METADATA_ONLY`）及与选题的关系，并简要说明被剔除条目的噪声原因。
- **中英文双语检索边界说明**：内置免 Key 接口（OpenAlex / CrossRef / arXiv）主要覆盖英文国际期刊、会议与预印本，不直接索引中国知网（CNKI）或万方全文库；当用户需要中英文双语材料时，用英文检索词跑脚本获取真实国际文献，同时提供可直接复制的中文专业检索式供用户在校园网环境下补查中文库。
- **严禁越界推断**：脚本拉回的是题录与摘要（`ABSTRACT_READ`），不能把摘要概述当成已核实全文实验细节；若某篇只有题录无摘要（`METADATA_ONLY`），必须注明“仅核实题录存在，尚未获取摘要/全文，待精读确认”。

#### 分支 B：用户明确禁止联网、或宿主机断网（离线安全路径）
- 若调用脚本，脚本会自动返回 `"capability_state": "OFFLINE_FALLBACK"`（也可显式传 `--offline`）。
- **绝对禁令**：在“实际找到或未找到的材料”一栏，必须明确写明 **“本次未执行外部检索（离线模式），以下仅为检索计划，未列出任何参考文献”**。**严禁凭训练记忆背诵任何作者、年份、论文标题或 DOI！**
- 若启用了本地门禁脚本，交付前跑一次离线门禁自检：
  ```bash
  python .agents/skills/paper-topic-literature/scripts/lit_gate_check.py --draft output.md --mode search-offline
  ```

### 第三步：强制四段式收尾结构
无论联网还是离线，2.1 的输出至少清晰包含以下四块：
1. **检索方案**（概念拆解、中英文关键词、2–4 条含正反方向的检索式、筛选标准）；
2. **实际找到或未找到的材料**（联网时列已核验清单与读取深度；离线时明确标为“未执行检索 / 仅提供计划”）；
3. **当前能确认什么、还不知道什么**（严禁凭一次检索没搜到或离线未查就断言“目前尚无研究”）；
4. **下一步最值得优先精读或补查的方向**。

---

## 二、 任务 2.2：多文献证据矩阵比较与问题聚焦

当用户提供多篇文献、摘要、阅读笔记，或已通过 `2.1` 生成 `02_literature_ledger.json` 时，按以下步骤收敛问题：

### 1. 先查来源身份与读取深度
- 若材料带 DOI / `arXiv` 编号：允许联网时运行 `lit_search_verify.py verify` 独立核验题录真伪；禁止联网时加 `--offline` 做本地伪造测试前缀筛查；
- 标清每份材料的证据层级：用户仅给了摘要或读书笔记时，标为 `摘要级 / 用户笔记级（未读全文）`，不得替原文补写实验样本细节或隐藏条件。

### 2. 建立结构化比较矩阵（禁止“一篇一段读后感”式罗列）
输出一张清晰的横向对比表：

| 来源编号 / 文献 | 读取深度 | 研究问题与场景 | 对象 / 数据 / 规模 | 方法与比较基线 | 核心发现（保留原数值与方向） | 明确限制或未覆盖条件 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |

### 3. 提炼共识、分歧与“三类缺口分离”
表格之后，围绕议题横向归纳：
1. **已有研究的一致认识**（哪些现象在多篇材料中得到了相符观察，基于哪几篇）；
2. **结论分歧及条件差异**（为什么 A 与 B 结论不同？是因为样本群体、任务设置、评价指标还是测量时间不同？）；
3. **严格区分三类“缺口/切入点”**（绝不混为一谈）：
   - **文献明确自述的限制**（某文作者在摘要/讨论中自己指出的不足，附来源位置）；
   - **跨文献比较推导出的待验假设**（把 A 的设置与 B 的问题交叉后浮现的可检验问题）；
   - **仍需补充检索或读全文才能确认的空白**（提醒用户：手头这几篇没提到 X，不代表整个学界没人做过 X，需针对 X 再做一次专项检索确认）。
