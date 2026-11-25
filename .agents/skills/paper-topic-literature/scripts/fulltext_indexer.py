#!/usr/bin/env python3
"""Local full-text indexer, page/paragraph anchor searcher, and ledger upgrader (Station 01).

Upgrades literature grounding from ABSTRACT_READ to FULLTEXT_READ with exact anchors
like [paper.pdf, p.4, para.2]. Works across .md, .txt, .html, .tex, and .pdf files.
Uses optional PyMuPDF (`pymupdf`), `pypdf`, or `pdftotext` when installed, with a pure
Python stdlib fallback (including basic PDF stream extraction and explicit OCR warning
if a scanned PDF yields no extractable text).
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import zlib
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SUPPORTED_TEXT_EXTS = {".md", ".markdown", ".txt", ".tex", ".html", ".htm", ".rst"}
PAGE_MARKER_REGEX = re.compile(r"^\s*(?:---|===)?\s*(?:page|第)\s*(\d+)\s*(?:页)?\s*(?:---|===)?\s*$", re.IGNORECASE)


def _split_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_paras = re.split(r"\n\s*\n+", normalized)
    cleaned: list[str] = []
    for p in raw_paras:
        collapsed = re.sub(r"\s+", " ", p).strip()
        if len(collapsed) >= 15:
            cleaned.append(collapsed)
    return cleaned


def _extract_pdf_pages_pymupdf(pdf_path: Path) -> tuple[list[tuple[int, str]] | None, str | None]:
    try:
        import pymupdf  # type: ignore
    except ImportError:
        return None, None
    pages: list[tuple[int, str]] = []
    with pymupdf.open(str(pdf_path)) as doc:
        for idx, page in enumerate(doc, start=1):
            pages.append((idx, page.get_text("text") or ""))
    return pages, "pymupdf"


def _extract_pdf_pages_pypdf(pdf_path: Path) -> tuple[list[tuple[int, str]] | None, str | None]:
    reader_cls = None
    backend = None
    try:
        from pypdf import PdfReader  # type: ignore

        reader_cls = PdfReader
        backend = "pypdf"
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore

            reader_cls = PdfReader
            backend = "PyPDF2"
        except ImportError:
            return None, None

    reader = reader_cls(str(pdf_path))
    pages: list[tuple[int, str]] = []
    for idx, page in enumerate(reader.pages, start=1):
        pages.append((idx, page.extract_text() or ""))
    return pages, backend


def _extract_pdf_pages_pdftotext(pdf_path: Path) -> tuple[list[tuple[int, str]] | None, str | None]:
    exe = shutil.which("pdftotext")
    if not exe:
        return None, None
    proc = subprocess.run(
        [exe, "-enc", "UTF-8", str(pdf_path), "-"],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None, None
    raw = proc.stdout.decode("utf-8", errors="replace")
    raw_pages = raw.split("\f")
    if raw_pages and not raw_pages[-1].strip():
        raw_pages.pop()
    return [(idx, txt) for idx, txt in enumerate(raw_pages, start=1)], "pdftotext"


def _extract_pdf_pages_stdlib(pdf_path: Path) -> tuple[list[tuple[int, str]], str]:
    """Best-effort pure Python stdlib text extractor for simple/unencrypted PDF content streams."""
    data = pdf_path.read_bytes()
    streams: list[bytes] = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.DOTALL):
        chunk = m.group(1)
        try:
            streams.append(zlib.decompress(chunk))
        except zlib.error:
            streams.append(chunk)

    extracted_segments: list[str] = []
    for st in streams:
        if b"BT" not in st and b"Tj" not in st and b"TJ" not in st:
            continue
        # Extract literal strings inside (...) before Tj/TJ
        literals = re.findall(rb"\(([^()\\]*(?:\\.[^()\\]*)*)\)\s*(?:Tj|')", st)
        array_groups = re.findall(rb"\[(.*?)\]\s*TJ", st, re.DOTALL)
        for arr in array_groups:
            literals.extend(re.findall(rb"\(([^()\\]*(?:\\.[^()\\]*)*)\)", arr))
        if literals:
            decoded_parts: list[str] = []
            for raw_lit in literals:
                raw_lit = (
                    raw_lit.replace(rb"\(", b"(")
                    .replace(rb"\)", b")")
                    .replace(rb"\\", b"\\")
                    .replace(rb"\n", b"\n")
                )
                decoded_parts.append(raw_lit.decode("utf-8", errors="ignore"))
            extracted_segments.append(" ".join(decoded_parts))

    combined = "\n\n".join(s.strip() for s in extracted_segments if s.strip())
    if not combined:
        return [], "stdlib-pdf-none"
    return [(1, combined)], "stdlib-pdf"


def extract_document_pages(path: Path) -> tuple[list[tuple[int, str]], str]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        for fn in (_extract_pdf_pages_pymupdf, _extract_pdf_pages_pypdf, _extract_pdf_pages_pdftotext):
            pages, backend = fn(path)
            if pages is not None and backend is not None:
                return pages, backend
        return _extract_pdf_pages_stdlib(path)

    raw_text = path.read_text(encoding="utf-8", errors="replace")
    if ext in (".html", ".htm"):
        raw_text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw_text, flags=re.DOTALL | re.IGNORECASE)
        raw_text = re.sub(r"</(p|div|li|h[1-6]|tr|br)\s*>", "\n\n", raw_text, flags=re.IGNORECASE)
        raw_text = html.unescape(re.sub(r"<[^>]+>", " ", raw_text))
    elif ext == ".tex":
        raw_text = re.sub(r"(?m)^%.*$", "", raw_text)

    if "\f" in raw_text:
        parts = [p for p in raw_text.split("\f") if p.strip()]
        return [(i, p) for i, p in enumerate(parts, start=1)], "text-formfeed"

    # Detect explicit page markers like "--- Page 2 ---" or "第 2 页"
    pages_dict: dict[int, list[str]] = {}
    cur_page = 1
    for line in raw_text.splitlines():
        pm = PAGE_MARKER_REGEX.match(line)
        if pm:
            cur_page = int(pm.group(1))
            continue
        pages_dict.setdefault(cur_page, []).append(line)
    return [(pno, "\n".join(lines)) for pno, lines in sorted(pages_dict.items())], f"text-{ext.lstrip('.')}"


def _tokenize(text: str) -> set[str]:
    en = {w.lower() for w in re.findall(r"[A-Za-z0-9]{2,}", text)}
    zh_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    zh_bi: set[str] = set()
    for chunk in zh_chunks:
        zh_bi.add(chunk)
        for i in range(len(chunk) - 1):
            zh_bi.add(chunk[i : i + 2])
    return en | zh_bi


def _norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", s.lower())


def cmd_index(args: argparse.Namespace) -> int:
    in_path = Path(args.input).resolve()
    files: list[Path] = []
    if in_path.is_file():
        files = [in_path]
    elif in_path.is_dir():
        for p in sorted(in_path.rglob("*")):
            if p.is_file() and (p.suffix.lower() == ".pdf" or p.suffix.lower() in SUPPORTED_TEXT_EXTS):
                files.append(p)
    else:
        raise SystemExit(f"Input path does not exist: {in_path}")

    chunks: list[dict[str, Any]] = []
    doc_manifest: list[dict[str, Any]] = []

    for fpath in files:
        pages, backend = extract_document_pages(fpath)
        doc_chunks = 0
        total_chars = 0
        first_excerpt = ""
        for page_no, page_text in pages:
            paras = _split_paragraphs(page_text)
            for para_no, para_text in enumerate(paras, start=1):
                doc_chunks += 1
                total_chars += len(para_text)
                if not first_excerpt:
                    first_excerpt = para_text[:500]
                anchor = f"[{fpath.name}, p.{page_no}, para.{para_no}]"
                chunks.append(
                    {
                        "chunk_id": f"{fpath.stem}_p{page_no}_para{para_no}",
                        "file_name": fpath.name,
                        "file_stem": fpath.stem,
                        "file_path": str(fpath),
                        "page": page_no,
                        "para": para_no,
                        "anchor": anchor,
                        "char_count": len(para_text),
                        "text": para_text,
                    }
                )

        status = "INDEXED" if doc_chunks > 0 else "NEEDS_OCR_OR_PDF_BACKEND"
        doc_manifest.append(
            {
                "file_name": fpath.name,
                "file_stem": fpath.stem,
                "file_path": str(fpath),
                "extractor_backend": backend,
                "pages_count": len(pages),
                "chunks_count": doc_chunks,
                "total_chars": total_chars,
                "status": status,
                "sample_header": first_excerpt,
            }
        )

    out_jsonl = Path(args.out_jsonl)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as fh:
        for ch in chunks:
            fh.write(json.dumps(ch, ensure_ascii=False) + "\n")

    upgraded_refs: list[str] = []
    if args.ledger:
        ledger_path = Path(args.ledger)
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        for doc in doc_manifest:
            if doc["status"] != "INDEXED" or doc["total_chars"] < 150:
                continue
            stem_norm = _norm_key(doc["file_stem"])
            header_norm = _norm_key(doc["sample_header"])
            for entry in ledger.get("entries") or []:
                rid = str(entry.get("ref_id") or "")
                doi = str(entry.get("doi") or "").lower()
                title_norm = _norm_key(str(entry.get("title") or ""))
                matched = False
                if rid and (_norm_key(rid) in stem_norm or stem_norm in _norm_key(rid)):
                    matched = True
                elif doi and doi in doc["sample_header"].lower():
                    matched = True
                elif title_norm and len(title_norm) >= 12 and (title_norm[:24] in header_norm or title_norm[:18] in stem_norm):
                    matched = True

                if matched:
                    entry["reading_depth"] = "FULLTEXT_READ"
                    entry["fulltext_file"] = doc["file_name"]
                    entry["fulltext_chunks_count"] = doc["chunks_count"]
                    if rid and rid not in upgraded_refs:
                        upgraded_refs.append(rid)

        out_ledger = Path(args.out_ledger) if args.out_ledger else ledger_path
        out_ledger.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "indexed_files": len(doc_manifest),
        "total_chunks": len(chunks),
        "out_jsonl": str(out_jsonl),
        "upgraded_to_fulltext_read": upgraded_refs,
        "documents": doc_manifest,
    }
    if args.out_manifest:
        mpath = Path(args.out_manifest)
        mpath.parent.mkdir(parents=True, exist_ok=True)
        mpath.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    idx_path = Path(args.index)
    if not idx_path.exists():
        raise SystemExit(f"Index file not found: {idx_path}")

    q_tokens = _tokenize(args.query)
    if not q_tokens:
        q_tokens = {args.query.strip().lower()}
    q_low = args.query.strip().lower()
    file_filter = (args.file_filter or "").strip().lower()

    scored: list[tuple[float, dict[str, Any]]] = []
    with idx_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            chunk = json.loads(line)
            if file_filter and file_filter not in chunk["file_name"].lower():
                continue
            text = chunk["text"]
            c_tokens = _tokenize(text)
            overlap = len(q_tokens & c_tokens)
            phrase_bonus = 3.0 if q_low and q_low in text.lower() else 0.0
            score = overlap + phrase_bonus
            if score > 0:
                scored.append((score, chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    hits = [
        {
            "score": round(sc, 2),
            "anchor": ch["anchor"],
            "file_name": ch["file_name"],
            "page": ch["page"],
            "para": ch["para"],
            "excerpt": ch["text"],
        }
        for sc, ch in scored[: args.top_k]
    ]
    print(json.dumps({"query": args.query, "total_hits": len(scored), "top_hits": hits}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Local full-text indexer & page/paragraph anchor searcher.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_idx = sub.add_parser("index", help="Index local PDF/Markdown/TXT full-text papers into anchored chunks.")
    p_idx.add_argument("--input", required=True, help="File or directory containing local full-text files.")
    p_idx.add_argument("--out-jsonl", required=True, help="Output JSONL path for indexed chunks.")
    p_idx.add_argument("--out-manifest", default="", help="Optional manifest JSON path.")
    p_idx.add_argument("--ledger", default="", help="Optional 02_literature_ledger.json to auto-upgrade to FULLTEXT_READ.")
    p_idx.add_argument("--out-ledger", default="", help="Optional path for updated ledger (defaults to --ledger in-place).")

    p_search = sub.add_parser("search", help="Search indexed full-text chunks and retrieve verbatim page/paragraph anchors.")
    p_search.add_argument("--index", required=True, help="Path to fulltext_chunks.jsonl.")
    p_search.add_argument("--query", required=True, help="Keywords or claim to locate inside full texts.")
    p_search.add_argument("--file-filter", default="", help="Optional substring filter on file_name.")
    p_search.add_argument("--top-k", type=int, default=6, help="Maximum matching chunks to return.")

    args = parser.parse_args()
    if args.command == "index":
        return cmd_index(args)
    return cmd_search(args)


if __name__ == "__main__":
    raise SystemExit(main())
