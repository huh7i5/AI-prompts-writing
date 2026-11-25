#!/usr/bin/env python3
"""Zero-dependency manuscript exporter & compiler (.docx + .tex) for Station 04.

Assembles ordered Markdown chapter drafts, resolves [@ref_id] citations against
02_literature_ledger.json / verified_refs.bib, and compiles:
  1) A valid Microsoft Word (.docx) package built purely with Python stdlib zipfile + OpenXML
     (supports headings, bold/italic spans, bullet lists, Markdown tables, and References).
  2) A clean XeLaTeX/LaTeX (.tex) source document with bibliography entries.

Optionally delegates to `pandoc` when `--prefer-pandoc` is passed and pandoc is installed.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CITE_KEY_REGEX = re.compile(r"\[@([A-Za-z0-9_:-]+)\]")
INLINE_TOKEN_REGEX = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")
CJK_REGEX = re.compile(r"[\u4e00-\u9fff]")

CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>
"""

ROOT_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

DOC_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
"""

STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="SimSun"/>
        <w:sz w:val="22"/>
        <w:szCs w:val="22"/>
      </w:rPr>
    </w:rPrDefault>
    <w:pPrDefault>
      <w:pPr>
        <w:spacing w:after="120" w:line="276" w:lineRule="auto"/>
      </w:pPr>
    </w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:jc w:val="center"/><w:spacing w:before="120" w:after="240"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="36"/><w:szCs w:val="36"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:keepNext/><w:spacing w:before="180" w:after="100"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:keepNext/><w:spacing w:before="140" w:after="80"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>
  </w:style>
</w:styles>
"""


def load_reference_catalog(lit_ledger_path: Path | None, bib_path: Path | None) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    if lit_ledger_path and lit_ledger_path.exists():
        data = json.loads(lit_ledger_path.read_text(encoding="utf-8"))
        for entry in data.get("entries") or []:
            rid = entry.get("ref_id")
            if rid:
                catalog[rid] = {
                    "ref_id": rid,
                    "authors": ", ".join(entry.get("authors") or ["Unknown"]),
                    "year": str(entry.get("year") or "n.d."),
                    "title": entry.get("title") or "",
                    "venue": entry.get("venue") or "",
                    "doi": entry.get("doi") or "",
                    "url": entry.get("url") or "",
                }
    if bib_path and bib_path.exists():
        bib_txt = bib_path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"@\w+\s*\{\s*([^,\s]+)\s*,([\s\S]*?)\n\}", bib_txt):
            rid = m.group(1).strip()
            if rid in catalog:
                continue
            body = m.group(2)
            fields: dict[str, str] = {}
            for fm in re.finditer(r"(\w+)\s*=\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", body):
                fields[fm.group(1).lower()] = fm.group(2).replace("{", "").replace("}", "").strip()
            catalog[rid] = {
                "ref_id": rid,
                "authors": fields.get("author", "Unknown").replace(" and ", ", "),
                "year": fields.get("year", "n.d."),
                "title": fields.get("title", ""),
                "venue": fields.get("journal", fields.get("booktitle", "")),
                "doi": fields.get("doi", ""),
                "url": fields.get("url", ""),
            }
    return catalog


def format_reference_line(num: int, ref: dict[str, Any]) -> str:
    parts = [f"[{num}] {ref['authors']} ({ref['year']}). {ref['title']}."]
    if ref.get("venue"):
        parts.append(f"{ref['venue']}.")
    if ref.get("doi"):
        parts.append(f"https://doi.org/{ref['doi']}")
    elif ref.get("url"):
        parts.append(ref["url"])
    return " ".join(p for p in parts if p)


def resolve_citations(markdown_text: str, catalog: dict[str, dict[str, Any]]) -> tuple[str, list[str], list[str]]:
    order: list[str] = []
    orphan_keys: list[str] = []

    def _repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in catalog:
            if key not in orphan_keys:
                orphan_keys.append(key)
            return f"[UNVERIFIED:{key}]"
        if key not in order:
            order.append(key)
        idx = order.index(key) + 1
        return f"[{idx}]"

    resolved = CITE_KEY_REGEX.sub(_repl, markdown_text)
    ref_lines = [format_reference_line(i, catalog[k]) for i, k in enumerate(order, start=1)]
    return resolved, ref_lines, orphan_keys


