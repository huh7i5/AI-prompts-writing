#!/usr/bin/env python3
"""Zero-dependency manuscript exporter & template adapter (.docx + .tex) for Station 04.

Capabilities (Python 3 standard library only, zero required third-party packages):
  1) Valid Microsoft Word (.docx) OpenXML output with:
     - Embedded PNG/JPEG figures via stdlib pixel dimension parsing + <w:drawing>
       (pairs .svg links with sibling .png or optional PyMuPDF rasterization if available)
     - Academic three-line tables (top 1.5pt, header 0.75pt, bottom 1.5pt, no vertical rules)
     - Centered page footer numbering and optional thesis chapter page breaks
  2) Source-grounded LaTeX (.tex) output aligned with templates/template_registry.json:
     - Built-in standalone CTAN classes: ctexart, article, ctexbook (GB/T 7713.1 + gbt7714),
       ieee (IEEEtran), elsarticle (Elsevier)
     - Verified university multi-chapter adapters: thuthesis (Tsinghua), pkuthss (PKU),
       sjtuthesis (SJTU), ustcthesis (USTC), plus Springer Nature sn-jnl skeleton
     - Bring-Your-Own template support via --inspect-tex and --template-tex

Optionally delegates .docx generation to `pandoc` when `--prefer-pandoc` is passed.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SKILL_DIR = Path(__file__).resolve().parent.parent
REGISTRY_PATH = SKILL_DIR / "templates" / "template_registry.json"

CITE_KEY_REGEX = re.compile(r"\[@([A-Za-z0-9_:-]+)\]")
INLINE_TOKEN_REGEX = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")
CJK_REGEX = re.compile(r"[\u4e00-\u9fff]")

ROOT_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

FOOTER_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:p>
    <w:pPr><w:jc w:val="center"/></w:pPr>
    <w:fldSimple w:instr=" PAGE ">
      <w:r><w:t>1</w:t></w:r>
    </w:fldSimple>
  </w:p>
</w:ftr>
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
  <w:style w:type="paragraph" w:styleId="Caption">
    <w:name w:val="caption"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:jc w:val="center"/><w:spacing w:before="60" w:after="180"/></w:pPr>
    <w:rPr><w:i/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>
  </w:style>
</w:styles>
"""


