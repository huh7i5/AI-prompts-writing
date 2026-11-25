# 研究引用了哪些资料

运营记录告诉我们在哪一天、什么时间租出了车。想知道这些行程的用途，还需要问卷里的回答。这里把各项来源与它们能回答的问题列在一起。

| 来源 | 本文使用的证据 | 实际查阅位置 |
| --- | --- | --- |
| Fanaee-T（2013），*Bike Sharing* | 两张表各按日和小时计数。日类型取自 `workingday`，总租借次数包括临时和注册两部分。样本大小以下载文件逐行清点。 | [UCI 数据字典与文件清单](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset) |
| Fanaee-T 与 Gama（2014），*Event labeling combining ensemble detectors and background knowledge* | 数据集的配套论文介绍了如何借助使用日志和背景信息标注事件。文章于 2013 年在线发表，2014 年编入第 2 卷。 | [出版社题录与摘要](https://link.springer.com/article/10.1007/s13748-013-0040-3) |
| Buck 等（2013），*Are Bikeshare Users Different from Regular Cyclists?* | 摘要报告，现场访问的一日票用户比线上受访的年度会员更常为休闲而骑行。两种调查分别接触哪些人，关系到结论可以推广到谁。 | [期刊摘要](https://journals.sagepub.com/doi/10.3141/2387-13) |
| LDA Consulting（2012），*Capital Bikeshare 2011 Member Survey* | 5,464 名会员完成线上调查。受访者最近一次租车中有 56% 出于非工作目的。一个人回答一次，这个比例不能直接换算成全部租借次数中的占比。 | [运营方报告，PDF 第 2、4 页](https://d21xlh2maitm24.cloudfront.net/wdc/Capital_Bikeshare_2011_Survey_Executive_Summary.pdf?mtime=20161206135934) |
| Younes 等（2020），*Comparing the Temporal Determinants of Dockless Scooter-share and Station-based Bike-share in Washington, D.C.* | 作者将 2018 年 12 月至 2019 年 6 月的小时记录按类别展开。有桩单车会员在高峰时段用量集中，非会员周末用量高于工作日。行程须在特区界内出发或结束。 | [作者机构存档，正文第 311 页及图 2](https://geog.umd.edu/sites/geog.umd.edu/files/pubs/1-s2.0-S0965856419311553-main_0.pdf) |
| Gebhart 与 Noland（2014），*The impact of weather conditions on bikeshare trips in Washington, DC* | 据摘要，逐小时数据中的低温、降雨和高湿与较低的用车可能性及较短的行程时长有关。天气是否解释本文的分组差值，需要检查本文自己的数据。 | [出版社摘要](https://link.springer.com/article/10.1007/s11116-014-9540-7) |
| Capital Bikeshare，*System Data* | 运营方按所购票种区分会员和临时用户，并记载了 2011 年秋短期票的变化。租车所持票种和出行目的需要分别解释。 | [运营方的 Member Type 与 Member Surveys 栏](https://capitalbikeshare.com/system-data) |

2026 年 11 月 25 日，我们用仓库自带的检索脚本在 Crossref 和 OpenAlex 查询会员类别与小时用量，以及天气、调查和骑行目的。关键词查询去重后返回 8 条，Crossref 的第二条查询遇到网络错误。随后按来源追查了 UCI 的数据说明、出版者摘要、马里兰大学公开的论文和运营方调查。最后对选用的 5 个 DOI 逐项核验；运营方网页和调查报告直接按原文核对。本清单供查阅这篇文章的出处。[来源账本与检索式](sources.json) · [DOI 核验结果](references-check.json)
