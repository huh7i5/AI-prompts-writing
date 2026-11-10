# Language versions

The Chinese and English READMEs are the reference versions. Each language file includes the writing preferences, all 43 numbered task prompts across ten stages, and separate copy-and-paste and Skill instructions. You do not need to switch to English to copy a task.

| Language | File | Scope |
| --- | --- | --- |
| 简体中文 | [README.md](../README.md) | Reference version |
| English | [README.en.md](../README.en.md) | Reference version |
| Español | [README.es.md](../README.es.md) | Full prompt translation |
| Français | [README.fr.md](../README.fr.md) | Full prompt translation |
| Deutsch | [README.de.md](../README.de.md) | Full prompt translation |
| Português | [README.pt.md](../README.pt.md) | Full prompt translation |
| 日本語 | [README.ja.md](../README.ja.md) | Full prompt translation |
| 한국어 | [README.ko.md](../README.ko.md) | Full prompt translation |
| Русский | [README.ru.md](../README.ru.md) | Full prompt translation |

The translations use the task text from commit [`329f86e`](https://github.com/huh7i5/AI-prompts-writing/commit/329f86e). They keep the same task IDs, HTML anchors, links, and placeholder meanings. The navigation names each language in that language, without country flags.

The new translations were prepared and reviewed with model assistance. They have not been reviewed by native-speaking contributors or domain experts, and no behavioral trials have been run in Spanish, French, German, Portuguese, Japanese, Korean, or Russian. The [existing English trials](validation/runs/2026-11-10-en/README.md) cover five English tasks only. Their results do not establish how another language version performs.

The example image remains an English translation of a recorded Chinese run. The standalone Skill remains the shared [Chinese instruction file](../.agents/skills/ai-prompt-writing/SKILL.md); these README translations do not add separately tested language-specific Skills. Supporting source notes and evaluation records keep the language named in their links.

## Review in this update

Translation review on 2026-11-10 checks meaning and document structure, rather than running the prompts as user tasks. Each file is compared with the English reference for task IDs, placeholders, links, code fences, quantities in prompts, and the repeated factual-boundary instruction. Review also covers conditions, negation, uncertainty, citation access limits, and the distinction between completed and planned work.

A separate model reviewer read the French, German, Portuguese, Russian, and Japanese task text and performed an additional focused Spanish review. Corrections included keeping *accuracy* distinct from *precision* in the French and Spanish examples, preserving useful qualifications in French editing instructions, and retaining the “without notice” condition for replacing published results in Japanese. The root review also clarified the distinction between plans made before seeing results and later exploratory analysis. No new behavioral performance claim follows from these checks.

## Keeping versions aligned

When a task changes, compare its numbered block in every language. Preserve negation, uncertainty, units, study conditions, evidence limits, and the separation between completed work and planned work. Check that links, placeholders, command names, and code fences still work. Record behavioral testing separately from translation review, and retain earlier input and output snapshots.

## 语言版本说明

每种语言均包含十阶段、43 个单项任务和总写作要求，直接复制与 Skill 安装分开。翻译以 `329f86e` 的任务文本为基础，保留相同编号、锚点、链接及占位符含义。

新增译文由模型辅助整理和复核，尚无母语贡献者或领域专家审校，也没有做这些语言的行为测试。既有中英文用例不作为其他语言的效果证据。首页图片仍是中文改稿记录的英文翻译；独立 Skill 继续共用中文指令文件。

本次审查核对了任务编号、占位符、链接、代码围栏、任务内数字及事实边界，并检查否定、条件、研究计划与已完成工作的区分。另一个模型代理复核了法、德、葡、俄、日语任务文本，并对西语作重点语义检查。已纠正准确率与精确率混用、限定语译法，以及“未告知便替换已发表结果”的条件遗漏；也澄清了结果出现前的计划与事后探索的区别。这些属于翻译审查，不能算作提示词行为测试。

后续修改任务时，按编号同步所有语言，重点核对否定、条件、不确定性、数字与证据范围。安装命令、占位符、代码围栏和链接也要一起检查。翻译审查与行为测试分别记录，历史输入和输出继续保留。