def _ooxml_runs(text: str) -> str:
    out: list[str] = []
    pos = 0
    for m in INLINE_TOKEN_REGEX.finditer(text):
        if m.start() > pos:
            plain = text[pos : m.start()]
            out.append(f'<w:r><w:t xml:space="preserve">{xml_escape(plain)}</w:t></w:r>')
        tok = m.group(0)
        if tok.startswith("**") and tok.endswith("**"):
            inner = tok[2:-2]
            out.append(f'<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{xml_escape(inner)}</w:t></w:r>')
        elif tok.startswith("*") and tok.endswith("*"):
            inner = tok[1:-1]
            out.append(f'<w:r><w:rPr><w:i/></w:rPr><w:t xml:space="preserve">{xml_escape(inner)}</w:t></w:r>')
        elif tok.startswith("`") and tok.endswith("`"):
            inner = tok[1:-1]
            out.append(
                '<w:r><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/></w:rPr>'
                f'<w:t xml:space="preserve">{xml_escape(inner)}</w:t></w:r>'
            )
        pos = m.end()
    if pos < len(text):
        out.append(f'<w:r><w:t xml:space="preserve">{xml_escape(text[pos:])}</w:t></w:r>')
    if not out:
        return '<w:r><w:t xml:space="preserve"></w:t></w:r>'
    return "".join(out)


def _ooxml_paragraph(text: str, style: str | None = None, left_indent: int = 0) -> str:
    ppr_parts: list[str] = []
    if style:
        ppr_parts.append(f'<w:pStyle w:val="{style}"/>')
    if left_indent > 0:
        ppr_parts.append(f'<w:ind w:left="{left_indent}"/>')
    ppr = f"<w:pPr>{''.join(ppr_parts)}</w:pPr>" if ppr_parts else ""
    return f"<w:p>{ppr}{_ooxml_runs(text)}</w:p>"


def _ooxml_table(rows: list[list[str]]) -> str:
    tbl_props = (
        "<w:tblPr>"
        '<w:tblW w:w="9000" w:type="dxa"/>'
        "<w:tblBorders>"
        '<w:top w:val="single" w:sz="6" w:space="0" w:color="4B5563"/>'
        '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="4B5563"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="D1D5DB"/>'
        "</w:tblBorders>"
        "</w:tblPr>"
    )
    tr_xml: list[str] = []
    for r_idx, row in enumerate(rows):
        cells_xml: list[str] = []
        for cell in row:
            txt = f"**{cell}**" if r_idx == 0 and not cell.startswith("**") else cell
            cells_xml.append(
                "<w:tc><w:tcPr><w:tcMar><w:top w:w=\"80\" w:type=\"dxa\"/><w:bottom w:w=\"80\" w:type=\"dxa\"/>"
                "<w:left w:w=\"100\" w:type=\"dxa\"/><w:right w:w=\"100\" w:type=\"dxa\"/></w:tcMar></w:tcPr>"
                f"{_ooxml_paragraph(txt)}</w:tc>"
            )
        tr_xml.append(f"<w:tr>{''.join(cells_xml)}</w:tr>")
    return f"<w:tbl>{tbl_props}{''.join(tr_xml)}</w:tbl>"


def markdown_to_docx_xml(md_text: str, title: str, authors: str) -> str:
    body_elems: list[str] = []
    if title:
        body_elems.append(_ooxml_paragraph(title, style="Title"))
    if authors:
        body_elems.append(_ooxml_paragraph(authors))

    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i].rstrip()
        stripped = raw.strip()
        if not stripped or stripped == "---":
            i += 1
            continue

        # Markdown table
        if stripped.startswith("|") and "|" in stripped[1:]:
            table_rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row_str = lines[i].strip().strip("|")
                cells = [c.strip() for c in row_str.split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c or "-") for c in cells):
                    table_rows.append(cells)
                i += 1
            if table_rows:
                body_elems.append(_ooxml_table(table_rows))
            continue

        # Headings
        hm = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if hm:
            lvl = len(hm.group(1))
            style = f"Heading{lvl}"
            body_elems.append(_ooxml_paragraph(hm.group(2).strip(), style=style))
            i += 1
            continue

        # Bullet / numbered list
        bm = re.match(r"^(?:[-*+]|\d+\.)\s+(.+)$", stripped)
        if bm:
            prefix = "• " if stripped[0] in "-*+" else stripped.split()[0] + " "
            body_elems.append(_ooxml_paragraph(prefix + bm.group(1).strip(), left_indent=360))
            i += 1
            continue

        # Image / SVG link fallback note
        im = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", stripped)
        if im:
            body_elems.append(_ooxml_paragraph(f"[Figure: {im.group(1)} — source: {im.group(2)}]"))
            i += 1
            continue

        # Blockquote
        if stripped.startswith(">"):
            body_elems.append(_ooxml_paragraph(stripped.lstrip("> ").strip(), left_indent=360))
            i += 1
            continue

        # Regular paragraph (merge consecutive plain lines)
        para_lines = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt or nxt == "---" or nxt.startswith(("#", "|", ">", "-", "*", "+")) or re.match(r"^\d+\.\s+", nxt):
                break
            para_lines.append(nxt)
            i += 1
        body_elems.append(_ooxml_paragraph(" ".join(para_lines)))

    sect_pr = '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>'
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(body_elems)}{sect_pr}</w:body>"
        "</w:document>"
    )


