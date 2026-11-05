# 生命周期插图生成记录
# 生命周期插图生成记录

日期：2026-11-05。使用内置 image_gen 重新生成；图片用于项目说明，不是实验结果，也不代表任何期刊认可。

本次按反馈改为像素手稿风格，并去掉顶部总标题。图中保留十个阶段、项目作用、返修回路和作者责任说明。没有使用外部 API，也没有用代码滤镜替代绘制。

生成后的目视复核：像素方块、阶梯线条和有限配色清楚；顶部没有总标题；十个阶段编号各出现一次；主流程为 1→2→3→4→5→6→7→8→9→10；9→6、9→4 的虚线回路和 10→1 的外圈回路均可见。图中没有真实实验数据、比例承诺、出版方标志或水印。

```text
Use case: scientific-educational / infographic-diagram.
Asset type: a single original landscape README illustration for AI-prompts-writing.

Edit the provided lifecycle illustration into a pixel-sketch / pixel-art manuscript style. Use crisp square pixel clusters, stepped pixel edges, limited palette, sparse dithering, and pixelated hand-drawn notebook details. It should feel like a careful academic sketchnote made in pixel art, not watercolor, not smooth vector art, not calligraphy, not 3D, and not a cute cartoon.

Remove the large top title completely. There must be no title or heading at the top and no empty title banner. Start the composition directly with the numbered lifecycle stages.

Keep exactly these ten numbered Chinese stage labels, each number exactly once:
"1 选题"
"2 文献"
"3 方案"
"4 研究记录与分析"
"5 初稿"
"6 修改"
"7 自查"
"8 投稿"
"9 反馈与返修"
"10 接收后与发表后"

Arrange them as a clean two-row serpentine workflow: 1→2→3→4→5 across the top; then 5→6→7→8→9→10 along the bottom from right to left. Use clear pixel arrows that never cross or cover labels. Keep a visible dashed pixel return arrow from 9 back to 6 and another from 9 back to 4, plus a light outer return from 10 back to 1.

In the middle, use a small understated pixel label "AI-prompts-writing" and below it "梳理问题 · 组织证据 · 起草改稿 · 辅助核对". This is a modest annotation, not a title or banner.

At the bottom, keep two small readable lines:
"贯穿全程：记录与版本 · 来源与证据 · 伦理与作者确认"
"作者负责研究执行、证据核实与最终决定"

Use a clean off-white or pale gray paper background with a very subtle pixel grid, dark navy/charcoal pixel outlines, muted teal and rust-red accents, limited colors, generous whitespace, and strong readability when displayed at about 900 px wide. Use small pixel icons: question notes, papers and magnifier, plan notebook, records and analysis, manuscript, edit marks, checklist, envelope, reviewer comments, archived folder. Do not add any extra text, logos, publisher marks, percentages, fake data, charts, watermarks, or the word Nature. Preserve the information and flow but redraw the visual style and composition.
```
日期：2026-11-05。使用内置 image_gen 生成；下列提示词为原文。图片用于项目说明，不是实验结果，也不代表任何期刊认可。

生成过程：首次请求因服务繁忙失败，未产出图片；使用同一提示词重试后成功。未使用外部 API，也未对图中文字或内容做代码编辑。

生成后的目视复核：十个阶段及编号、中文标签、项目名和作者职责文字与下列要求一致。实线显示参考顺序，虚线表示返修；从反馈回到研究记录与分析的虚线中段被中央说明带遮住，需结合正文理解，不能据此把研究看成自动、单向的生产过程。

```text
Use case: scientific-educational / infographic-diagram.
Asset type: a single original landscape hand-drawn scientific editorial illustration for the public README of AI-prompts-writing. This is an explanatory workflow, not research results.
Primary request: show the research and academic-paper-writing lifecycle and exactly where a text prompt library assists. Render as an elegant high-impact science journal editorial sketch: restrained fine graphite and ink lines, pale teal and muted ochre watercolor washes, warm nearly-white paper background, ample whitespace, consistent precise typography. Mature academic art direction, small observational sketches of real research tools and manuscripts; no cartoon characters, no cute faces, no generic corporate flowchart cards, no gradients, no 3-D.
Composition: wide landscape 16:10, preferably around 2400 x 1500 pixels, with generous margins. Ten clearly numbered stages on one continuous clockwise path. A readable two-row serpentine arrangement is recommended: stages 1,2,3,4,5 across the upper row left to right; stages 10,9,8,7,6 across the lower row left to right. Connect 1→2→3→4→5, then turn downward at the right from 5→6, then 6→7→8→9→10 right to left. Allow enough vertical room between rows for a simple central project annotation. Every connection has a small clear arrowhead, no accidental reverse sequence.
Stage text, render verbatim as large legible Chinese labels, with an unobtrusive hand-drawn object beside each:
"1 选题" (pencil and short question notes);
"2 文献" (papers and magnifying glass);
"3 方案" (open research plan notebook);
"4 研究记录与分析" (carefully layered records and a calculator, no invented numerical data; can break label after 研究记录);
"5 初稿" (manuscript sheets);
"6 修改" (manuscript with visible editorial pencil marks);
"7 自查" (magnifying glass over checklist);
"8 投稿" (document and envelope);
"9 反馈与返修" (annotated reviewer letter);
"10 接收后与发表后" (proof sheets and archived folder; can break label after 接收后).
Centre annotation: project name exactly "AI-prompts-writing". Beneath it, exactly "梳理问题 · 组织证据 · 起草改稿 · 辅助核对". This central annotation describes help offered across the path, not automatic execution or guaranteed acceptance.
Iteration: add two thin dashed curved return arrows from stage 9, one back to stage 6 and one back to stage 4, routed neatly without covering text. Add a light curved return connection from stage 10 to stage 1 along the left outer margin, indicating new questions after publication. Solid sequential flow and dashed revision loops must be visually distinguishable.
Footer, verbatim, in readable smaller Chinese: "贯穿全程：记录与版本 · 来源与证据 · 伦理与作者确认".
A final concise line, verbatim: "作者负责研究执行、证据核实与最终决定".
Only these texts plus title "研究与论文写作生命周期". No additional tiny text, fake handwriting, fabricated scientific values, invented data plots, guarantees, percentage claims, logos, publisher mastheads or watermarks. In particular do not print Nature anywhere. Preserve every stage number exactly once. The figure must remain readable at GitHub README width of 900 pixels. Chinese typography should be crisp and natural, while illustrations and connecting lines have the gentle irregularity of careful hand sketching.
```
