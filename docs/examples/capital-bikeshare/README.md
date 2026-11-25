# 华盛顿共享单车研究样稿

**[阅读完整论文](paper.md)**

工作日租得更多，这些租借集中在哪几小时？这篇文章使用同一系统连续两年的日表和小时表，按月份、用户类别和时段展开比较。正文含两幅数据图和三张表。

## 数据从哪里来

原始资料为 Hadi Fanaee-T (2013), *Bike Sharing*, UCI Machine Learning Repository。日表沿用仓库已保存的原始字节。小时表从同一份 UCI 压缩包中提取，再用 gzip 无损封装。运行脚本时会核验两个原始文件的 SHA-256。数据按 CC BY 4.0 许可发布，图表和统计量由本次分析生成。[UCI 及数据许可](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset) · [原始日表](../../validation/runs/2026-11-25-bike-sharing/workspace/02_evidence/day.csv) · [小时表](hour.csv.gz)

## 怎样复算

在仓库中打开本目录，依次执行以下命令，只需要 Python 3 标准库。

```sh
python day_analysis.py --check
python hour_analysis.py --check
python check_paper.py
```

前两条重算日表和小时表，与保存的结果对照。第三条独立读取这两个原始文件，核对论文三张表共 13 行的标签、分母和差值。它检查 39 个差值，并核对表 1 的三对天数和表 2 的五个天数。[日层面结果](day-results.json) · [小时层面结果](hour-results.json)

已附图可直接阅读。自行重画时需安装 Matplotlib，小时图还需系统中有微软雅黑、思源黑体等脚本支持的中文字体。

```sh
python day_analysis.py --check --plot
python plot_hour.py
```

## 文章如何核对

本次在仓库公开版 [`3459e7f`](https://github.com/huh7i5/AI-prompts-writing/tree/3459e7fbd4a7d16edfd2abf7085d2775d92d1577) 的基础上扩展首次试跑。文献、分析、写作与审查由 Codex 分工完成，写作同时参考本机的 `paper-writing` Skill。仓库原有脚本分别检查了文献记录、主张与证据、写作和审查说明。另有一名独立的审稿 Agent 从原始记录复算，核对了月度实例、用户占比、小时峰值和 731、725、655 天三个不同样本的口径。它指出初稿把计数单位写成了观察单位，也指出窗口外合计较低不能推广到窗口外的每一个小时。正文已据此修订。[证据索引](claims.json) · [来源和阅读范围](sources.md) · [初次试跑的短稿与对照实验](../../validation/runs/2026-11-25-bike-sharing/README.md)

这是一次公开数据的探索性再分析。仓库中的检查记录供读者自行核对；本稿尚未经期刊同行评审。
