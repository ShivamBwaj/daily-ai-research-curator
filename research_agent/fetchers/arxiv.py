"""Fetch recent papers from arXiv (cs.AI, cs.LG) via the Atom API."""

from __future__ import annotations

import logging
import time
import urllib.parse
from typing import Any

import feedparser
import requests

logger = logging.getLogger(__name__)

# HTTPS; be polite — shared CI IPs (e.g. GitHub Actions) often get 429 without delays/retries.
ARXIV_API = "https://export.arxiv.org/api/query"
CATEGORIES = ("cs.AI", "cs.LG")
USER_AGENT = (
    "DailyResearchCurator/1.0 "
    "(+https://github.com/ShivamBwaj/daily-ai-research-curator; contact via repo)"
)
TIMEOUT = 60
MAX_RETRIES = 5
BACKOFF_BASE_SEC = 4
# arXiv asks for ~3s between bulk requests; CI runners are easy to throttle.
DELAY_BETWEEN_CATEGORIES_SEC = 5.0


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
    headers = {"User-Agent": USER_AGENT}

    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=headers, timeout=TIMEOUT)
            if r.status_code == 429:
                wait = BACKOFF_BASE_SEC * (2**attempt)
                logger.warning(
                    "arXiv rate limited (429) for %s, sleeping %ss (attempt %s/%s)",
                    label,
                    wait,
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(wait)
                continue
            if r.status_code >= 500:
                wait = BACKOFF_BASE_SEC * (2**attempt)
                logger.warning(
                    "arXiv server error %s for %s, sleeping %ss",
                    r.status_code,
                    label,
                    wait,
                )
                time.sleep(wait)
                continue
            r.raise_for_status()
            parsed = feedparser.parse(r.content)
            out: list[dict[str, Any]] = []
            for entry in getattr(parsed, "entries", []) or []:
                item = _entry_to_item(entry, label)
                if item:
                    out.append(item)
            return out
        except requests.RequestException as e:
            logger.warning("arXiv API request failed for %s: %s", label, e)
            if attempt < MAX_RETRIES - 1:
                time.sleep(BACKOFF_BASE_SEC * (2**attempt))
            else:
                return []
    return []


def fetch_arxiv_papers(max_total: int = 20) -> list[dict[str, Any]]:
    """Fetch up to ``max_total`` recent papers from cs.AI and cs.LG (Atom API)."""
    seen: set[str] = set()
    combined: list[dict[str, Any]] = []

    for i, label in enumerate(CATEGORIES):
        if i > 0:
            time.sleep(DELAY_BETWEEN_CATEGORIES_SEC)
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
