"""Fetch recent papers from arXiv (cs.AI, cs.LG) via the Atom API."""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any

import feedparser
import requests

logger = logging.getLogger(__name__)

# Official Atom API (RSS feeds omit items on weekends via skipDays; API is reliable.)
ARXIV_API = "http://export.arxiv.org/api/query"
CATEGORIES = ("cs.AI", "cs.LG")
USER_AGENT = "DailyResearchCurator/1.0 (mailto:local)"
TIMEOUT = 60


def _strip_summary(text: str) -> str:
    return " ".join(text.split()).strip()


def _entry_to_item(entry: Any, label: str) -> dict[str, Any] | None:
    title = (getattr(entry, "title", None) or "").strip()
    title = title.replace("\n", " ")
    link = (getattr(entry, "link", None) or "").strip()
    if not title or not link:
        return None
    summary_raw = getattr(entry, "summary", None) or ""
    summary = _strip_summary(summary_raw) or "(No abstract.)"
    published = (getattr(entry, "published", None) or getattr(entry, "updated", None) or "").strip()
    prim = getattr(entry, "arxiv_primary_category", None)
    if prim and getattr(prim, "term", None):
        src = f"arXiv {prim.term}"
    else:
        src = f"arXiv {label}"
    return {
        "title": title,
        "summary": summary,
        "link": link,
        "source": src,
        "published": published,
    }


def _fetch_category(label: str, max_results: int) -> list[dict[str, Any]]:
    params = {
        "search_query": f"cat:{label}",
        "start": "0",
        "max_results": str(max_results),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("arXiv API request failed for %s: %s", label, e)
        return []

    parsed = feedparser.parse(r.content)
    out: list[dict[str, Any]] = []
    for entry in getattr(parsed, "entries", []) or []:
        item = _entry_to_item(entry, label)
        if item:
            out.append(item)
    return out


def fetch_arxiv_papers(max_total: int = 20) -> list[dict[str, Any]]:
    """Fetch up to ``max_total`` recent papers from cs.AI and cs.LG (Atom API)."""
    seen: set[str] = set()
    combined: list[dict[str, Any]] = []

    for label in CATEGORIES:
        # Request ``max_total`` per category so we still reach ``max_total`` after merge/dedupe.
        batch = _fetch_category(label, max_total)
        for item in batch:
            key = item["link"]
            if key in seen:
                continue
            seen.add(key)
            combined.append(item)
            if len(combined) >= max_total:
                return combined[:max_total]

    return combined[:max_total]
