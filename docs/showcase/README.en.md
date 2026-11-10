# A short introduction, before and after editing

[简体中文](README.md) · [Back to the project](../../README.en.md#showcase)

Recorded on 2026-11-10. A short introduction was first generated from an ordinary writing request. It was then revised using the project's Skill and prompt 6.2. Each step used a fresh sub-agent context. The first draft and the complete revision response are retained.

The English passages below are translations prepared for this page. The model runs were conducted in Chinese.

## Initial request

The request asked for a Chinese introduction of about 150 characters on generative AI-assisted rewriting and undergraduates' source-checking behavior. Only the topic had been decided. No literature, study design, or results were supplied. The model was asked to return prose only.

The exact Chinese request and revision instructions are saved with the example. The drafting context received the writing request and file handling instructions, without instructions to introduce weaknesses. The first draft was used.

## First draft

Generative AI can assist undergraduates in rewriting text by adjusting wording and sentence structure, but fluent expression does not by itself establish fidelity to the original source. Whether students return to the source before adopting rewritten text, and how they check key concepts and arguments, are questions worth examining in this setting. Studying the relationship between AI-assisted rewriting and undergraduates' source-checking behavior can help clarify information judgment and academic responsibility in technology-assisted writing.

[Original Chinese output](draft-before.md)

## Revised with the project

Generative AI can assist undergraduates in rewriting text by adjusting wording and sentence structure, but fluent expression does not by itself establish fidelity to the original source. This study aims to examine the relationship between AI-assisted rewriting and undergraduates' source-checking behavior, focusing on whether students return to the source before adopting rewritten text and how they check whether key concepts and arguments in the rewritten text are consistent with the original.

[Complete revision input in Chinese](revision-input.md) · [Complete revision output in Chinese](draft-after.md)

The revision input included the project's Skill as it stood on that date and prompt 6.2. It allowed clarification of what source checking means while leaving the observation method for the author to decide.

## What changed

| Location | Original wording | Actual edit and reason |
| --- | --- | --- |
| Opening | Fluent expression does not by itself establish fidelity to the original source | Kept in full. The distinction was already clear |
| Focus of checking | How they check key concepts and arguments | Specified checking whether concepts and arguments in the rewritten text are consistent with the original source |
| Purpose | Can help clarify information judgment and academic responsibility | Replaced with “This study aims to examine,” positioning the research relationship before the concrete questions and removing a broad closing claim |

The first draft was already cautious. The edits concern references within sentences, ordering, and information density. The author still needs an observation method, materials, and results. The opening is background framing and would also need appropriate support when used in a real manuscript.

![English translation of the editing example](../../assets/showcase-before-after-en.png)

The English image and passages translate the recorded Chinese example. Separate direct trials of selected English task prompts are recorded in the [English behavior report](../validation/runs/2026-11-10-en/README.md). This illustration remains a translation of the Chinese run. The image-generation prompts are available in the [generation record](../../assets/showcase-before-after-prompt.md).

## How this example was produced

Both steps ran in the default model environment of this Codex session, without web access, analysis, or citation checking. An exact API model identifier, sampling configuration, and random seed were not fixed. Revision used both the Skill and task instructions, so the example cannot isolate the contribution of any one rule. Assessment by real authors and additional examples remains necessary.

This replaces the demonstration created on November 8. Its drafting task had explicitly requested common weaknesses, and its image was generated without the full recorded paragraphs. That produced a mismatch between the image and saved text. The old version remains in Git history. This example starts again from a neutral request.

The public example is newly written. Earlier private editing work supplied general checks on structure, references, and linked revisions.