def write_stdlib_docx(md_text: str, title: str, authors: str, out_docx: Path) -> None:
    out_docx.parent.mkdir(parents=True, exist_ok=True)
    doc_xml = markdown_to_docx_xml(md_text, title=title, authors=authors)
    with zipfile.ZipFile(out_docx, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES_XML.encode("utf-8"))
        zf.writestr("_rels/.rels", ROOT_RELS_XML.encode("utf-8"))
        zf.writestr("word/_rels/document.xml.rels", DOC_RELS_XML.encode("utf-8"))
        zf.writestr("word/styles.xml", STYLES_XML.encode("utf-8"))
        zf.writestr("word/document.xml", doc_xml.encode("utf-8"))


def _tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    out = []
    for ch in text:
        out.append(replacements.get(ch, ch))
    s = "".join(out)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", s)
    s = re.sub(r"\*([^*]+)\*", r"\\textit{\1}", s)
    return s


def markdown_to_latex(md_text: str, title: str, authors: str, ref_lines: list[str]) -> str:
    has_cjk = bool(CJK_REGEX.search(md_text + title + authors))
    doc_cls = r"\documentclass[11pt,a4paper]{ctexart}" if has_cjk else r"\documentclass[11pt,a4paper]{article}"
    preamble = [
        doc_cls,
        r"\usepackage[margin=2.5cm]{geometry}",
        r"\usepackage{hyperref}",
        r"\usepackage{booktabs}",
        r"\title{" + _tex_escape(title or "Manuscript Draft") + "}",
        r"\author{" + _tex_escape(authors or "[Authors]") + "}",
        r"\date{}",
        r"\begin{document}",
        r"\maketitle",
        "",
    ]
    body: list[str] = []
    for raw in md_text.splitlines():
        st = raw.strip()
        if not st or st == "---":
            body.append("")
            continue
        hm = re.match(r"^(#{1,3})\s+(.+)$", st)
        if hm:
            cmd = {1: "section", 2: "subsection", 3: "subsubsection"}[len(hm.group(1))]
            body.append(rf"\{cmd}{{{_tex_escape(hm.group(2).strip())}}}")
            continue
        body.append(_tex_escape(st))

    if ref_lines:
        body.extend(["", r"\begin{thebibliography}{99}"])
        for idx, rline in enumerate(ref_lines, start=1):
            body.append(rf"\bibitem{{ref{idx}}} {_tex_escape(rline)}")
        body.append(r"\end{thebibliography}")

    body.append(r"\end{document}")
    return "\n".join(preamble + body) + "\n"


