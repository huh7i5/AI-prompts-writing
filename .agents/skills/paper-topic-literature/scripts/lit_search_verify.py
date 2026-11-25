#!/usr/bin/env python3
"""Zero-dependency academic literature search & citation verification engine (Station 01).

Queries keyless open scholarly APIs (OpenAlex, CrossRef, arXiv) using only the Python 3
standard library. Enforces strict provenance tracking, reading-depth tagging
(ABSTRACT_READ vs METADATA_ONLY), counter-query retrieval, and graceful offline fallback.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# Ensure Windows consoles never crash on Unicode paper titles or Chinese messages.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

USER_AGENT = (
    "paper-topic-literature-skill/1.0 "
    "(https://github.com/huh7i5/AI-prompts-writing; mailto:academic-skill@users.noreply.github.com)"
)

FAKE_DOI_PREFIXES = ("10.0000/", "10.1234/", "10.5555/", "10.9999/")
DOI_REGEX = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)")
ARXIV_REGEX = re.compile(r"\barXiv:(\d{4}\.\d{4,5}(?:v\d+)?)\b", re.IGNORECASE)
STOPWORDS = {"the", "a", "an", "of", "in", "on", "for", "and", "to", "with", "using", "via", "from", "by"}


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _clean_doi(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = raw.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:", "DOI:"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
    cleaned = cleaned.rstrip(".,;)]}>\"'")
    if cleaned.lower().endswith(".pdf"):
        cleaned = cleaned[:-4]
    return cleaned.lower() if cleaned else None


def _is_fake_doi(doi: str) -> bool:
    low = doi.lower()
    return any(low.startswith(p) for p in FAKE_DOI_PREFIXES) or "/fake" in low


def _strip_markup(text: str | None) -> str:
    if not text:
        return ""
    unescaped = html.unescape(text)
    no_tags = re.sub(r"<[^>]+>", " ", unescaped)
    return re.sub(r"\s+", " ", no_tags).strip()


def _reconstruct_openalex_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    max_idx = -1
    for positions in inverted_index.values():
        if positions:
            local_max = max(positions)
            if local_max > max_idx:
                max_idx = local_max
    if max_idx < 0 or max_idx > 20000:
        return ""
    words = [""] * (max_idx + 1)
    for token, positions in inverted_index.items():
        for pos in positions:
            if 0 <= pos <= max_idx:
                words[pos] = token
    return re.sub(r"\s+", " ", " ".join(w for w in words if w)).strip()


def _http_get_json(url: str, timeout: float = 12.0) -> tuple[dict[str, Any] | None, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
            return json.loads(payload), None
    except urllib.error.HTTPError as exc:
        return None, f"HTTP_{exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return None, f"NET_ERR:{type(exc).__name__}"


def _http_get_text(url: str, timeout: float = 12.0) -> tuple[str | None, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as exc:
        return None, f"HTTP_{exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, f"NET_ERR:{type(exc).__name__}"


def search_openalex(
    query: str,
    max_results: int,
    since: int | None,
    until: int | None,
    polarity: str,
) -> tuple[list[dict[str, Any]], str | None]:
    params: dict[str, Any] = {"search": query, "per-page": max_results}
    filters: list[str] = []
    if since:
        filters.append(f"from_publication_date:{since}-01-01")
    if until:
        filters.append(f"to_publication_date:{until}-12-31")
    if filters:
        params["filter"] = ",".join(filters)
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    data, err = _http_get_json(url)
    if err or not data:
        return [], err or "EMPTY_RESPONSE"

    results: list[dict[str, Any]] = []
    for item in data.get("results", []):
        title = _strip_markup(item.get("display_name") or item.get("title"))
        if not title:
            continue
        doi = _clean_doi(item.get("doi"))
        authors = [
            a.get("author", {}).get("display_name", "").strip()
            for a in item.get("authorships", [])
            if a.get("author", {}).get("display_name")
        ]
        year = item.get("publication_year")
        primary_loc = item.get("primary_location") or {}
        source_obj = primary_loc.get("source") or {}
        venue = source_obj.get("display_name")
        oa_info = item.get("open_access") or {}
        oa_url = oa_info.get("oa_url") or primary_loc.get("landing_page_url") or item.get("id")
        abstract = _reconstruct_openalex_abstract(item.get("abstract_inverted_index"))
        depth = "ABSTRACT_READ" if len(abstract) >= 30 else "METADATA_ONLY"
        results.append(
            {
                "title": title,
                "authors": authors,
                "year": int(year) if isinstance(year, int) else None,
                "venue": venue,
                "doi": doi,
                "arxiv_id": None,
                "openalex_id": item.get("id"),
                "url": oa_url or (f"https://doi.org/{doi}" if doi else None),
                "cited_by_count": item.get("cited_by_count"),
                "sources_matched": ["openalex"],
                "polarity_tag": polarity,
                "verification_status": "API_VERIFIED",
                "reading_depth": depth,
                "abstract_text": abstract or None,
            }
        )
    return results, None


def search_crossref(
    query: str,
    max_results: int,
    since: int | None,
    until: int | None,
    polarity: str,
) -> tuple[list[dict[str, Any]], str | None]:
    params: dict[str, Any] = {"query": query, "rows": max_results}
    filters: list[str] = []
    if since:
        filters.append(f"from-pub-date:{since}")
    if until:
        filters.append(f"until-pub-date:{until}")
    if filters:
        params["filter"] = ",".join(filters)
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    data, err = _http_get_json(url)
    if err or not data:
        return [], err or "EMPTY_RESPONSE"

    items = (data.get("message") or {}).get("items") or []
    results: list[dict[str, Any]] = []
    for item in items:
        titles = item.get("title") or []
        title = _strip_markup(titles[0] if titles else "")
        if not title:
            continue
        doi = _clean_doi(item.get("DOI"))
        authors: list[str] = []
        for a in item.get("author") or []:
            given = (a.get("given") or "").strip()
            family = (a.get("family") or "").strip()
            full = f"{given} {family}".strip() or (a.get("name") or "").strip()
            if full:
                authors.append(full)
        year = _extract_crossref_year(item)
        containers = item.get("container-title") or []
        venue = _strip_markup(containers[0]) if containers else None
        abstract = _strip_markup(item.get("abstract"))
        depth = "ABSTRACT_READ" if len(abstract) >= 30 else "METADATA_ONLY"
        results.append(
            {
                "title": title,
                "authors": authors,
                "year": year,
                "venue": venue,
                "doi": doi,
                "arxiv_id": None,
                "openalex_id": None,
                "url": item.get("URL") or (f"https://doi.org/{doi}" if doi else None),
                "cited_by_count": item.get("is-referenced-by-count"),
                "sources_matched": ["crossref"],
                "polarity_tag": polarity,
                "verification_status": "API_VERIFIED",
                "reading_depth": depth,
                "abstract_text": abstract or None,
            }
        )
    return results, None


def _extract_crossref_year(item: dict[str, Any]) -> int | None:
    for field in ("published-print", "published-online", "published", "issued", "created"):
        part = item.get(field) or {}
        date_parts = part.get("date-parts") or []
        if date_parts and date_parts[0] and isinstance(date_parts[0][0], int):
            return int(date_parts[0][0])
    return None


def search_arxiv(
    query: str,
    max_results: int,
    since: int | None,
    until: int | None,
    polarity: str,
) -> tuple[list[dict[str, Any]], str | None]:
    raw_tokens = re.findall(r"[A-Za-z0-9\u4e00-\u9fff-]+", query)
    bool_ops = {"and", "or", "not"}
    terms = [t for t in raw_tokens if t.lower() not in bool_ops]
    arxiv_q = " AND ".join(f"all:{t}" for t in terms[:8]) if terms else query
    params = {
        "search_query": arxiv_q,
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
    xml_text, err = _http_get_text(url)
    if err or not xml_text:
        return [], err or "EMPTY_RESPONSE"

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return [], "XML_PARSE_ERR"

    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    results: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ns):
        title = _strip_markup(entry.findtext("atom:title", default="", namespaces=ns))
        if not title:
            continue
        published = entry.findtext("atom:published", default="", namespaces=ns)
        year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None
        if since and year and year < since:
            continue
        if until and year and year > until:
            continue
        raw_id = entry.findtext("atom:id", default="", namespaces=ns).strip()
        arxiv_id = raw_id.rsplit("/abs/", 1)[-1] if "/abs/" in raw_id else raw_id
        doi = _clean_doi(entry.findtext("arxiv:doi", default="", namespaces=ns))
        authors = [
            (a.findtext("atom:name", default="", namespaces=ns) or "").strip()
            for a in entry.findall("atom:author", ns)
            if (a.findtext("atom:name", default="", namespaces=ns) or "").strip()
        ]
        summary = _strip_markup(entry.findtext("atom:summary", default="", namespaces=ns))
        depth = "ABSTRACT_READ" if len(summary) >= 30 else "METADATA_ONLY"
        results.append(
            {
                "title": title,
                "authors": authors,
                "year": year,
                "venue": "arXiv preprint",
                "doi": doi,
                "arxiv_id": arxiv_id or None,
                "openalex_id": None,
                "url": raw_id or (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None),
                "cited_by_count": None,
                "sources_matched": ["arxiv"],
                "polarity_tag": polarity,
                "verification_status": "API_VERIFIED",
                "reading_depth": depth,
                "abstract_text": summary or None,
            }
        )
    return results, None


def _norm_title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", title.lower())


def _make_ref_id(entry: dict[str, Any], used: set[str]) -> str:
    authors = entry.get("authors") or []
    surname = "anon"
    if authors:
        ascii_author = unicodedata.normalize("NFKD", authors[0]).encode("ascii", "ignore").decode("ascii")
        parts = re.findall(r"[A-Za-z]+", ascii_author)
        if parts:
            surname = parts[-1].lower()
    year = str(entry.get("year") or "nd")
    words = [w.lower() for w in re.findall(r"[A-Za-z]{3,}", entry.get("title") or "") if w.lower() not in STOPWORDS]
    keyword = words[0] if words else "paper"
    base = f"{surname}{year}{keyword}"
    candidate = base
    idx = 0
    while candidate in used:
        idx += 1
        suffix = chr(ord("a") + (idx - 1) % 26)
        candidate = f"{base}{suffix}" if idx <= 26 else f"{base}{idx}"
    used.add(candidate)
    return candidate


def deduplicate_and_assign_keys(raw_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_by_key: dict[str, dict[str, Any]] = {}
    doi_to_key: dict[str, str] = {}

    for item in raw_entries:
        doi = item.get("doi")
        tkey = _norm_title_key(item.get("title") or "")
        canonical_key = None
        if doi and doi in doi_to_key:
            canonical_key = doi_to_key[doi]
        elif tkey and tkey in merged_by_key:
            canonical_key = tkey
        else:
            canonical_key = tkey or (doi or f"item_{len(merged_by_key)}")

        if canonical_key not in merged_by_key:
            merged_by_key[canonical_key] = dict(item)
            if doi:
                doi_to_key[doi] = canonical_key
        else:
            existing = merged_by_key[canonical_key]
            for src in item.get("sources_matched", []):
                if src not in existing["sources_matched"]:
                    existing["sources_matched"].append(src)
            if not existing.get("doi") and doi:
                existing["doi"] = doi
                doi_to_key[doi] = canonical_key
            if not existing.get("arxiv_id") and item.get("arxiv_id"):
                existing["arxiv_id"] = item["arxiv_id"]
            if not existing.get("openalex_id") and item.get("openalex_id"):
                existing["openalex_id"] = item["openalex_id"]
            if not existing.get("abstract_text") and item.get("abstract_text"):
                existing["abstract_text"] = item["abstract_text"]
                existing["reading_depth"] = item["reading_depth"]
            if existing.get("cited_by_count") is None and item.get("cited_by_count") is not None:
                existing["cited_by_count"] = item["cited_by_count"]

    used_ids: set[str] = set()
    final_list: list[dict[str, Any]] = []
    for entry in merged_by_key.values():
        entry["ref_id"] = _make_ref_id(entry, used_ids)
        final_list.append(entry)
    return final_list


def format_bibtex(entries: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for e in entries:
        if e.get("verification_status") != "API_VERIFIED":
            continue
        ref_id = e["ref_id"]
        authors = " and ".join(e.get("authors") or ["Unknown"])
        title = (e.get("title") or "").replace("{", "\\{").replace("}", "\\}")
        year = e.get("year") or ""
        venue = (e.get("venue") or "").replace("&", "\\&")
        doi = e.get("doi") or ""
        url = e.get("url") or ""
        depth = e.get("reading_depth") or "METADATA_ONLY"
        lines = [
            f"@article{{{ref_id},",
            f"  title = {{{title}}},",
            f"  author = {{{authors}}},",
        ]
        if year:
            lines.append(f"  year = {{{year}}},")
        if venue:
            lines.append(f"  journal = {{{venue}}},")
        if doi:
            lines.append(f"  doi = {{{doi}}},")
        if url:
            lines.append(f"  url = {{{url}}},")
        lines.append(f"  note = {{verified_via={'+'.join(e.get('sources_matched', []))}; reading_depth={depth}}}")
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def verify_single_doi(doi: str, offline: bool = False) -> dict[str, Any]:
    clean = _clean_doi(doi) or doi
    if _is_fake_doi(clean):
        return {
            "identifier": clean,
            "id_type": "doi",
            "verification_status": "REJECTED_FAKE_PREFIX",
            "reason": "Reserved test or fabricated DOI prefix detected.",
        }
    if offline:
        return {
            "identifier": clean,
            "id_type": "doi",
            "verification_status": "UNCHECKED_OFFLINE",
            "reason": "Offline mode enabled; external verification skipped.",
        }

    encoded = urllib.parse.quote(clean, safe="")
    cr_data, cr_err = _http_get_json(f"https://api.crossref.org/works/{encoded}")
    if cr_data and cr_data.get("message"):
        msg = cr_data["message"]
        titles = msg.get("title") or []
        title = _strip_markup(titles[0]) if titles else ""
        authors = [
            f"{(a.get('given') or '').strip()} {(a.get('family') or '').strip()}".strip()
            for a in (msg.get("author") or [])
        ]
        abstract = _strip_markup(msg.get("abstract"))
        return {
            "identifier": clean,
            "id_type": "doi",
            "verification_status": "API_VERIFIED",
            "matched_source": "crossref",
            "title": title,
            "authors": [a for a in authors if a],
            "year": _extract_crossref_year(msg),
            "reading_depth": "ABSTRACT_READ" if len(abstract) >= 30 else "METADATA_ONLY",
        }

    oa_url = f"https://api.openalex.org/works/https://doi.org/{encoded}"
    oa_data, oa_err = _http_get_json(oa_url)
    if oa_data and oa_data.get("id"):
        abstract = _reconstruct_openalex_abstract(oa_data.get("abstract_inverted_index"))
        authors = [
            a.get("author", {}).get("display_name", "").strip()
            for a in oa_data.get("authorships", [])
            if a.get("author", {}).get("display_name")
        ]
        return {
            "identifier": clean,
            "id_type": "doi",
            "verification_status": "API_VERIFIED",
            "matched_source": "openalex",
            "title": _strip_markup(oa_data.get("display_name")),
            "authors": authors,
            "year": oa_data.get("publication_year"),
            "reading_depth": "ABSTRACT_READ" if len(abstract) >= 30 else "METADATA_ONLY",
        }

    if (cr_err and cr_err.startswith("NET_ERR")) and (oa_err and oa_err.startswith("NET_ERR")):
        return {
            "identifier": clean,
            "id_type": "doi",
            "verification_status": "UNCHECKED_OFFLINE",
            "reason": f"Network unreachable ({cr_err}).",
        }

    return {
        "identifier": clean,
        "id_type": "doi",
        "verification_status": "NOT_FOUND",
        "reason": f"DOI not found in CrossRef ({cr_err}) or OpenAlex ({oa_err}).",
    }


def verify_single_arxiv(arxiv_id: str, offline: bool = False) -> dict[str, Any]:
    clean = re.sub(r"^arxiv:", "", arxiv_id.strip(), flags=re.IGNORECASE)
    if offline:
        return {
            "identifier": clean,
            "id_type": "arxiv",
            "verification_status": "UNCHECKED_OFFLINE",
            "reason": "Offline mode enabled.",
        }
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({"id_list": clean})
    xml_text, err = _http_get_text(url)
    if err or not xml_text:
        status = "UNCHECKED_OFFLINE" if (err and err.startswith("NET_ERR")) else "NOT_FOUND"
        return {"identifier": clean, "id_type": "arxiv", "verification_status": status, "reason": err}
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {"identifier": clean, "id_type": "arxiv", "verification_status": "NOT_FOUND", "reason": "XML_PARSE_ERR"}
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        return {"identifier": clean, "id_type": "arxiv", "verification_status": "NOT_FOUND"}
    title = _strip_markup(entry.findtext("atom:title", default="", namespaces=ns))
    if not title or title.lower() == "error":
        return {"identifier": clean, "id_type": "arxiv", "verification_status": "NOT_FOUND"}
    published = entry.findtext("atom:published", default="", namespaces=ns)
    year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None
    authors = [
        (a.findtext("atom:name", default="", namespaces=ns) or "").strip()
        for a in entry.findall("atom:author", ns)
    ]
    return {
        "identifier": clean,
        "id_type": "arxiv",
        "verification_status": "API_VERIFIED",
        "matched_source": "arxiv",
        "title": title,
        "authors": [a for a in authors if a],
        "year": year,
        "reading_depth": "ABSTRACT_READ",
    }


def cmd_search(args: argparse.Namespace) -> int:
    sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
    if args.offline:
        ledger = {
            "schema_version": "1.0",
            "generated_at": _utc_now_iso(),
            "capability_state": "OFFLINE_FALLBACK",
            "is_systematic_review": False,
            "instruction": (
                "OFFLINE_FALLBACK: Do NOT output any memorized references, authors, titles, or DOIs. "
                "Output ONLY search concept breakdown, bilingual Boolean queries (including counter-evidence), "
                "and screening criteria."
            ),
            "search_protocol": {
                "primary_query": args.query,
                "counter_or_alt_query": args.counter_query or "",
                "databases_queried": [],
                "year_from": args.since,
                "year_to": args.until,
                "inclusion_criteria": [],
            },
            "entries": [],
        }
        if args.out_ledger:
            Path(args.out_ledger).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out_ledger).write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(ledger, ensure_ascii=False, indent=2))
        return 0

    raw_entries: list[dict[str, Any]] = []
    source_errors: dict[str, str] = {}
    succeeded_sources: list[str] = []

    queries_to_run = [(args.query, "PRIMARY_QUERY", args.max_results)]
    if args.counter_query:
        counter_limit = max(2, args.max_results // 2)
        queries_to_run.append((args.counter_query, "COUNTER_OR_ALT_QUERY", counter_limit))

    for q_text, polarity, limit in queries_to_run:
        for src in sources:
            if src == "openalex":
                items, err = search_openalex(q_text, limit, args.since, args.until, polarity)
            elif src == "crossref":
                items, err = search_crossref(q_text, limit, args.since, args.until, polarity)
            elif src == "arxiv":
                items, err = search_arxiv(q_text, limit, args.since, args.until, polarity)
            else:
                continue
            if err:
                source_errors[f"{src}:{polarity}"] = err
            else:
                if src not in succeeded_sources:
                    succeeded_sources.append(src)
                raw_entries.extend(items)

    if not succeeded_sources:
        capability_state = "OFFLINE_FALLBACK"
    else:
        capability_state = "ONLINE_API_VERIFIED"

    deduped = deduplicate_and_assign_keys(raw_entries)
    ledger = {
        "schema_version": "1.0",
        "generated_at": _utc_now_iso(),
        "capability_state": capability_state,
        "is_systematic_review": False,
        "source_diagnostics": source_errors,
        "search_protocol": {
            "primary_query": args.query,
            "counter_or_alt_query": args.counter_query or "",
            "databases_queried": succeeded_sources,
            "year_from": args.since,
            "year_to": args.until,
            "inclusion_criteria": [],
        },
        "total_verified_entries": len(deduped),
        "entries": deduped,
    }

    if args.out_ledger:
        out_path = Path(args.out_ledger)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.out_bib and deduped:
        bib_path = Path(args.out_bib)
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        bib_path.write_text(format_bibtex(deduped), encoding="utf-8")

    print(json.dumps(ledger, ensure_ascii=False, indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    dois: list[str] = list(args.doi or [])
    arxivs: list[str] = list(args.arxiv or [])

    if args.from_file:
        text = Path(args.from_file).read_text(encoding="utf-8")
        for match in DOI_REGEX.findall(text):
            cleaned = _clean_doi(match)
            if cleaned and cleaned not in dois:
                dois.append(cleaned)
        for match in ARXIV_REGEX.findall(text):
            if match not in arxivs:
                arxivs.append(match)

    results: list[dict[str, Any]] = []
    for d in dois:
        results.append(verify_single_doi(d, offline=args.offline))
    for a in arxivs:
        results.append(verify_single_arxiv(a, offline=args.offline))

    invalid_count = sum(
        1 for r in results if r["verification_status"] in ("NOT_FOUND", "REJECTED_FAKE_PREFIX")
    )
    report = {
        "generated_at": _utc_now_iso(),
        "total_checked": len(results),
        "verified_count": sum(1 for r in results if r["verification_status"] == "API_VERIFIED"),
        "invalid_or_fake_count": invalid_count,
        "status": "BLOCKED" if invalid_count > 0 else "PASS",
        "results": results,
    }

    if args.out_report:
        out_path = Path(args.out_report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if invalid_count > 0 else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Zero-dependency OpenAlex/CrossRef/arXiv search and DOI verification tool."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="Search real scholarly APIs and export verified ledger/BibTeX.")
    p_search.add_argument("--query", required=True, help="Primary scholarly search terms.")
    p_search.add_argument("--counter-query", default="", help="Counter-evidence / null-result / alternative query.")
    p_search.add_argument(
        "--sources",
        default="openalex,crossref,arxiv",
        help="Comma-separated APIs to query (default: openalex,crossref,arxiv).",
    )
    p_search.add_argument("--since", type=int, default=None, help="Start publication year (inclusive).")
    p_search.add_argument("--until", type=int, default=None, help="End publication year (inclusive).")
    p_search.add_argument("--max-results", type=int, default=6, help="Max results per source for primary query.")
    p_search.add_argument("--offline", action="store_true", help="Force offline search-plan fallback mode.")
    p_search.add_argument("--out-ledger", default="", help="Optional path to write JSON literature ledger.")
    p_search.add_argument("--out-bib", default="", help="Optional path to write BibTeX file.")

    p_verify = sub.add_parser("verify", help="Verify DOIs and arXiv IDs individually or extracted from a file.")
    p_verify.add_argument("--doi", nargs="*", default=[], help="One or more DOIs to verify.")
    p_verify.add_argument("--arxiv", nargs="*", default=[], help="One or more arXiv IDs to verify.")
    p_verify.add_argument("--from-file", default="", help="Markdown/BibTeX/text file to scan for DOIs & arXiv IDs.")
    p_verify.add_argument("--offline", action="store_true", help="Run format/fake-prefix checks only without network.")
    p_verify.add_argument("--out-report", default="", help="Optional JSON output report path.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "search":
        return cmd_search(args)
    if args.command == "verify":
        return cmd_verify(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
