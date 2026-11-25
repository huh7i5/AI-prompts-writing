---
name: paper-audit-submission
description: >-
  Station 04 academic quality-assurance, journal submission, peer-review revision, and post-acceptance skill. Covers cross-section fact/number consistency checks, reviewer-perspective critique, citation support verification, reporting guideline checks (7.1-7.5), reference formatting, cover letters, journal readiness, CRediT/ethics/AI declarations (8.1-8.4), reviewer comment triage, cross-chapter synced revisions, point-by-point response letters (9.1-9.3), and page proof comparison, data archiving, or post-publication corrections (10.1-10.3).
  Use when the user wants to audit a draft against raw tables/sources before submission, prepare submission declarations or cover letters, revise a paper and respond to advisor/reviewer comments, or check page proofs and archiving notes.
  Do NOT use for initial topic brainstorming or external literature discovery (use paper-topic-literature), pre-study research design (use paper-design-evidence), or first-pass prose drafting from outlines (use paper-draft-polish).
---

# Paper Pre-Submission Audit, Peer-Review Revision & Proofs (Station 04)

本 Skill 是学术论文流水线的 **4 号工位（事实数字口径审计、投稿声明、审稿联动返修与校样核查）**，作为论文交付前的最后一道独立质检防线与返修闭环控制器。

核心准则：**局部检查绝不自称全文核验；来源数字冲突时绝不替作者平均或二选一；没有新增实验数据时绝不把“审稿人要求补实验”改写成“我们已补充实验”；未知的伦理、利益冲突与作者同意事项一律标 `[待作者确认]`。**

---

## Step 0：运行时能力探针与核查范围锁定（每次调用必做）

开始核查或整理材料前，先确认宿主工具能力与本次实际读取到的材料范围：

| 探测项 | 判定条件 | 具备能力时的标准动作 | 缺失或受限时的安全降级动作 |
| :--- | :--- | :--- | :--- |
| **`CAP_SCRIPT`** | 可执行本地 `python` 命令 | 先运行 [check_numbers.py](./scripts/check_numbers.py) 提取各段落/表格的样本量与带单位数值排查冲突；交付前运行 [audit_submission_gate.py](./scripts/audit_submission_gate.py) 过门禁 | 声明 `[未启用本地数值扫描脚本]`，人工逐处提取摘要、正文、表格与图注数字逐一核对 |
| **`CAP_EXT_VERIFY`** | 允许联网且用户未限定“仅用给定材料” | `7.4` 可调用 1 号工位 `lit_search_verify.py verify` 核验题录真伪；`8.3` 可核对目标期刊官方最新作者指南 | 严格限定在**用户给定材料内部做一致性与支持度检查**（材料内部一致 ≠ 真实世界已独立核实；未查到 ≠ 文献不存在或造假） |
| **`SCOPE_LOCK`** | 用户提供的是全文还是局部片段/单页校样 | 开头第一句明确交代**本次实际读取了哪些章节/表格/页码，哪些部分未提供** | 凡未提供的章节、图表或校样页，统一列为 `[未提供 - 待核对]`，严禁输出“全文已核验一致”或“已完成整篇校样” |

---

## 任务路由与按需加载规程（Progressive Disclosure）

仅执行用户当前明确请求的子任务（支持合理组合如 `9.2 改稿 + 9.3 逐条回复`；`7.3` 与 `9.1` 明确要求先出诊断/计划时不直接重写全文），并**按需读取**对应的 `references/` 细则：