def load_template_registry() -> dict[str, dict[str, Any]]:
    if not REGISTRY_PATH.exists():
        return {}
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return data.get("templates") or {}


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
                    "authors_bib": " and ".join(entry.get("authors") or ["Unknown"]),
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
            raw_author = fields.get("author", "Unknown")
            catalog[rid] = {
                "ref_id": rid,
                "authors": raw_author.replace(" and ", ", "),
                "authors_bib": raw_author,
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


def extract_citation_keys(markdown_text: str, catalog: dict[str, dict[str, Any]]) -> tuple[list[str], list[str]]:
    cited: list[str] = []
    orphans: list[str] = []
    for m in CITE_KEY_REGEX.finditer(markdown_text):
        key = m.group(1)
        if key not in catalog:
            if key not in orphans:
                orphans.append(key)
        elif key not in cited:
            cited.append(key)
    return cited, orphans


def render_bibtex_entries(keys: list[str], catalog: dict[str, dict[str, Any]]) -> str:
    blocks: list[str] = []
    for k in keys:
        ref = catalog.get(k)
        if not ref:
            continue
        lines = [
            f"@article{{{k},",
            f"  author  = {{{ref.get('authors_bib') or ref.get('authors') or 'Unknown'}}},",
            f"  title   = {{{ref.get('title') or 'Untitled'}}},",
            f"  journal = {{{ref.get('venue') or 'Preprint'}}},",
            f"  year    = {{{ref.get('year') or '2026'}}},",
        ]
        if ref.get("doi"):
            lines.append(f"  doi     = {{{ref['doi']}}},")
        if ref.get("url"):
            lines.append(f"  url     = {{{ref['url']}}},")
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def _read_image_size_px(img_path: Path) -> tuple[int, int, str] | None:
    """Read (width, height, ext) for PNG or JPEG purely via Python stdlib struct."""
    data = img_path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        if w > 0 and h > 0:
            return w, h, "png"
    if data[:2] == b"\xff\xd8":
        idx = 2
        while idx + 4 < len(data):
            if data[idx] != 0xFF:
                idx += 1
                continue
            marker = data[idx + 1]
            idx += 2
            if marker in (0xD8, 0xD9) or (0xD0 <= marker <= 0xD7):
                continue
            if idx + 2 > len(data):
                break
            seg_len = struct.unpack(">H", data[idx : idx + 2])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                if idx + 7 <= len(data):
                    h, w = struct.unpack(">HH", data[idx + 3 : idx + 7])
                    if w > 0 and h > 0:
                        return w, h, "jpeg"
                break
            idx += seg_len
    return None


def _resolve_image_candidate(img_ref: str, search_dirs: list[Path], raster_dir: Path | None = None) -> tuple[Path | None, str]:
    raw_path = Path(img_ref)
    candidates: list[Path] = []
    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        for d in search_dirs:
            candidates.append((d / raw_path).resolve())

    found = next((p for p in candidates if p.exists() and p.is_file()), None)
    if not found:
        return None, f"missing:{img_ref}"

    suf = found.suffix.lower()
    if suf in (".png", ".jpg", ".jpeg"):
        return found, "bitmap"

    if suf == ".svg":
        for alt_ext in (".png", ".jpg", ".jpeg"):
            alt = found.with_suffix(alt_ext)
            if alt.exists() and alt.is_file():
                return alt, "paired-svg-bitmap"
        if raster_dir is not None:
            try:
                import fitz  # type: ignore

                svg_doc = fitz.open(str(found))
                page = svg_doc[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
                out_png = raster_dir / f"{found.stem}_raster.png"
                pix.save(str(out_png))
                return out_png, "fitz-rasterized"
            except Exception:
                pass
        return found, "vector-svg-only"

    return found, "unsupported-format"


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


def _ooxml_paragraph(
    text: str,
    style: str | None = None,
    left_indent: int = 0,
    align: str | None = None,
    page_break_before: bool = False,
) -> str:
    ppr_parts: list[str] = []
    if style:
        ppr_parts.append(f'<w:pStyle w:val="{style}"/>')
    if page_break_before:
        ppr_parts.append("<w:pageBreakBefore/>")
    if align:
        ppr_parts.append(f'<w:jc w:val="{align}"/>')
    if left_indent > 0:
        ppr_parts.append(f'<w:ind w:left="{left_indent}"/>')
    ppr = f"<w:pPr>{''.join(ppr_parts)}</w:pPr>" if ppr_parts else ""
    return f"<w:p>{ppr}{_ooxml_runs(text)}</w:p>"


def _ooxml_image_paragraph(rel_id: str, img_id: int, w_px: int, h_px: int, filename: str) -> str:
    max_emu = 5303520  # ~5.8 inches (fits A4 content width cleanly)
    raw_cx = int(w_px * 9525)
    raw_cy = int(h_px * 9525)
    if raw_cx > max_emu and raw_cx > 0:
        scale = max_emu / raw_cx
        cx = max_emu
        cy = max(1, int(raw_cy * scale))
    else:
        cx = max(9525, raw_cx)
        cy = max(9525, raw_cy)
    esc_name = xml_escape(filename)
    return (
        "<w:p><w:pPr><w:jc w:val=\"center\"/><w:keepNext/></w:pPr><w:r><w:drawing>"
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx}" cy="{cy}"/>'
        f'<wp:docPr id="{img_id}" name="{esc_name}"/>'
        "<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect=\"1\"/></wp:cNvGraphicFramePr>"
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        "<pic:pic>"
        f'<pic:nvPicPr><pic:cNvPr id="{img_id}" name="{esc_name}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        "<pic:spPr>"
        f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        "</pic:spPr>"
        "</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>"
    )


def _ooxml_table(rows: list[list[str]]) -> str:
    """Render an academic three-line table (top 1.5pt, header 0.75pt, bottom 1.5pt, no verticals)."""
    tbl_props = (
        "<w:tblPr>"
        '<w:tblW w:w="9000" w:type="dxa"/>'
        "<w:tblBorders>"
        '<w:top w:val="single" w:sz="12" w:space="0" w:color="1F2937"/>'
        '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="1F2937"/>'
        '<w:left w:val="none"/><w:right w:val="none"/>'
        '<w:insideH w:val="none"/><w:insideV w:val="none"/>'
        "</w:tblBorders>"
        "</w:tblPr>"
    )
    tr_xml: list[str] = []
    for r_idx, row in enumerate(rows):
        cells_xml: list[str] = []
        hdr_border = (
            '<w:tcBorders><w:bottom w:val="single" w:sz="6" w:space="0" w:color="374151"/></w:tcBorders>'
            if r_idx == 0
            else ""
        )
        for cell in row:
            txt = f"**{cell}**" if r_idx == 0 and not cell.startswith("**") else cell
            cells_xml.append(
                "<w:tc><w:tcPr>"
                f"{hdr_border}"
                '<w:tcMar><w:top w:w="80" w:type="dxa"/><w:bottom w:w="80" w:type="dxa"/>'
                '<w:left w:w="100" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tcMar></w:tcPr>'
                f"{_ooxml_paragraph(txt)}</w:tc>"
            )
        tr_xml.append(f"<w:tr>{''.join(cells_xml)}</w:tr>")
    return f"<w:tbl>{tbl_props}{''.join(tr_xml)}</w:tbl>"


def _content_types_xml(image_exts: set[str]) -> str:
    ext_defaults = [
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
    ]
    if "png" in image_exts:
        ext_defaults.append('<Default Extension="png" ContentType="image/png"/>')
    if "jpeg" in image_exts or "jpg" in image_exts:
        ext_defaults.append('<Default Extension="jpeg" ContentType="image/jpeg"/>')
        ext_defaults.append('<Default Extension="jpg" ContentType="image/jpeg"/>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        + "".join(ext_defaults)
        + '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        + '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        + '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
        + "</Types>"
    )


def _doc_rels_xml(image_rels: list[tuple[str, str]]) -> str:
    rels = [
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>',
        '<Relationship Id="rIdFooter1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>',
    ]
    for rid, target in image_rels:
        rels.append(
            f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{target}"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(rels)
        + "</Relationships>"
    )


def write_stdlib_docx(
    md_text: str,
    title: str,
    authors: str,
    out_docx: Path,
    search_dirs: list[Path] | None = None,
    page_break_on_h1: bool = False,
) -> dict[str, Any]:
    out_docx.parent.mkdir(parents=True, exist_ok=True)
    dirs = search_dirs or [Path.cwd()]
    body_elems: list[str] = []
    media_entries: list[tuple[str, bytes]] = []
    image_rels: list[tuple[str, str]] = []
    image_exts: set[str] = set()
    embedded_images: list[str] = []

    if title:
        body_elems.append(_ooxml_paragraph(title, style="Title"))
    if authors:
        body_elems.append(_ooxml_paragraph(authors, align="center"))

    h1_seen = 0
    with tempfile.TemporaryDirectory() as tmp_raster:
        raster_dir = Path(tmp_raster)
        lines = md_text.splitlines()
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if not stripped or stripped == "---":
                i += 1
                continue

            if stripped.startswith("|") and "|" in stripped[1:]:
                table_rows: list[list[str]] = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                    if not all(re.fullmatch(r":?-{2,}:?", c or "-") for c in cells):
                        table_rows.append(cells)
                    i += 1
                if table_rows:
                    body_elems.append(_ooxml_table(table_rows))
                continue

            hm = re.match(r"^(#{1,3})\s+(.+)$", stripped)
            if hm:
                lvl = len(hm.group(1))
                do_break = page_break_on_h1 and lvl == 1 and h1_seen > 0
                if lvl == 1:
                    h1_seen += 1
                body_elems.append(_ooxml_paragraph(hm.group(2).strip(), style=f"Heading{lvl}", page_break_before=do_break))
                i += 1
                continue

            bm = re.match(r"^(?:[-*+]|\d+\.)\s+(.+)$", stripped)
            if bm:
                prefix = "• " if stripped[0] in "-*+" else stripped.split()[0] + " "
                body_elems.append(_ooxml_paragraph(prefix + bm.group(1).strip(), left_indent=360))
                i += 1
                continue

            im = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", stripped)
            if im:
                cap_text, img_ref = im.group(1).strip(), im.group(2).strip()
                resolved_img, img_kind = _resolve_image_candidate(img_ref, dirs, raster_dir=raster_dir)
                size_info = _read_image_size_px(resolved_img) if resolved_img and resolved_img.exists() and img_kind in ("bitmap", "paired-svg-bitmap", "fitz-rasterized") else None
                if resolved_img and size_info:
                    w_px, h_px, ext = size_info
                    img_id = len(media_entries) + 1
                    rel_id = f"rIdImg{img_id}"
                    media_name = f"media/image{img_id}.{ext}"
                    media_entries.append((f"word/{media_name}", resolved_img.read_bytes()))
                    image_rels.append((rel_id, media_name))
                    image_exts.add(ext)
                    embedded_images.append(resolved_img.name)
                    body_elems.append(_ooxml_image_paragraph(rel_id, img_id, w_px, h_px, resolved_img.name))
                    if cap_text:
                        body_elems.append(_ooxml_paragraph(cap_text, style="Caption"))
                else:
                    body_elems.append(_ooxml_paragraph(f"[Figure: {cap_text or 'Figure'} — source: {img_ref} ({img_kind})]", style="Caption"))
                i += 1
                continue

            if stripped.startswith(">"):
                body_elems.append(_ooxml_paragraph(stripped.lstrip("> ").strip(), left_indent=360))
                i += 1
                continue

            para_lines = [stripped]
            i += 1
            while i < len(lines):
                nxt = lines[i].strip()
                if not nxt or nxt == "---" or nxt.startswith(("#", "|", ">", "-", "*", "+", "![")) or re.match(r"^\d+\.\s+", nxt):
                    break
                para_lines.append(nxt)
                i += 1
            body_elems.append(_ooxml_paragraph(" ".join(para_lines)))

    sect_pr = (
        "<w:sectPr>"
        '<w:footerReference w:type="default" r:id="rIdFooter1"/>'
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>'
        "</w:sectPr>"
    )
    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f"<w:body>{''.join(body_elems)}{sect_pr}</w:body>"
        "</w:document>"
    )

    with zipfile.ZipFile(out_docx, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types_xml(image_exts).encode("utf-8"))
        zf.writestr("_rels/.rels", ROOT_RELS_XML.encode("utf-8"))
        zf.writestr("word/_rels/document.xml.rels", _doc_rels_xml(image_rels).encode("utf-8"))
        zf.writestr("word/styles.xml", STYLES_XML.encode("utf-8"))
        zf.writestr("word/footer1.xml", FOOTER_XML.encode("utf-8"))
        zf.writestr("word/document.xml", doc_xml.encode("utf-8"))
        for arc_name, payload in media_entries:
            zf.writestr(arc_name, payload)

    return {"embedded_images": embedded_images}