def _collect_inputs(workspace: Path | None, explicit_inputs: list[str]) -> list[Path]:
    if explicit_inputs:
        return [Path(p) for p in explicit_inputs]
    assert workspace is not None
    drafts_dir = workspace / "04_drafts"
    if not drafts_dir.exists():
        return []
    order_hints = ("abstract", "intro", "related", "method", "result", "discuss", "conclu")
    files = sorted(drafts_dir.glob("*.md"))

    def _sort_key(p: Path) -> tuple[int, str]:
        low = p.stem.lower()
        for idx, hint in enumerate(order_hints):
            if hint in low:
                return (idx, low)
        return (99, low)

    return sorted(files, key=_sort_key)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile paper Markdown drafts + verified citations into .docx and .tex.")
    parser.add_argument("--workspace", default="", help="Optional paper workspace directory (auto-discovers 04_drafts & ledgers).")
    parser.add_argument("--inputs", nargs="*", default=[], help="Explicit ordered Markdown draft files.")
    parser.add_argument("--title", default="", help="Manuscript title (defaults to 00_project_spec.json title_working).")
    parser.add_argument("--authors", default="", help="Author line.")
    parser.add_argument("--lit-ledger", default="", help="Optional 02_literature_ledger.json path.")
    parser.add_argument("--bib", default="", help="Optional verified_refs.bib path.")
    parser.add_argument("--out-docx", default="", help="Output .docx file path.")
    parser.add_argument("--out-tex", default="", help="Output .tex file path.")
    parser.add_argument("--out-md", default="", help="Optional assembled Markdown path with resolved references.")
    parser.add_argument("--prefer-pandoc", action="store_true", help="Use pandoc for .docx if installed.")
    args = parser.parse_args()

    ws = Path(args.workspace).resolve() if args.workspace else None
    input_files = _collect_inputs(ws, args.inputs)
    if not input_files:
        raise SystemExit("No input Markdown files found. Pass --inputs or populate <workspace>/04_drafts/*.md.")

    title = args.title
    if not title and ws and (ws / "00_project_spec.json").exists():
        spec = json.loads((ws / "00_project_spec.json").read_text(encoding="utf-8"))
        title = spec.get("title_working") or ""

    lit_path = Path(args.lit_ledger) if args.lit_ledger else (ws / "01_literature" / "02_literature_ledger.json" if ws else None)
    bib_path = Path(args.bib) if args.bib else (ws / "01_literature" / "verified_refs.bib" if ws else None)
    catalog = load_reference_catalog(lit_path, bib_path)

    raw_sections = [p.read_text(encoding="utf-8").strip() for p in input_files]
    assembled_raw = "\n\n".join(s for s in raw_sections if s)

    resolved_body, ref_lines, orphan_keys = resolve_citations(assembled_raw, catalog)
    assembled_with_refs = resolved_body
    if ref_lines and not re.search(r"(?m)^#{1,2}\s+(?:References|参考文献)", resolved_body):
        assembled_with_refs += "\n\n## References\n\n" + "\n\n".join(ref_lines) + "\n"

    out_docx = Path(args.out_docx) if args.out_docx else (ws / "06_submission" / "manuscript.docx" if ws else None)
    out_tex = Path(args.out_tex) if args.out_tex else (ws / "06_submission" / "manuscript.tex" if ws else None)
    out_md = Path(args.out_md) if args.out_md else (ws / "06_submission" / "manuscript_assembled.md" if ws else None)

    if out_md:
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(assembled_with_refs, encoding="utf-8")

    docx_backend = None
    if out_docx:
        if args.prefer_pandoc and shutil.which("pandoc"):
            tmp_md = out_docx.with_suffix(".tmp.md")
            tmp_md.parent.mkdir(parents=True, exist_ok=True)
            tmp_md.write_text(assembled_with_refs, encoding="utf-8")
            proc = subprocess.run([shutil.which("pandoc"), str(tmp_md), "-o", str(out_docx)], check=False)
            tmp_md.unlink(missing_ok=True)
            docx_backend = "pandoc" if proc.returncode == 0 else "stdlib-ooxml"
            if docx_backend == "stdlib-ooxml":
                write_stdlib_docx(assembled_with_refs, title=title, authors=args.authors, out_docx=out_docx)
        else:
            write_stdlib_docx(assembled_with_refs, title=title, authors=args.authors, out_docx=out_docx)
            docx_backend = "stdlib-ooxml"

    if out_tex:
        out_tex.parent.mkdir(parents=True, exist_ok=True)
        tex_src = markdown_to_latex(resolved_body, title=title, authors=args.authors, ref_lines=ref_lines)
        out_tex.write_text(tex_src, encoding="utf-8")

    summary = {
        "inputs_compiled": [p.name for p in input_files],
        "resolved_citations_count": len(ref_lines),
        "unverified_orphan_citations": orphan_keys,
        "docx_output": str(out_docx) if out_docx else None,
        "docx_backend": docx_backend,
        "tex_output": str(out_tex) if out_tex else None,
        "status": "WARN_ORPHAN_CITATIONS" if orphan_keys else "PASS",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
