# 写作对照图生成记录

日期为 2026-11-10。两张图均由内置 image_gen 新生成，采用像素手稿风格。正文来自本次固定的首次生成与项目改稿记录，完整输入和文字记录见 [示例记录](../docs/showcase/README.md)。

中文图为 [showcase-before-after.png](showcase-before-after.png)，英文图为 [showcase-before-after-en.png](showcase-before-after-en.png)。两张图均为 1586×992 像素。英文图使用中文示例的忠实翻译，其语言版本未作为独立的英文模型运行或性能测试。

## 目视核对

已逐句对照生成前固定的文字，核对了两栏全文、两版相同的首句、段落末句和底部三条说明。图中没有新增或遗漏正文句子。英文左栏末尾的 technology-assisted 在行尾换行，保留了原有连字符。标记只突出后半段调整，原首句在两栏保持相同。图片没有总标题、检测率、得分或虚构引用。

长段文字在窄屏会缩小，完整可复制文字在示例记录中提供。图片只用于呈现这次局部修改。

## 中文图实际生成提示词

```text
Use case: infographic-diagram. Create a new original pixel-sketch academic notebook comparison illustration for a GitHub README.
Landscape canvas about 16:10, high-resolution around 2400×1500. Generous white/very pale warm paper background, almost invisible grid. Two equal rectangular manuscript panels side by side with ample text area. Small stepped dark navy outlines and one modest pixel arrow between them. A restrained teal accent and a little rust-red, subtle pixel clusters and stepped edges. Mature scientific sketchnote, not cute, not watercolor, not glossy cards, not 3D. No decorative objects consuming space. No overall title and no top banner.

The main purpose is exact text comparison. Typeset the FULL text supplied below VERBATIM. No paraphrasing, no inserted words, no omitted words, no invented text. Body typography crisp and easily readable at 900 px displayed width. Use clean regular typography with slight pixel-inspired styling only on borders and arrows; exact characters matter more than stylistic effects. The two first sentences are identical and must appear identically. Keep the opening visually unmarked or identically pale in both panels. Make the change in later sentences visible with very light teal underline and a small rust-red margin mark, without crossing or obscuring text.

Left panel label (only this label): "首次生成"
Left panel body, quote verbatim, preserve punctuation and ALL words:
"生成式AI能够通过调整措辞、重组句式辅助本科生改写文本，但流畅的表达并不直接表明改写内容忠实于原始来源。学生在采纳改写文本前是否回查原文、如何核对关键概念与论证含义，是这一使用情境中值得关注的问题。围绕生成式AI辅助改写与本科生来源核对行为的关系展开研究，有助于进一步理解技术辅助写作中的信息判断与学术责任。"

Right panel label (only this label): "项目修改后"
Right panel body, quote verbatim, preserve punctuation and ALL words:
"生成式AI能够通过调整措辞、重组句式辅助本科生改写文本，但流畅的表达并不直接表明改写内容忠实于原始来源。本研究拟考察生成式AI辅助改写与本科生来源核对行为的关系，重点关注学生在采纳改写文本前是否回查原文，以及如何核对改写文本中的关键概念和论证含义是否与原文一致。"

Bottom strip with three equally spaced short labels, exactly:
"首句保留"
"明确核对对象"
"删去空泛结尾"

Small footer label in the bottom right, exactly "单次修改示例".

No other text, no percentages, no invented grades, no detection scores, no fake citations, no publisher logos or watermarks, no giant heading. The actual changes are preserving the first sentence, clarifying the checking target and source-consistency relation, and removing a vague closing. Do not depict an already strong original as a failure. Each paragraph must stay within its own panel and have balanced line spacing. Render hyphens, apostrophes and punctuation faithfully.
```

## 英文图实际生成提示词

```text
Use case: infographic-diagram. Create a new original pixel-sketch academic notebook comparison illustration for a GitHub README.
Landscape canvas about 16:10, high-resolution around 2400×1500. Generous white/very pale warm paper background, almost invisible grid. Two equal rectangular manuscript panels side by side with ample text area. Small stepped dark navy outlines and one modest pixel arrow between them. A restrained teal accent and a little rust-red, subtle pixel clusters and stepped edges. Mature scientific sketchnote, not cute, not watercolor, not glossy cards, not 3D. No decorative objects consuming space. No overall title and no top banner.

The main purpose is exact text comparison. Typeset the FULL text supplied below VERBATIM. No paraphrasing, no inserted words, no omitted words, no invented text. Body typography crisp and easily readable at 900 px displayed width. Use clean regular typography with slight pixel-inspired styling only on borders and arrows; exact characters matter more than stylistic effects. The two first sentences are identical and must appear identically. Keep the opening visually unmarked or identically pale in both panels. Make the change in later sentences visible with very light teal underline and a small rust-red margin mark, without crossing or obscuring text.

Left panel label (only this label): "First draft"
Left panel body, quote verbatim, preserve punctuation and ALL words:
"Generative AI can assist undergraduates in rewriting text by adjusting wording and sentence structure, but fluent expression does not by itself establish fidelity to the original source. Whether students return to the source before adopting rewritten text, and how they check key concepts and arguments, are questions worth examining in this setting. Studying the relationship between AI-assisted rewriting and undergraduates' source-checking behavior can help clarify information judgment and academic responsibility in technology-assisted writing."

Right panel label (only this label): "Revised with project"
Right panel body, quote verbatim, preserve punctuation and ALL words:
"Generative AI can assist undergraduates in rewriting text by adjusting wording and sentence structure, but fluent expression does not by itself establish fidelity to the original source. This study aims to examine the relationship between AI-assisted rewriting and undergraduates' source-checking behavior, focusing on whether students return to the source before adopting rewritten text and how they check whether key concepts and arguments in the rewritten text are consistent with the original."

Bottom strip with three equally spaced short labels, exactly:
"Keep the opening"
"Clarify what is checked"
"Remove a vague closing"

Small footer label in the bottom right, exactly "One editing example".

No other text, no percentages, no invented grades, no detection scores, no fake citations, no publisher logos or watermarks, no giant heading. The actual changes are preserving the first sentence, clarifying the checking target and source-consistency relation, and removing a vague closing. Do not depict an already strong original as a failure. Each paragraph must stay within its own panel and have balanced line spacing. Render hyphens, apostrophes and punctuation faithfully.
```
