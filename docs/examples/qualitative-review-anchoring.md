# 示例：无 CSV 统计数据场景——纯 PDF/全文文献综述页码锚定与相关工作撰写（`review`）

并非所有论文都有实验 CSV 和统计 `p` 值。人文社科、政策档案与纯文献综述（`FOCUSED_REVIEW` / `QUALITATIVE`）的核心痛点在于**多篇文献如何不写“流水账”、且每个观点都能回溯到原文准确页码与段落**。

本示例演示 1 号工位 `fulltext_indexer.py` + `lit_gate_check.py` 在**无定量统计数据**下的完整落地实测。

---

## 一、 原始文献切片与页码建库（真实脚本实测）

准备两份研究原文材料（`chen2023_fieldwork.md` 跨第 1–2 页，`taylor2024_policy.md` 第 1 页），运行：

```bash
python .agents/skills/paper-topic-literature/scripts/fulltext_indexer.py index \
  --input ./sources --out-jsonl ./fulltext_chunks.jsonl --ledger ./02_literature_ledger.json

python .agents/skills/paper-topic-literature/scripts/fulltext_indexer.py search \
  --index ./fulltext_chunks.jsonl --query "警报 疲劳 跳过 弹窗 24 名 城区 农村" --top-k 3
```

**实测检索结果（直接返回 `[文件名, 页码, 段落]` 硬锚点，并将账本从 `ABSTRACT_ONLY` 升级为 `FULLTEXT_READ`）**：

```json
{
  "query": "警报 疲劳 跳过 弹窗 24 名 城区 农村",
  "total_hits": 2,
  "top_hits": [
    {
      "score": 3.0,
      "anchor": "[chen2023_fieldwork.md, p.1, para.1]",
      "excerpt": "通过对某市 3 家社区卫生中心共 24 名全科医生的半结构化访谈，作者指出基层电子病历弹窗警告平均每天触发 42 次，导致约三分之二的常规提示被直接跳过。"
    },
    {
      "score": 2.0,
      "anchor": "[chen2023_fieldwork.md, p.2, para.1]",
      "excerpt": "研究同时交代该观察仅涵盖城区三家站点，农村乡镇卫生院因接诊节奏不同未纳入比较，因此外推范围有限。"
    }
  ]
}
```

---

## 二、 生成的相关工作段落（按争议脉络组织，拒绝逐篇罗列 + 拒绝索要 `p` 值）

> 围绕基层临床决策支持系统的“警告疲劳”问题，既有研究在干预重点上存在分歧。基于对 3 家城区社区卫生中心 24 名全科医生的半结构化访谈，`[@chen2023fieldwork]`（证据位置：`[chen2023_fieldwork.md, p.1, para.1]`；局限见 `[chen2023_fieldwork.md, p.2, para.1]`：样本仅限城区机构，未纳入农村乡镇卫生院）记录到常规弹窗高频触发后易被跳过；相比之下，`[@taylor2024policy]`（证据位置：`[taylor2024_policy.md, p.1, para.1]`）通过对 2018—2023 年 18 份市政政策档案的分析指出，只有配合分诊护士预筛而非单纯重设计弹窗界面时，跳过率才出现下降。

---

## 三、 过门禁检验结果（实跑 `lit_gate_check.py`）

```bash
python .agents/skills/paper-topic-literature/scripts/lit_gate_check.py \
  --draft ./review_para.md --mode related-work --ledger ./02_literature_ledger.json
```

实测输出：

```json
{
  "mode": "related-work",
  "status": "PASS",
  "blocker_count": 0,
  "warn_count": 0,
  "findings": []
}
```

**关键合规点**：
1. 全文每个具体论断均对应实际读到的页码与段落锚点；
2. 完整保留了原始研究第 2 页关于“未覆盖农村乡镇卫生院”的外推限制，没有用“弥补了基层医疗全部空白”等夸大词；
3. 针对该质性/档案研究，全程不强行要求统计检验或样本功效计算。