def _tex_escape_plain(text: str) -> str:
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
    return "".join(replacements.get(ch, ch) for ch in text)


def _tex_escape_inline(text: str, cite_cmd: str | None = None, catalog: dict[str, Any] | None = None) -> str:
    """Convert inline Markdown (**bold**, *italic*, `code`, [@key]) cleanly into LaTeX."""
    out: list[str] = []
    token_re = re.compile(r"(\[@[A-Za-z0-9_:-]+\]|\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")
    pos = 0
    for m in token_re.finditer(text):
        if m.start() > pos:
            out.append(_tex_escape_plain(text[pos : m.start()]))
        tok = m.group(0)
        if tok.startswith("[@") and tok.endswith("]"):
            key = tok[2:-1]
            if cite_cmd and catalog is not None:
                out.append(rf"\{cite_cmd}{{{key}}}" if key in catalog else rf"[UNVERIFIED:{_tex_escape_plain(key)}]")
            else:
                out.append(_tex_escape_plain(tok))
        elif tok.startswith("**") and tok.endswith("**"):
            out.append(r"\textbf{" + _tex_escape_inline(tok[2:-2], cite_cmd, catalog) + "}")
        elif tok.startswith("*") and tok.endswith("*"):
            out.append(r"\textit{" + _tex_escape_inline(tok[1:-1], cite_cmd, catalog) + "}")
        elif tok.startswith("`") and tok.endswith("`"):
            out.append(r"\texttt{" + _tex_escape_plain(tok[1:-1]) + "}")
        pos = m.end()
    if pos < len(text):
        out.append(_tex_escape_plain(text[pos:]))
    return "".join(out)


