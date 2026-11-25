# 工位 01 运行命令

在本发布版仓库根目录执行。raw 中的搜索、两份 DOI 核验和门禁 JSON 均由对应脚本直接写出。重跑联网命令时，检索排序与接口可用性可能变化。

```powershell
python .agents/skills/ai-prompt-writing/scripts/pipeline_doctor.py diagnose --workspace docs/validation/runs/2026-11-25-bike-sharing/workspace
New-Item -ItemType Directory -Force 'docs/validation/runs/2026-11-25-bike-sharing/workspace/01_literature/raw' | Out-Null
python .agents/skills/paper-topic-literature/scripts/lit_search_verify.py search --query "Capital Bikeshare Washington registered casual weekday weekend ridership" --counter-query "Capital Bikeshare weather seasonal variation daily trip counts" --since 2010 --until 2026 --sources openalex,crossref --max-results 2 --out-ledger docs/validation/runs/2026-11-25-bike-sharing/workspace/01_literature/raw/search.json
python .agents/skills/paper-topic-literature/scripts/lit_search_verify.py verify --doi 10.24432/C5W894 10.1007/s13748-013-0040-3 --out-report docs/validation/runs/2026-11-25-bike-sharing/workspace/01_literature/raw/doi_verify.json
python .agents/skills/paper-topic-literature/scripts/lit_search_verify.py verify --doi 10.1007/s11116-014-9540-7 --out-report docs/validation/runs/2026-11-25-bike-sharing/workspace/01_literature/raw/weather_doi_verify.json
python .agents/skills/paper-topic-literature/scripts/lit_gate_check.py --draft docs/validation/runs/2026-11-25-bike-sharing/workspace/01_literature/source_note.md --mode related-work --ledger docs/validation/runs/2026-11-25-bike-sharing/workspace/01_literature/02_literature_ledger.json --json-out docs/validation/runs/2026-11-25-bike-sharing/workspace/01_literature/raw/literature_gate.json
```

首轮诊断时工作区尚未创建，回报 `FULL_SUITE_MODE`，同级四站均在。依据已有研究问题，进入 `paper-topic-literature`，依次读取该站说明、选题、检索及相关工作规程。搜索和首批 DOI 定点核验可独立执行。另在浏览工具打开 UCI 数据页、两篇期刊论文的出版社页面及天气论文的 Rutgers 题录，用于确认实际读取深度。原始检索结果含未入选题录；下游引用键取经筛选的 `02_literature_ledger.json`。