| 子任务编号与场景 | 必读细则文件 | 核心产出物 |
| :--- | :--- | :--- |
| **7.1 对照原始材料查事实与数字 / 7.2 审稿视角挑刺 / 7.3 提交前综合审计** | [01-pre-submission-audit.md](./references/01-pre-submission-audit.md) | 逐句证据支持与冲突定位（材料足够纠正时给替换段）/ 六列综合审计表（`位置｜问题｜依据｜严重程度｜最小修改方案｜受影响位置`） |
| **7.4 文献身份与论断支持核对 / 7.5 适用报告指南完整性检查** | [01-pre-submission-audit.md](./references/01-pre-submission-audit.md) | “身份状态—读取层级—支持判断—依据位置—待核实”五栏记录（`7.4`）/ 报告指南逐条对照表（`7.5`） |
| **8.1 整理参考文献格式 / 8.2 投稿信 / 8.3 选刊与提交材料核对** | [02-submission-and-declarations.md](./references/02-submission-and-declarations.md) | 缺失标 `[待核实]` 的格式化题录 / 克制真实的 Cover Letter / “可继续准备—必须补齐—需作者确认”清单 |
| **8.4 整理作者贡献、伦理、利益冲突、数据与 AI 使用声明** | [02-submission-and-declarations.md](./references/02-submission-and-declarations.md) | 严格基于已确认事实的各项声明草稿 + 必须由全体作者确认的开放事项清单 |
| **9.1 拆解反馈排改稿顺序 / 9.2 按意见联动改正文 / 9.3 逐条回复审稿人** | [03-peer-review-and-proofs.md](./references/03-peer-review-and-proofs.md) | 优先级修改方案（`9.1`）/ 修订正文 + 跨章同步对照表（`9.2`）/ 区分“已完成/计划补做/不采纳/待核实”的回复信（`9.3`） |
| **10.1 比较接收稿与校样 / 10.2 材料归档说明 / 10.3 发表后错误评估与沟通** | [03-peer-review-and-proofs.md](./references/03-peer-review-and-proofs.md) | 排版错误 vs 实质数字变化分离表（`10.1`）/ 分级共享归档说明（`10.2`）/ 错误影响范围与致编辑沟通草稿（`10.3`） |

---

## 五条不可逾越的硬红线（Boundary Redlines）

1. **多源数字冲突禁止私自裁定（对应 `T06`）**：
   - 当摘要、方法、表格或图注中的样本量/数值相互冲突（如方法写 `102 人`、表 1 写 `120`、摘要写 `200 人`）且无作者更正授权时，必须完整列出三处数字及其原文位置，受影响句子标 `[待作者确认权威数值]`，**严禁私自选一个数、求平均或抹平差异**。
2. **题录存在 ≠ 支持该句论断（对应 `T09`）**：
   - 核查引用时必须把“文献是否存在 → 元数据是否准确 → 实际读到的内容是否支持文中那句话”拆成三步；绝不因题录格式工整就判定支持论断，也不在禁网时凭虚构测试前缀直接武断宣称现实中造假（标为未独立核实并指出内容不支持即可）。
3. **审稿返修严禁伪造“已补实验”与假同步（对应 `T08 / R08 / H03`）**：
   - 没有新增实验结果时，对审稿人要求补充实验或显著性检验的意见，必须如实列为 **`仍待处理 / 计划补做`**，**严禁编造样本数据、`p` 值或写“我们已补充实验”**；
   - 参数或口径变更后（如年度补助封顶调整为 `90 万元`），必须列出计算公式（如 $\min(12\text{万}\times 15, 90\text{万}) = 90\text{万元}$），同步修改所有已提供的摘要、正文、表格与图注，撤除失去依据的派生指标（如缺现金流时的内部收益率），并将未提供的章节列为 `[待核对]`。
4. **投稿声明与隐私零默认假设（对应 `T11`）**：
   - 严禁默认填写“无资助”“无利益冲突”“已获伦理审批”“全体作者同意署名顺序”或生成虚构数据仓库 DOI；含个人隐私的访谈/医疗记录未获公开授权时，严禁建议无条件公开原始材料。
5. **校样实质变化与发表后更正边界（对应 `T12`）**：
   - 校样中出现样本量（如 `30 人` 变 `300 人`）、结果或结论的实质性变动时，严禁直接认可新数字或轻率当成普通排版笔误自行拍板，必须标明表文冲突与影响，交作者与责任编辑共同确认；严禁声称“已提交校样”或“已联系编辑完成更正”。

---

## 确定性工具调用速查（`CAP_SCRIPT` 可用时）

路径相对于本 Skill 根目录（`.agents/skills/paper-audit-submission`）：

1. **运行跨段落/跨文件数值与样本量冲突扫描器**：
   ```bash
   python scripts/check_numbers.py --inputs manuscript_snippets.md [--out-json number_scan.json]
   ```
2. **运行 4 号工位交付前合规硬门禁**：
   ```bash
   python scripts/audit_submission_gate.py \
     --draft station04_output.md \
     --task 9.2 \
     [--no-new-experiments] \
     [--partial-scope] \
     [--unconfirmed-declarations] \
     [--claim-ledger ./paper_workspace/03_backbone/03_claim_ledger.json] \
     [--modified-claims C01]
   ```
   若返回 `"status": "BLOCKED"`（退出码 `2`），必须立即删除越界完成声明、全文已核验夸大语或伪造编号后再交付。