def markdown_body_to_latex(
    md_text: str,
    top_section_cmd: str = "section",
    cite_cmd: str | None = None,
    catalog: dict[str, Any] | None = None,
    search_dirs: list[Path] | None = None,
    tex_dir: Path | None = None,
) -> str:
    level_map = (
        {1: "chapter", 2: "section", 3: "subsection"}
        if top_section_cmd == "chapter"
        else {1: "section", 2: "subsection", 3: "subsubsection"}
    )
    body: list[str] = []
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        st = lines[i].strip()
        if not st or st == "---":
            body.append("")
            i += 1
            continue

        if st.startswith("|") and "|" in st[1:]:
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c or "-") for c in cells):
                    rows.append(cells)
                i += 1
            if rows:
                cols = max(len(r) for r in rows)
                col_spec = "l" + "c" * (cols - 1)
                body.extend([r"\begin{table}[htbp]", r"\centering", rf"\begin{{tabular}}{{{col_spec}}}", r"\toprule"])
                for r_idx, row in enumerate(rows):
                    padded = row + [""] * (cols - len(row))
                    rendered_cells = [_tex_escape_inline(c, cite_cmd, catalog) for c in padded]
                    if r_idx == 0:
                        rendered_cells = [rf"\textbf{{{rc}}}" for rc in rendered_cells]
                    body.append(" & ".join(rendered_cells) + r" \\")
                    if r_idx == 0 and len(rows) > 1:
                        body.append(r"\midrule")
                body.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
            continue

        hm = re.match(r"^(#{1,3})\s+(.+)$", st)
        if hm:
            cmd = level_map[len(hm.group(1))]
            body.append(rf"\{cmd}{{{_tex_escape_inline(hm.group(2).strip(), cite_cmd, catalog)}}}")
            i += 1
            continue

        im = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", st)
        if im:
            cap_txt, img_ref = im.group(1).strip(), im.group(2).strip()
            resolved_img, _ = _resolve_image_candidate(img_ref, search_dirs or [Path.cwd()])
            fig_path = img_ref.replace("\\", "/")
            if resolved_img and tex_dir:
                try:
                    fig_path = str(resolved_img.relative_to(tex_dir.resolve())).replace("\\", "/")
                except ValueError:
                    fig_path = resolved_img.name
            body.extend([r"\begin{figure}[htbp]", r"\centering"])
            if fig_path.lower().endswith(".svg"):
                body.append(rf"% NOTE: SVG vector graphic '{fig_path}' may require pdf/png conversion or svg package")
            body.append(rf"\includegraphics[width=0.82\linewidth]{{{fig_path}}}")
            if cap_txt:
                body.append(rf"\caption{{{_tex_escape_inline(cap_txt, cite_cmd, catalog)}}}")
            body.extend([r"\end{figure}", ""])
            i += 1
            continue

        if re.match(r"^[-*+]\s+", st):
            body.append(r"\begin{itemize}")
            while i < len(lines) and re.match(r"^[-*+]\s+", lines[i].strip()):
                item = re.sub(r"^[-*+]\s+", "", lines[i].strip())
                body.append(r"  \item " + _tex_escape_inline(item, cite_cmd, catalog))
                i += 1
            body.extend([r"\end{itemize}", ""])
            continue

        if re.match(r"^\d+\.\s+", st):
            body.append(r"\begin{enumerate}")
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                item = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                body.append(r"  \item " + _tex_escape_inline(item, cite_cmd, catalog))
                i += 1
            body.extend([r"\end{enumerate}", ""])
            continue

        if st.startswith(">"):
            body.append(r"\begin{quote}")
            while i < len(lines) and lines[i].strip().startswith(">"):
                body.append("  " + _tex_escape_inline(lines[i].strip().lstrip("> ").strip(), cite_cmd, catalog))
                i += 1
            body.extend([r"\end{quote}", ""])
            continue

        body.append(_tex_escape_inline(st, cite_cmd, catalog))
        i += 1

    return "\n".join(body)


