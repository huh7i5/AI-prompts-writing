# English behavior trials — 2026-11-10

[Fixed cases and criteria](cases.md) · [Revision and retry](revision.md) · [中文验证说明](../../README.md) · [English prompt collection](../../../../README.en.md#quality)

Six fixed English inputs were run once each in fresh contexts. Five met their prewritten criteria. E06 partially met its criteria because a confirmed operating status was preserved in the analysis but omitted from the replacement prose. Prompt 7.1 was then revised, and E06R met the original criteria on a fresh run. The first E06 output and its partial judgment are retained.

This covers five distinct English prompts out of 43 numbered tasks: 6.1, 6.2, 6.3, 7.1, and 9.2. The other 38 English tasks have not had behavior trials in this round.

## Initial results

| Case | Judgment against fixed criteria | Evidence in the output | Observation |
| --- | --- | --- | --- |
| [E01](E01.md) | Pass | Rewrites the paragraph, removes the metaphor, aside, and repeated closing, preserves 12 ms and 18 ms, and limits the result to the single measurement. | The revision focuses on the measured result and declines the unsupported record-management benefit. |
| [E02](E02.md) | Pass | Maps reader questions and section roles, merges duplicated material, flattens the hierarchy, and supplies revised sections with permission and validation limits. | The explanation is long relative to the short draft and repeats the plan in several forms. |
| [E03](E03.md) | Pass | Changes P1, Table 1, A1, and C1 to capped annual support of CNY 0.9 million, correctly computes the cap, and removes the unsupported 12% return. | The pre-cap CNY 1.8 million remains explicitly labeled as the intermediate calculation. It is not a stale final support amount. |
| [E04](E04.md) | Pass | Keeps the original paragraph verbatim, including first person, 89% and 90%, and the single-measurement qualification. | Adds author questions about the measurement scope and test data while leaving the prose intact. |
| [E05](E05.md) | Pass | Corrects the comparison in the abstract, preserves the numbers, and keeps both replication and statistical reporting requests unresolved. | No invented participants, result, p-value, line number, or unseen section update. |
| [E06](E06.md) | Partial | Distinguishes design capacity, cumulative scenario output, annual flow, and actual operation, but its proposed replacement sentences omit the explicitly supplied not-yet-operating status. | That status appears repeatedly in the analysis. The partial judgment concerns the usable replacement prose under the second prewritten criterion. |

For E06, the second criterion explicitly requires recommended wording that retains both source quantities and the not-yet-operating status. The initial answer retained the status in its evidence table, so judging the whole answer as retaining it would be a more permissive interpretation. This record uses the stricter reading of the actual replacement prose. It is a narrow omission, not a fabricated operating result.

## Targeted change and retry

Prompt 7.1 now asks for coherent replacement prose that retains confirmed study stage, operating status, and necessary conditions whenever the supplied materials support a correction. The Chinese prompt and Skill were updated alongside the English prompt. Other task prompts were not changed.

| Follow-up | Judgment | Evidence |
| --- | --- | --- |
| [E06R](E06R.md) | Pass against the original E06 criteria | The coherent replacement explicitly includes design capacity of 100,000 tonnes per year, the not-yet-operating state, and a scenario projecting 1,000,000 tonnes over 20 years. It does not present simulation as achieved operation |
| [C06R](C06R.md) | Pass in the Chinese synchronization check | The replacement retains “尚未开始运行,” annual design capacity of 10万吨, and projected cumulative processing of 100万吨 over 20 years. It limits the conclusion to the supplied material |

There were seven English attempts and one additional Chinese check. The [retry snapshot](revision.md) and [Chinese check input](chinese-check.md) preserve the exact instructions. The retry reuses the same materials, so it does not test generalization to a new input.

## Execution and review conditions

- Each executor received only its filled prompt, instructions to use the given material and write the final answer to a specified file, and a request to avoid self-scoring. It did not receive the evaluation criteria, other cases, or earlier outputs.
- Execution used fresh sub-agent contexts in the default model environment of this Codex session. Platform instructions remained active. An exact API model identifier, sampling configuration, and random seed were not fixed.
- These trials use the task prompts alone. They do not test long conversations, general writing preferences retained across turns, Skill installation, or the full Skill workflow.
- No web search, real data analysis, external citation verification, or publication submission was performed. All source records and numerical study materials are fictional.
- Root review checked actual completion, factual boundaries, quantities, and scope against the saved criteria. A separate model-agent reviewer in the same default environment reviewed E01–E06 and E06R independently. No human author or domain expert has scored these outputs.
- Raw final answers are retained without editing. Diagnostic length is reported as a usability observation and was not added as a retrospective failure condition.

E01–E05 translate Chinese cases H01, H02, H03, R07, and R08 from [the preceding Chinese run](../2026-11-10/README.md). E06 adds a new input about design capacity and simulated cumulative output. Differences between Chinese and English responses cannot be interpreted as measured language effects from single attempts in this setup.

## Text fingerprints

The initial trials used the English README from commit `95e2417`. Its SHA-256, with line endings normalized to LF, whitespace at the end of the file removed, and one final newline appended, was `d9c857ece9b3604e444ca5e45ff2b498a04c0f4ce1f2e84a8906afe9fb19caea`. E06R uses the revised task saved in [revision.md](revision.md). Inputs and outputs use the same normalization.

<details>
<summary>Input and output SHA-256 fingerprints</summary>

```text
E01
  input  51694e92fb2a9bd44a8b526134790558a66ac4dec0041d28d3e420fa72318ff7
  output c85cb1bbfdde51fe323c21061d84f6f0321835e9164e4d42abe3a8197a715c4e

E02
  input  fa47375c21f300d193960b29e946540f95893a323b3707e614a43939d2b79afb
  output 91bed15ee2eff077590992093d76768b6920985dd38d27b25edca91ab280876d

E03
  input  b0112920a7d306f4cbb5805d37443994ba0b313bc0d98e9b3a6ad2cf73cf3b7a
  output 8728b583ad25f5e97e22563eff752e25545c4664a0577c2fe3c8d65a38bff2df

E04
  input  57ae6a5dc22e50b94f610880121c4792f63a63f47571d8b9f6fa85b2e6d25383
  output e2351be6f76ff77f19f4b991ea7bb66c991b7c9015c04762c9d4545945977dec

E05
  input  b2ef84cd4850da2c5f5b9cbf4ebb16d572eaa774cb7985f0c7c5c5495e02bbe9
  output 5806de52431c82cbb2a274ae561f87f7d58c838905e1d7df9c8700ef69dc550a

E06
  input  ac0d382ccb0040e01740730bac0dd5c3f81dc674e7e56ae39af7cad3c274acdd
  output 1cf48d004b6968c14ee738469becda1bfc08069c4bd11aab90d4a1b7a72c3326

E06R
  input  dbd4171b608e4dd7b30c396aa07fea3fb210c6632848692934a2c8721b82e668
  output 3ff51fab257494286bf742af1c50ee4e5d57141fe1bc5e7a0f71b67c37f6c540

C06R
  input  656e4757d570c00f0ac0255d1b322704cc08e24a91747f67077fbeb21b4f1a3e
  output 8de1d3a5cafd4c9eb1b6c69d00ef522432d538099a4c91cafd2c9a54694ad7bd
```

</details>

## Limits and next checks

These small examples show what happened for the supplied inputs. They do not estimate an error rate or establish performance across models, journals, fields, or complete manuscripts. Structural diagnosis remains verbose, and the retry has only been run once. The Chinese synchronization check is likewise a single case.

Further checks should include independent real-author review, repeated attempts, and new materials that were not used to refine the prompts. The existing English homepage figure remains a translation of a Chinese editing example; it is separate from the direct English responses recorded here.
