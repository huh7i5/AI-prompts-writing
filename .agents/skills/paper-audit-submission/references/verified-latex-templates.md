# 已核验的 LaTeX 期刊与高校学位论文模板来源清单

本清单记录 `export_manuscript.py` 内置模板档案与自带模板探测（`--inspect-tex` / `--template-tex`）的**一手官方/开源出处**，所有 `\documentclass`、目录结构与引用宏命令均核对自原始项目代码或 CTAN 文档，绝不凭记忆编造，也不擅自复制第三方受限 `.cls` 或校徽商标资源。

---

## 一、 通用及国际期刊 / 会议模板（TeX Live / MiKTeX 发行版内置，可独立编译）

1. **中文通用论文 (`ctexart`) & 中文通用学位大论文 (`ctexbook` + `gbt7714`)**
   - **依据标准**：中国国家标准 **GB/T 7713.1-2006 / 2025**《学位论文编写规则》（前置部分 → 主体 `\chapter` 分章 → GB/T 7714 参考文献 → 附录 → 结尾致谢与科研成果）与 **GB/T 7714-2015**《信息与文献 参考文献著录规则》。
   - **上游来源**：CTAN `ctex` 宏包与 [`zepinglee/gbt7714-bibtex-style`](https://github.com/zepinglee/gbt7714-bibtex-style)（LPPL-1.3c）。
   - **典型命令**：`\documentclass[12pt,a4paper,openany]{ctexbook}` + `\usepackage{gbt7714}` + `\bibliographystyle{gbt7714-numerical}`。

2. **IEEE 会议与期刊 (`ieee`)**
   - **上游来源**：CTAN [`ieeetran`](https://ctan.org/pkg/ieeetran)（官方示例 `bare_conf.tex`、`bare_jrnl.tex`；LPPL）。
   - **关键约束**：基于 `article` 层级，**不支持 `\chapter`**，最高层级为 `\section`；支持 `conference` / `journal` / `technote` / `peerreview` 选项及 `IEEEkeywords` 环境。

3. **Elsevier 期刊 (`elsarticle`)**
   - **上游来源**：CTAN [`elsarticle`](https://ctan.org/pkg/elsarticle)（官方示例 `elsarticle-template-num.tex`、`elsarticle-template-harv.tex`；LPPL）。
   - **关键约束**：`\documentclass[preprint,12pt]{elsarticle}`（审稿常见 `review` / `1p` / `3p` / `5p`），前置摘要与关键词须放在 `\begin{frontmatter}...\end{frontmatter}` 内；最高正文层级为 `\section`。

4. **Springer Nature 期刊 (`sn-jnl`)**
   - **上游来源**：Springer Nature 官方作者支持 [`sn-article-template`](https://www.springernature.com/gp/authors/campaigns/latex-author-support)（`\documentclass[sn-mathphys-num]{sn-jnl}` 或 `sn-basic` / `iicol`）。
   - **使用方式**：因未随全部基础发行版默认预装，请先从 Springer Nature 官网下载 `sn-jnl.cls` 到本地目录，再配合 `--template-tex` 或 `--tex-template sn-jnl` 导出对应正文。

---

## 二、 国内代表高校学位论文模板适配档案（仅按官方结构生成章节与配置，须从官网/CTAN获取完整工程）

| 高校 | 上游权威仓库与 CTAN | 实查入口文件与选项 | 真实章节目录与参考文献规范 | 许可与商标注意 |
| :--- | :--- | :--- | :--- | :--- |
| **清华大学** (`thuthesis`) | [`tuna/thuthesis`](https://github.com/tuna/thuthesis) · [CTAN](https://ctan.org/pkg/thuthesis) | `\documentclass[degree=master]{thuthesis}` + `\input{thusetup}`（`thuthesis-example.tex`） | 章节放在 `data/chap01.tex`…，`data/abstract.tex`，参考文献 `\bibliography{ref/refs}` | **LPPL-1.3c**；`thu-fig-logo.pdf` 等校徽图形属清华大学注册商标，不得剥离或他用 |
| **北京大学** (`pkuthss`) | [`CasperVector/pkuthss`](https://github.com/CasperVector/pkuthss) · [CTAN](https://ctan.org/pkg/pkuthss) | `\documentclass[UTF8]{pkuthss}` + `\pkuthssinfo{...}`（`thesis.tex`） | 章节放在 `chap/chap1.tex`…（`\chapter{...}`），常用 `biblatex` (`caspervector` 或 `gb7714-2015`)，`\parencite` / `\supercite` | **LPPL-1.3** + Public Domain（示例） |
| **上海交通大学** (`sjtuthesis`) | [`sjtug/SJTUThesis`](https://github.com/sjtug/SJTUThesis) · [CTAN `sjtutex`](https://ctan.org/pkg/sjtutex) | `\documentclass[type=master]{sjtuthesis}` + `\input{setup}`（`main.tex`） | 章节放在 `contents/abstract.tex`、`contents/intro.tex`…，`\printbibliography[heading=bibintoc]` | **LPPL-1.3c + Apache-2.0**；校徽版权归上海交大 |
| **中国科学技术大学** (`ustcthesis`) | [`ustctug/ustcthesis`](https://github.com/ustctug/ustcthesis) | `\documentclass[degree=doctor]{ustcthesis}` + `\input{ustcsetup}`（`main.tex`） | 章节放在 `chapters/1-introduction.tex`…，内建 `\declarationofaiusage`（AI 工具使用声明），`\printbibliography` | **LPPL-1.3c** |

> **其他高校与期刊怎么办？**  
> 直接从你所在学校研究生院或目标期刊下载最新官方 LaTeX 压缩包到本地，运行：
> ```bash
> python scripts/export_manuscript.py --inspect-tex /path/to/your_school_template_dir
> python scripts/export_manuscript.py --workspace ./paper_workspace --template-tex /path/to/your_school_template_dir/main.tex --out-tex ./paper_workspace/06_submission/adapted_manuscript.tex
> ```
> 脚本会自动识别该模板的 `\documentclass`、是否使用 `\chapter`、引用宏命令（`\cite` / `\parencite` / `\supercite`）以及分文件 `\input`/`\include` 路径，在不改动学校原封面与盲审样式的前提下生成匹配正文章节。