def markdown_to_latex(md_text: str, title: str, authors: str, ref_lines: list[str]) -> str:
    """Backwards-compatible standalone single-file LaTeX compiler."""
    has_cjk = bool(CJK_REGEX.search(md_text + title + authors))
    doc_cls = r"\documentclass[11pt,a4paper]{ctexart}" if has_cjk else r"\documentclass[11pt,a4paper]{article}"
    preamble = [
        doc_cls,
        r"\usepackage[margin=2.5cm]{geometry}",
        r"\usepackage{graphicx}",
        r"\usepackage{hyperref}",
        r"\usepackage{booktabs}",
        r"\title{" + _tex_escape_plain(title or "Manuscript Draft") + "}",
        r"\author{" + _tex_escape_plain(authors or "[Authors]") + "}",
        r"\date{}",
        r"\begin{document}",
        r"\maketitle",
        "",
    ]
    body_tex = markdown_body_to_latex(md_text, top_section_cmd="section")
    tail: list[str] = []
    if ref_lines:
        tail.extend(["", r"\begin{thebibliography}{99}"])
        for idx, rline in enumerate(ref_lines, start=1):
            tail.append(rf"\bibitem{{ref{idx}}} {_tex_escape_plain(rline)}")
        tail.append(r"\end{thebibliography}")
    tail.append(r"\end{document}")
    return "\n".join(preamble) + "\n" + body_tex + "\n" + "\n".join(tail) + "\n"


def inspect_tex_target(path_input: Path) -> dict[str, Any]:
    """Read-only inspector for user-supplied school/journal .tex or directory templates."""
    target = path_input.resolve()
    if not target.exists():
        raise FileNotFoundError(f"TeX template target not found: {target}")

    tex_files: list[Path] = []
    if target.is_file():
        tex_files = [target]
        root_dir = target.parent
    else:
        root_dir = target
        tex_files = sorted(target.rglob("*.tex"))

    combined = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in tex_files[:30])
    doc_match = re.search(r"\\documentclass(?:\[([^\]]*)\])?\{([^}]+)\}", combined)
    doc_opts = doc_match.group(1) if doc_match and doc_match.group(1) else ""
    doc_class = doc_match.group(2).strip() if doc_match else "unknown"

    uses_chapter = bool(re.search(r"\\chapter\{", combined)) or any(
        k in doc_class.lower() for k in ("book", "thesis", "pkuthss", "report")
    )
    if re.search(r"\\supercite\{", combined):
        cite_cmd = "supercite"
    elif re.search(r"\\parencite\{", combined):
        cite_cmd = "parencite"
    else:
        cite_cmd = "cite"

    bib_engine = "biblatex" if re.search(r"\\usepackage[^}]*\{biblatex\}|\\printbibliography", combined) else (
        "gbt7714" if "gbt7714" in combined else "bibtex"
    )
    includes = re.findall(r"\\(?:input|include)\{([^}]+)\}", combined)
    local_cls = sorted(p.name for p in root_dir.rglob("*.cls"))

    return {
        "target": str(target),
        "documentclass": doc_class,
        "documentclass_options": doc_opts,
        "top_section_cmd": "chapter" if uses_chapter else "section",
        "detected_citation_cmd": cite_cmd,
        "detected_bib_engine": bib_engine,
        "detected_includes": includes[:25],
        "local_cls_files": local_cls,
        "has_body_markers": "% AI_PROMPTS_BODY_START" in combined,
    }


