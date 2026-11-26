# LaTeX 通用模板、高校学位论文骨架与自带模板适配规程

本文件规范 4 号工位 `export_manuscript.py` 如何生成与适配 LaTeX 文档（所有规则对应 [`templates/template_registry.json`](../templates/template_registry.json) 与 [`verified-latex-templates.md`](./verified-latex-templates.md) 中核实过的一手上游来源）。

---

## 一、 三种使用场景与命令选择

1. **无需额外宏包，直接可编译单篇论文（`article` / `ctexart` / `ieee` / `elsarticle`）**：
   ```bash
   # 中文通用核心期刊小论文（CTeX + GB/T 7714）
   python scripts/export_manuscript.py --workspace ./paper_workspace --tex-template ctexart

   # IEEE 英文双栏会议/期刊
   python scripts/export_manuscript.py --workspace ./paper_workspace --tex-template ieee --authors "A. Author, B. Author"

   # Elsevier 期刊预印本
   python scripts/export_manuscript.py --workspace ./paper_workspace --tex-template elsarticle
   ```
2. **国标中文多章大论文（`ctexbook` + `gbt7714`）及清华/北大/上交/中科大学位论文结构对接**：
   ```bash
   # 通用 GB/T 7713.1 多章大论文（独立可编译主文件 + chapters/*.tex + refs.bib）
   python scripts/export_manuscript.py --workspace ./paper_workspace --tex-template ctexbook --out-tex ./paper_workspace/06_submission/main.tex

   # 对接清华大学 thuthesis（生成 data/chap*.tex + ref/refs.bib，须配合官网 thuthesis 宏包编译）
   python scripts/export_manuscript.py --workspace ./paper_workspace --tex-template thuthesis --out-tex ./paper_workspace/06_submission/thuthesis-main.tex

   # 对接北京大学 pkuthss（生成 chap/chap*.tex + thesis.bib + \parencite 引用）
   python scripts/export_manuscript.py --workspace ./paper_workspace --tex-template pkuthss --out-tex ./paper_workspace/06_submission/thesis.tex
   ```
   同样支持 `--tex-template sjtuthesis`（生成 `contents/*.tex`）与 `--tex-template ustcthesis`（生成 `chapters/*.tex`）。
3. **任意院校/期刊官网自带模板适配（BYO Template）**：
   先只读扫描用户自带模板目录或主 `.tex` 文件，探测 `\documentclass`、章节层级（`\chapter` vs `\section`）和引用习惯（`\cite` / `\parencite` / `\supercite`）：
   ```bash
   python scripts/export_manuscript.py --inspect-tex ./my_school_template
   python scripts/export_manuscript.py --workspace ./paper_workspace --template-tex ./my_school_template/main.tex --out-tex ./paper_workspace/06_submission/adapted.tex
   ```
   **绝不覆盖用户原模板目录内的 `.cls`、封面或盲审宏包配置**。

---

## 二、 字体与插图防坑提示

- 中文模板（`ctexart`、`ctexbook`、`thuthesis`、`pkuthss`、`sjtuthesis`、`ustcthesis`）统一要求使用 **XeLaTeX**（或 LuaLaTeX）与 UTF-8 编码。
- 在 Word `.docx` 中嵌入图片时，优先引用 `.png` 或 `.jpg` 位图；若源图为 `.svg`，系统未安装光栅化转换时仅写入规范来源定位文字，绝不生成损坏图像包装。
