# 工作日，谁在租共享单车？

[读研究样稿](workspace/04_drafts/manuscript.md) · [看给 Agent 的任务](input.md) · [查看审查记录](workspace/05_audit/04-audit.md)

只看总量，华盛顿 Capital Bikeshare 在工作日平均每天多租出 254.7 次。拆开后能看到两种相反的变化。与非工作日相比，注册用户日均多租 1019.2 次，临时用户日均少租 764.6 次。2011 年和 2012 年分别计算，方向都一样。三个差值分别从未取整的均值算出，显示到一位小数。[原始日表](workspace/02_evidence/day.csv) · [分年结果和分母](workspace/02_evidence/results.json)

## 这篇文章怎么写出来的

2026 年 11 月 25 日，我们在 Codex 中从公开版的独立工作目录开始，用仓库里的总控和四个 Skill 完成这次试跑。选用的数据集已有明确的工作日定义和两类用户的计数，文章里的每个表格数值都能复算。[本次测试的版本 `3459e7f`](https://github.com/huh7i5/AI-prompts-writing/tree/3459e7fbd4a7d16edfd2abf7085d2775d92d1577) · [UCI 数据说明](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset)

| 环节 | 这次实际做了什么 | 可查材料 |
| --- | --- | --- |
| 选题与找文献 | 聚焦两类用户的日均租借量。关键词检索返回的两项都不符合选题，Agent 通过 UCI 数据页和定向查找补齐了三项来源，并用仓库脚本逐条核验 DOI。两篇期刊论文的使用限于实际读到的摘要。 | [来源与检索结果](workspace/01_literature/source_note.md) |
| 设计与算数据 | Agent 编写脚本，读取 731 天的原始日表，核对每一天的合计，再按日类型求均值。分年和合并的计算完成后，才把研究状态改为已有结果。 | [数据、许可与计算口径](workspace/02_evidence/data-source.md) · [三条主张及证据](workspace/03_backbone/03_claim_ledger.json) |
| 起草 | 写作 Agent 读取文献、结果、主张与提纲，写出中文稿。表 1 给出每组均值和差值，可直接与日表对照。 | [提纲](workspace/03_backbone/04_outline.md) · [文章](workspace/04_drafts/manuscript.md) |
| 审查 | 另一个 Agent 按仓库说明复查稿件，核对数字、引用和解释范围。为检验表格有没有把数字配错对象，本例另外做了逐格复算和故意改错的对照。 | [审查记录](workspace/05_audit/04-audit.md) · [独立复算脚本](check_sample.py) |

文献查找与数据准备并行，写作等到两者就绪才开始。总控根据当时已有的文件，依次建议了选题、设计、写作和审查四站。计算脚本、调度和文章由本次 Codex 会话完成，仓库自带的脚本用于诊断和检查。

本次四站的检查都返回了 `PASS`。终稿审查结束后再运行总控诊断，它识别到了审查报告，仍建议进入审查工位。本例以稿件修订和复算完成作为结束条件。

## 原有检查能发现什么

初稿通过了仓库的写作检查。审稿时，另一个 Agent 指出了讨论里“临时用户在非工作日租车更频繁”可能被理解为每个人租得更勤。日表只统计全系统的租借次数。这条反馈用来修订摘要和讨论。[初稿](workspace/05_audit/first-draft.md) · [修订稿](workspace/04_drafts/manuscript.md)

我们还保留了所有数字，只在临时副本里对调“合并”部分的两个行名。例如，原属临时用户的 606.6 次/日被标到注册用户名下。注册用户的实际值是 3978.3 次/日。

| 送检文本 | 仓库原有的润色检查 | 本例另写的逐格复算 |
| --- | --- | --- |
| 修订稿 | 通过 | 27 个数全部吻合 |
| 两个用户标签对调的副本 | 通过 | 定位到 6 处错配，涉及两行各三个数 |

数字还在文中，所属用户却变了。这个例子说明，若要让 Agent 自动交付一篇数据文章，还需要核对每一个数对应的行、列和单位。当前附加脚本核验本例表格的年份、用户类别、日类型和数值；单位和正文解释由审稿 Agent 对照原始材料检查。[逐格结果](checks/table.json) · [错配明细](checks/control.json)

仓库自带的数字扫描还读了修订稿的 27 个文本块，提取到的样本量和带单位数值都是 0。稿中用“天”描述分母，用“次/日”作为表题单位。对于这种写法，扫描输出里的“0 条提醒”需要和实际识别了多少数字一起看。[原始扫描结果](workspace/05_audit/04-number-scan.json)

## 自己跑一遍

从本例目录打开终端。下列命令只使用 Python 标准库和已附的数据。

```sh
python workspace/02_evidence/analysis.py --check
python check_sample.py
python control.py
```

第一条从日表重算并对照保存的统计结果。第二条直接从日表核对稿件。第三条在临时副本里交换合并组的两个用户标签，再比较两种检查的结果。文献检索需要联网，完整查询式和当时的接口响应也已保留。[检索命令](workspace/01_literature/commands.md) · [原始响应](workspace/01_literature/raw)

<details>
<summary>复查本次用到的仓库原生脚本</summary>

在仓库根目录打开 PowerShell。下面读取已归档的工位产物，可离线重跑诊断、初稿检查、修订检查与终稿审查。语言模型生成的文字以本例保存的两个版本为准；重新生成文章时，措辞可能变化。

```powershell
$skillDir = ".agents/skills"
$work = "docs/validation/runs/2026-11-25-bike-sharing/workspace"
$claim = "$work/03_backbone/03_claim_ledger.json"
$lit = "$work/01_literature/02_literature_ledger.json"
$paper = "$work/04_drafts/manuscript.md"
$review = "$work/05_audit"

python "$skillDir/ai-prompt-writing/scripts/pipeline_doctor.py" diagnose --workspace "$work"
python "$skillDir/paper-topic-literature/scripts/lit_gate_check.py" --draft "$work/01_literature/source_note.md" --mode related-work --ledger "$lit"
python "$skillDir/paper-design-evidence/scripts/design_evidence_gate.py" --draft "$work/03_backbone/04_outline.md" --claim-ledger "$claim" --task 3.4,4.3 --paradigm quantitative --time-state post-results
python "$skillDir/paper-draft-polish/scripts/style_and_draft_gate.py" --draft "$review/first-draft.md" --mode draft --section results --claim-ledger "$claim" --lit-ledger "$lit"
python "$skillDir/paper-draft-polish/scripts/style_and_draft_gate.py" --draft "$paper" --mode polish --source-text "$review/first-draft.md" --claim-ledger "$claim" --lit-ledger "$lit"
python "$skillDir/paper-audit-submission/scripts/check_numbers.py" --inputs "$paper"
python "$skillDir/paper-audit-submission/scripts/audit_submission_gate.py" --draft "$review/04-audit.md" --task 7.1,7.4 --claim-ledger "$claim"
```

</details>