def export_using_registry_template(
    template_name: str,
    input_files: list[Path],
    raw_sections: list[str],
    title: str,
    authors: str,
    catalog: dict[str, dict[str, Any]],
    out_tex: Path,
    search_dirs: list[Path],
) -> dict[str, Any]:
    registry = load_template_registry()
    if template_name not in registry:
        raise ValueError(f"Unknown --tex-template '{template_name}'. Allowed: {sorted(registry.keys())}")
    meta = registry[template_name]
    out_tex.parent.mkdir(parents=True, exist_ok=True)

    full_raw = "\n\n".join(s for s in raw_sections if s)
    cited_keys, orphan_keys = extract_citation_keys(full_raw, catalog)
    cite_cmd = meta.get("citation_cmd", "cite")
    top_cmd = meta.get("top_section_cmd", "section")
    generated_files: list[str] = [str(out_tex)]

    bib_rel = "ref/refs.bib" if template_name == "thuthesis" else ("thesis.bib" if template_name == "pkuthss" else "refs.bib")
    bib_out = out_tex.parent / bib_rel
    bib_out.parent.mkdir(parents=True, exist_ok=True)
    bib_out.write_text(render_bibtex_entries(cited_keys, catalog), encoding="utf-8")
    generated_files.append(str(bib_out))

    chapter_dir_name = meta.get("chapter_dir")
    if chapter_dir_name:
        chap_dir = out_tex.parent / chapter_dir_name
        chap_dir.mkdir(parents=True, exist_ok=True)
        include_lines: list[str] = []
        for idx, (src_file, sec_md) in enumerate(zip(input_files, raw_sections), start=1):
            chap_stem = f"chap{idx:02d}_{re.sub(r'[^A-Za-z0-9_-]+', '_', src_file.stem)}"
            if template_name == "thuthesis":
                chap_stem = f"chap{idx:02d}"
            elif template_name == "pkuthss":
                chap_stem = f"chap{idx}"
            chap_path = chap_dir / f"{chap_stem}.tex"
            chap_tex = markdown_body_to_latex(
                sec_md,
                top_section_cmd=top_cmd,
                cite_cmd=cite_cmd,
                catalog=catalog,
                search_dirs=search_dirs,
                tex_dir=out_tex.parent,
            )
            chap_path.write_text(chap_tex + "\n", encoding="utf-8")
            generated_files.append(str(chap_path))
            include_cmd = "include" if template_name == "ustcthesis" else "input"
            include_lines.append(rf"\{include_cmd}{{{chapter_dir_name}/{chap_stem}}}")

        header_comment = (
            f"% !TEX encoding = UTF-8\n"
            f"% !TEX program = xelatex\n"
            f"% Profile: {template_name} | Source: {meta.get('source')} ({meta.get('url')})\n"
            f"% License: {meta.get('license')}\n"
        )
        if template_name == "ctexbook":
            main_lines = [
                header_comment,
                meta["documentclass"],
                r"\usepackage{graphicx}",
                r"\usepackage{booktabs}",
                r"\usepackage{hyperref}",
                r"\usepackage{gbt7714}",
                rf"\title{{{_tex_escape_plain(title or '学位论文草稿')}}}",
                rf"\author{{{_tex_escape_plain(authors or '[作者]')}}}",
                r"\date{}",
                r"\begin{document}",
                r"\frontmatter",
                r"\maketitle",
                r"\tableofcontents",
                r"\mainmatter",
                *include_lines,
                r"\backmatter",
                r"\bibliographystyle{gbt7714-numerical}",
                r"\bibliography{refs}",
                r"\end{document}",
            ]
        elif template_name == "pkuthss":
            main_lines = [
                header_comment,
                meta["documentclass"],
                r"\usepackage[backend=biber,style=gb7714-2015,utf8]{biblatex}",
                rf"\addbibresource{{{bib_rel}}}",
                r"\usepackage{graphicx,booktabs}",
                rf"\pkuthssinfo{{ctitle={{{_tex_escape_plain(title or '论文题目')}}}, cauthor={{{_tex_escape_plain(authors or '作者')}}}}}",
                r"\begin{document}",
                r"\frontmatter",
                r"\tableofcontents",
                r"\mainmatter",
                *include_lines,
                r"\backmatter",
                r"\printbibliography",
                r"\end{document}",
            ]
        else:
            setup_line = rf"\input{{{meta['setup_file'].replace('.tex', '')}}}" if meta.get("setup_file") else "% Setup file from upstream template"
            bib_tail = r"\bibliography{ref/refs}" if template_name == "thuthesis" else r"\printbibliography"
            ai_note = rf"% {meta['ai_usage_macro']}" if meta.get("ai_usage_macro") else ""
            main_lines = [
                header_comment,
                meta["documentclass"],
                f"% Upstream wrapper skeleton (install {template_name}.cls via CTAN/TeX Live or official GitHub repo)",
                setup_line,
                r"\begin{document}",
                r"\maketitle",
                ai_note,
                r"\frontmatter",
                r"\tableofcontents",
                r"\mainmatter",
                *include_lines,
                r"\backmatter",
                bib_tail,
                r"\end{document}",
            ]
        out_tex.write_text("\n".join(line for line in main_lines if line is not None) + "\n", encoding="utf-8")
    else:
        body_tex = markdown_body_to_latex(
            full_raw,
            top_section_cmd=top_cmd,
            cite_cmd=cite_cmd,
            catalog=catalog,
            search_dirs=search_dirs,
            tex_dir=out_tex.parent,
        )
        esc_title = _tex_escape_plain(title or "Manuscript Title")
        esc_auth = _tex_escape_plain(authors or "[Authors]")
        if template_name == "ieee":
            lines = [
                meta["documentclass"],
                r"\usepackage{cite,graphicx,booktabs,amsmath}",
                r"\begin{document}",
                rf"\title{{{esc_title}}}",
                rf"\author{{\IEEEauthorblockN{{{esc_auth}}}}}",
                r"\maketitle",
                body_tex,
                r"\bibliographystyle{IEEEtran}",
                r"\bibliography{refs}",
                r"\end{document}",
            ]
        elif template_name == "elsarticle":
            lines = [
                meta["documentclass"],
                r"\usepackage{graphicx,booktabs}",
                r"\begin{document}",
                r"\begin{frontmatter}",
                rf"\title{{{esc_title}}}",
                rf"\author{{{esc_auth}}}",
                r"\end{frontmatter}",
                body_tex,
                r"\bibliographystyle{elsarticle-num}",
                r"\bibliography{refs}",
                r"\end{document}",
            ]
        elif template_name == "sn-jnl":
            lines = [
                f"% Requires sn-jnl.cls from {meta.get('url')}",
                meta["documentclass"],
                r"\usepackage{graphicx,booktabs,amsmath}",
                r"\begin{document}",
                rf"\title{{{esc_title}}}",
                rf"\author{{{esc_auth}}}",
                r"\maketitle",
                body_tex,
                r"\bibliography{refs}",
                r"\end{document}",
            ]
        else:
            lines = [
                meta["documentclass"],
                r"\usepackage[margin=2.5cm]{geometry}",
                r"\usepackage{graphicx,booktabs,hyperref}",
                rf"\title{{{esc_title}}}",
                rf"\author{{{esc_auth}}}",
                r"\date{}",
                r"\begin{document}",
                r"\maketitle",
                body_tex,
                r"\bibliographystyle{gbt7714-numerical}" if template_name == "ctexart" else r"\bibliographystyle{plain}",
                r"\bibliography{refs}",
                r"\end{document}",
            ]
        out_tex.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "tex_template": template_name,
        "upstream_source": meta.get("source"),
        "upstream_url": meta.get("url"),
        "license": meta.get("license"),
        "requires_external_cls": meta.get("requires_external_cls", False),
        "cited_keys": cited_keys,
        "orphan_keys": orphan_keys,
        "generated_files": generated_files,
    }


