# 数据来源与复算记录

Hadi Fanaee-T 于 2013 年向 UCI Machine Learning Repository 提交了 *Bike Sharing*。数据来自美国华盛顿特区地区的 Capital Bikeshare 系统。本分析使用公开的按日汇总表。每天一行，表中没有个人标识符。[UCI 数据集与变量说明](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset) · [数据集 DOI](https://doi.org/10.24432/C5W894)

UCI 标明数据采用 CC BY 4.0 许可。本目录保留了原始 `day.csv` 的全部字节。分组均值和差值由本次分析生成。归属为 Fanaee-T, H. (2013). *Bike Sharing* [Dataset]. UCI Machine Learning Repository。官方压缩包内的 `Readme.txt` 另请使用者在发表时引用 Hadi Fanaee-T 与 João Gama 的 *Event labeling combining ensemble detectors and background knowledge*。[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [原始论文 DOI](https://doi.org/10.1007/s13748-013-0040-3)

## 固定输入

2026-11-25 通过 Python 标准库 `urllib.request.urlopen` 获取 UCI 的 ZIP 压缩包，使用 `zipfile.ZipFile.read("day.csv")` 提取原始字节。压缩包还含小时数据和说明文件。统计只读取 `day.csv`。[UCI 压缩包](https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip)

| 文件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| UCI ZIP 压缩包 | 279992 | `b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401` |
| 压缩包中的 `day.csv` | 57569 | `a6bcf826782d3c0fbfdcbeead17cd0884185a0dafe8ff10cd48a874ee7ba18be` |

## 字段与计算

| 字段 | 本次用途 |
| --- | --- |
| `dteday`、`yr` | 从实际日期 `dteday` 取公历年份；用 `yr` 交叉核验，0 表示 2011，1 表示 2012。 |
| `workingday`、`holiday` | 按数据集的 `workingday` 分组。1 为工作日，0 包括周末和节假日。逐日用公历星期和档案中的节假日标志复核编码。 |
| `casual`、`registered`、`cnt` | 分别为临时用户租用次数、注册用户租用次数和总租用次数。相同用户可以多次租车。 |

每一天在相应组内贡献一次观测。分组均值是相应列的租用总数除以该组观测天数，单位为次／日。两年合并时也使用该日型的全部天数作分母。差值按工作日均值减非工作日均值计算。脚本在求差前保留精确分数，输出 JSON 时转换为浮点数；整数分子及分母另存于 `rental_sums` 与 `n_days`。

## 本地核验

在本目录运行以下两条命令。第一条从固定输入生成 `results.json`，第二条重新读取原始数据并核对全部结果。两次运行均已在 Python 3.14.6 标准库环境完成。

```sh
python analysis.py
python analysis.py --check
```

| 主张或结果 | 原始来源与版本 | 处理步骤及输出定位 | 限制或偏离 | 待补记录 |
| --- | --- | --- | --- | --- |
| 覆盖两年内的完整 731 天 | 上列 `day.csv` 快照 | 逐日解析日期并与完整日历比对，见 `results.json` 的 `calendar` 和 `checks` | 2011-01-01 至 2012-12-31 内遗漏、重复、越界均为 0；未删行或插补 | 无 |
| 两年内，注册用户的工作日日均租用次数分别比非工作日高，临时用户分别较低 | 同一快照中的两个分量 | 六组分别计算天数、整数和、算术均值，再计算三组工作日减非工作日差值，见 `groups` 和 `contrasts` | 两个类别共用相同观察日；租用次数不能识别独立人数、出行目的或工作日的因果影响 | 无 |
| 两个分量的方向相反，合计的日型差值为正 | 同一快照的 `cnt` | 先核对每行 `cnt = casual + registered`，再按与分量相同的方法求总量均值和差值 | 未调整天气、季节或系统运营变化；解释范围限于该系统的观察期 | 无 |

另用 SQLite 内存表从原始 CSV 直接按年及日型执行 `COUNT(*)` 与 `AVG`，所得天数、均值和工作日减非工作日差值与 Python 计算在所报告精度下一致。上述描述性比较所需的记录均已齐备。个体层面的问题需要能够识别相应观察单位的资料。
