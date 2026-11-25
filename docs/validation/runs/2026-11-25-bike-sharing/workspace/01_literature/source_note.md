# 来源与读取范围

UCI 日表区分两类用户的租车次数，将周末和节假日合为非工作日，可以据此分别比较注册用户、临时用户和系统整体的日均用量。[@fanaee2013bike] 数据集介绍论文据摘要使用共享单车日志和外部背景知识标注事件。[@fanaee2014event] Gebhart 和 Noland 在另一项华盛顿研究中将逐小时天气与用车记录相连，摘要报告低温、降雨及高湿度条件下，用车可能性较低、行程时间较短。[@gebhart2014weather] 本文的两个年度及两类用户的工作日差额均需以 UCI 日表计算。

| 来源 | 实际读取位置 | 可支持的用途 |
| --- | --- | --- |
| Fanaee-T，2013，数据集 | [UCI 数据页](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset) 的变量说明、文件清单、引用及许可 | 日与小时文件的区别、工作日定义和计数口径。统计日数以实际读取的日表为准。 |
| Fanaee-T 与 Gama，2014，配套研究 | [出版社题录和摘要](https://link.springer.com/article/10.1007/s13748-013-0040-3) | 共享单车日志用于事件标注。在线发表于 2013 年，卷期年份为 2014 年。 |
| Gebhart 与 Noland，2014，华盛顿研究 | [出版社摘要](https://link.springer.com/article/10.1007/s11116-014-9540-7) | 小时尺度用车和天气的关联。将其用于本研究时，仍需日表分析才能判断两组间的天气差异。 |

## 检索与筛选

范围为 2010—2026 年。正向概念为华盛顿共享单车、注册与临时用户、工作日与非工作日、日租车次数。另以天气、季节和用车量检索替代解释。以下两式供文献库复查，实际脚本使用的纯关键词见运行命令。

- `"Capital Bikeshare" AND (registered OR casual) AND (weekday OR weekend OR holiday OR workingday) AND (trips OR ridership)`
- `("Capital Bikeshare" OR "Washington DC bikeshare") AND (weather OR season) AND (trips OR ridership)`

纳入原始数据及其介绍论文，以及直接使用华盛顿共享单车记录考察日历或天气条件的实证研究。脚本去重后共得两条，均出自反向检索。一条地域为波士顿，另一条以骑行安全为主题，均已排除。三项入选来源均经定向查找和 DOI 核验取得。两篇论文引用限于摘要所述，逐日分组数据由后续分析提供。

开放接口的四次组合查询中，仅 OpenAlex 反向检索成功。OpenAlex 正向检索返回 `NET_ERR:URLError`，Crossref 的两次关键词检索均返回 `HTTP_429`。脚本未报告需要密钥。另用浏览工具访问 DataCite 记录时未取得页面；数据集 DOI 已由 OpenAlex 及 UCI 页交叉核对。文章 DOI 的 Crossref 定点请求均成功。三条 DOI 验证输出都只含题录，账本中的更深读取层级分别来自实际打开的数据说明和出版社摘要。搜索覆盖有限，无法据此判断类似日类型比较在文献中的普遍程度。