def export_byo_template(
    template_tex: Path,
    raw_md: str,
    catalog: dict[str, dict[str, Any]],
    out_tex: Path,
    search_dirs: list[Path],
) -> dict[str, Any]:
    """Adapt manuscript body to an existing user-provided .tex template without mutating the source."""
    info = inspect_tex_target(template_tex)
    tpl_file = template_tex if template_tex.is_file() else (template_tex / "main.tex")
    if not tpl_file.exists():
        tex_candidates = sorted(template_tex.glob("*.tex"))
        if not tex_candidates:
            raise FileNotFoundError(f"No entry .tex file found in {template_tex}")
        tpl_file = tex_candidates[0]

    tpl_src = tpl_file.read_text(encoding="utf-8", errors="replace")
    cited_keys, orphan_keys = extract_citation_keys(raw_md, catalog)
    body_tex = markdown_body_to_latex(
        raw_md,
        top_section_cmd=info["top_section_cmd"],
        cite_cmd=info["detected_citation_cmd"],
        catalog=catalog,
        search_dirs=search_dirs,
        tex_dir=out_tex.parent,
    )

    marker_re = re.compile(r"(%\s*AI_PROMPTS_BODY_START[\s\S]*?%\s*AI_PROMPTS_BODY_END)")
    if marker_re.search(tpl_src):
        patched = marker_re.sub(
            lambda _: "% AI_PROMPTS_BODY_START\n" + body_tex + "\n% AI_PROMPTS_BODY_END",
            tpl_src,
            count=1,
        )
        injection_mode = "marker-block"
    elif r"\end{document}" in tpl_src:
        idx = tpl_src.rfind(r"\end{document}")
        patched = tpl_src[:idx] + "\n% --- Inserted Draft Body ---\n" + body_tex + "\n\n" + tpl_src[idx:]
        injection_mode = "before-end-document"
    else:
        patched = tpl_src + "\n\n" + body_tex + "\n"
        injection_mode = "appended"

    out_tex.parent.mkdir(parents=True, exist_ok=True)
    out_tex.write_text(patched, encoding="utf-8")
    bib_out = out_tex.parent / "refs_generated.bib"
    bib_out.write_text(render_bibtex_entries(cited_keys, catalog), encoding="utf-8")
    return {
        "byo_template": str(tpl_file),
        "detected": info,
        "injection_mode": injection_mode,
        "cited_keys": cited_keys,
        "orphan_keys": orphan_keys,
        "generated_files": [str(out_tex), str(bib_out)],
    }


