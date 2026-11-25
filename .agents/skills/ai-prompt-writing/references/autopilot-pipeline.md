# 端到端全自动论文流水线编排规程（Writer vs. Reviewer 对抗闭环）

当用户提供了工作区目录（或原料包：`raw_data.csv`、本地文献 PDF 文件夹、研究简报）并要求**“按端到端流水线推进整篇论文直到打包交付”**时，总控 Agent（`ai-prompt-writing`）按本规程执行自动化接力与多角色盲审闭环。

---

## 一、 核心流水线五步接力协议

```text
原料入厂 (PDFs + raw_data.csv + brief)
  ├──► Station 01 (paper-topic-literature)
  │      1. lit_search_verify.py 查核真实 API 题录与摘要 -> 02_literature_ledger.json + verified_refs.bib
  │      2. fulltext_indexer.py 解析本地全文 PDF/TXT -> fulltext_chunks.jsonl（精准升级 FULLTEXT_READ 与页码锚点）
  ├──► Station 02 (paper-design-evidence)
  │      1. init_workspace.py 初始化工作区 01_literature .. 06_submission
  │      2. stats_and_plot.py 对 raw_data.csv 跑确定性统计检验 + 生成 SVG 矢量图与图注 -> 写回 RECOMPUTED_LOCAL 证据
  │      3. 锁定 03_backbone/03_claim_ledger.json 与 04_outline.md -> 过 design_evidence_gate.py
  ├──► Station 03 (paper-draft-polish)
  │      1. 严格依照 03_claim_ledger.json、04_outline.md 与 [p.X, para.Y] 原文锚点撰写 04_drafts/*.md
  │      2. 过 style_and_draft_gate.py（去 AI 套话、去空泛自谦、核查数字保真）
  ├──► 对抗盲审闭环 (Blind Reviewer #2 <-> Station 04 联动返修)
  │      1. 拉起独立上下文的 Reviewer 子代理（只喂成稿 + 文献账本 + 主张账本 + 统计输出，不继承撰稿人思考过程）
  │      2. 逐条审出事实冲突、论证跳跃、替代解释遗漏 -> 写入 05_audit/reviewer_feedback.md
  │      3. 调用 Station 04（9.2 联动同步改稿）与 check_numbers.py 逐一修正并同步摘要/表格/结论
  └──► 全站联检 & 成品编译打包
         1. 运行 python scripts/pipeline_doctor.py run-gates --workspace <dir> 确认全部硬门禁 PASS
         2. 运行 export_manuscript.py 打包导出 06_submission/manuscript.docx 与 manuscript.tex
```

---

## 二、 上下文隔离对抗盲审规则（如何防止“自己审自己放水”）

1. **信息隔离原则**：若当前宿主支持 `invoke_subagent`（子代理），必须指派一个独立子代理扮演 **“严格但建设性的领域审稿人（Reviewer #2）”**。
2. **输入清单限定**：只向审稿子代理传入：
   - `04_drafts/*.md`（待审文稿）；
   - `01_literature/02_literature_ledger.json`（核对有无歪曲文献或超摘要深度推断）；
   - `03_backbone/03_claim_ledger.json` 与 `02_evidence/*_stats.json`（核对数字、条件限制与不利权衡是否全部保留）；
   - `05_audit/` 下确定性脚本输出的报告。
3. **打回与收敛条件**：
   - 最多执行 **2 轮“审稿挑刺 → 联动返修”闭环**；
   - 若审稿人要求补充目前工作区完全没有的新实验或新受试者数据，**严禁伪造补做**——由 Station 04 写入未决清单与审稿回复信预案，待人类作者实地补齐数据；
   - 仅当 `pipeline_doctor.py run-gates` 返回 `"overall_status": "PASS"`（或无 `BLOCKER` 级别故障）时，才允许进入最终 `.docx`/`.tex` 编译导出。

---

## 三、 人类作者必须接管的停驻节点（Human-in-the-Loop Gates）

自动化工厂绝不替人类作者越权拍板以下三件事，遇到时自动保存当前阶段产出并停驻提示确认：
1. 研究尚在 `PRE_STUDY` 阶段、没有任何实测数据时（停止在 `04_outline.md` 与带 `[待补]` 槽位的方法计划）；
2. 原始材料内部出现无更正记录的数值/版本冲突（如两份表格样本量打架）；
3. 投稿阶段的作者最终署名顺序、资助编号、利益冲突声明、伦理审批号与受限数据公开授权。