def _collect_inputs(workspace: Path | None, explicit_inputs: list[str]) -> list[Path]:
    if explicit_inputs:
        return [Path(p) for p in explicit_inputs]
    assert workspace is not None
    drafts_dir = workspace / "04_drafts"
    if not drafts_dir.exists():
        return []
    order_hints = ("abstract", "intro", "ch1", "related", "ch2", "method", "ch3", "result", "ch4", "discuss", "conclu", "ch5")
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
    parser.add_argument("--workspace", default="", help="Optional paper workspace directory.")
    parser.add_argument("--inputs", nargs="*", default=[], help="Explicit ordered Markdown draft files.")
    parser.add_argument("--title", default="", help="Manuscript title.")
    parser.add_argument("--authors", default="", help="Author line.")
    parser.add_argument("--lit-ledger", default="", help="Optional 02_literature_ledger.json path.")
    parser.add_argument("--bib", default="", help="Optional verified_refs.bib path.")
    parser.add_argument("--out-docx", default="", help="Output .docx file path.")
    parser.add_argument("--out-tex", default="", help="Output .tex file path.")
    parser.add_argument("--out-md", default="", help="Optional assembled Markdown path.")
    parser.add_argument("--tex-template", default="", help="Verified template profile (ctexart, article, ctexbook, ieee, elsarticle, sn-jnl, thuthesis, pkuthss, sjtuthesis, ustcthesis).")
    parser.add_argument("--template-tex", default="", help="Path to user-supplied school/journal .tex template.")
    parser.add_argument("--inspect-tex", default="", help="Inspect a .tex file or template directory and print detected conventions.")
    parser.add_argument("--prefer-pandoc", action="store_true", help="Use pandoc for .docx if installed.")
    args = parser.parse_args()

    if args.inspect_tex:
        print(json.dumps(inspect_tex_target(Path(args.inspect_tex)), ensure_ascii=False, indent=2))
        return 0

    ws = Path(args.workspace).resolve() if args.workspace else None
    input_files = _collect_inputs(ws, args.inputs)
    if not input_files:
        raise SystemExit("No input Markdown files found. Pass --inputs or populate <workspace>/04_drafts/*.md.")

    spec: dict[str, Any] = {}
    if ws and (ws / "00_project_spec.json").exists():
        spec = json.loads((ws / "00_project_spec.json").read_text(encoding="utf-8"))

    title = args.title or (spec.get("title_working") or "")
    paper_preset = spec.get("paper_preset") or "general"

    lit_path = Path(args.lit_ledger) if args.lit_ledger else (ws / "01_literature" / "02_literature_ledger.json" if ws else None)
    bib_path = Path(args.bib) if args.bib else (ws / "01_literature" / "verified_refs.bib" if ws else None)
    catalog = load_reference_catalog(lit_path, bib_path)

    raw_sections = [p.read_text(encoding="utf-8").strip() for p in input_files]
    assembled_raw = "\n\n".join(s for s in raw_sections if s)

    resolved_body, ref_lines, orphan_keys = resolve_citations(assembled_raw, catalog)
    assembled_with_refs = resolved_body
    if ref_lines and not re.search(r"(?m)^#{1,2}\s+(?:References|参考文献)", resolved_body):
        assembled_with_refs += "\n\n## References\n\n" + "\n\n".join(ref_lines) + "\n"

    search_dirs: list[Path] = []
    for p in input_files:
        if p.resolve().parent not in search_dirs:
            search_dirs.append(p.resolve().parent)
    if ws:
        for sub in (ws, ws / "02_evidence", ws / "04_drafts"):
            if sub not in search_dirs:
                search_dirs.append(sub)

    out_docx = Path(args.out_docx) if args.out_docx else (ws / "06_submission" / "manuscript.docx" if ws else None)
    out_tex = Path(args.out_tex) if args.out_tex else (ws / "06_submission" / "manuscript.tex" if ws else None)
    out_md = Path(args.out_md) if args.out_md else (ws / "06_submission" / "manuscript_assembled.md" if ws else None)

    if out_md:
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(assembled_with_refs, encoding="utf-8")

    docx_backend = None
    docx_meta: dict[str, Any] = {}
    if out_docx:
        break_chapters = paper_preset == "thesis_zh" or args.tex_template in ("ctexbook", "thuthesis", "pkuthss", "sjtuthesis", "ustcthesis")
        if args.prefer_pandoc and shutil.which("pandoc"):
            tmp_md = out_docx.with_suffix(".tmp.md")
            tmp_md.parent.mkdir(parents=True, exist_ok=True)
            tmp_md.write_text(assembled_with_refs, encoding="utf-8")
            proc = subprocess.run([shutil.which("pandoc"), str(tmp_md), "-o", str(out_docx)], check=False)
            tmp_md.unlink(missing_ok=True)
            docx_backend = "pandoc" if proc.returncode == 0 else "stdlib-ooxml"
            if docx_backend == "stdlib-ooxml":
                docx_meta = write_stdlib_docx(assembled_with_refs, title=title, authors=args.authors, out_docx=out_docx, search_dirs=search_dirs, page_break_on_h1=break_chapters)
        else:
            docx_meta = write_stdlib_docx(assembled_with_refs, title=title, authors=args.authors, out_docx=out_docx, search_dirs=search_dirs, page_break_on_h1=break_chapters)
            docx_backend = "stdlib-ooxml"

    tex_meta: dict[str, Any] = {}
    if out_tex:
        out_tex.parent.mkdir(parents=True, exist_ok=True)
        if args.template_tex:
            tex_meta = export_byo_template(Path(args.template_tex), assembled_raw, catalog, out_tex, search_dirs)
        elif args.tex_template:
            tex_meta = export_using_registry_template(args.tex_template, input_files, raw_sections, title, args.authors, catalog, out_tex, search_dirs)
        else:
            tex_src = markdown_to_latex(resolved_body, title=title, authors=args.authors, ref_lines=ref_lines)
            out_tex.write_text(tex_src, encoding="utf-8")
            tex_meta = {"tex_template": "default_single_file", "generated_files": [str(out_tex)]}

    summary = {
        "inputs_compiled": [p.name for p in input_files],
        "resolved_citations_count": len(ref_lines),
        "unverified_orphan_citations": orphan_keys,
        "docx_output": str(out_docx) if out_docx else None,
        "docx_backend": docx_backend,
        "docx_embedded_images": docx_meta.get("embedded_images", []),
        "tex_output": str(out_tex) if out_tex else None,
        "tex_details": tex_meta,
        "status": "WARN_ORPHAN_CITATIONS" if orphan_keys else "PASS",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
