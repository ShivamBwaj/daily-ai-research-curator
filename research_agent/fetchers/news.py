"""Fetch headlines from Google News RSS."""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any

import feedparser
import requests

logger = logging.getLogger(__name__)

QUERIES = ["AI agents", "LLM", "RAG AI"]
USER_AGENT = "DailyResearchCurator/1.0 (local)"
TIMEOUT = 30


def _google_news_rss_url(query: str) -> str:
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def _parse_feed(url: str, query_label: str) -> list[dict[str, Any]]:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("News RSS fetch failed (%s): %s", query_label, e)
        return []

    parsed = feedparser.parse(r.content)
    out: list[dict[str, Any]] = []
    for entry in getattr(parsed, "entries", []) or []:
        title = (getattr(entry, "title", None) or "").strip()
        link = (getattr(entry, "link", None) or "").strip()
        source_title = ""
        if getattr(entry, "source", None):
            source_title = (getattr(entry.source, "title", None) or "").strip()
        if not title or not link:
            continue
        summary = f"News query: “{query_label}”. Source feed: Google News."
        out.append(
            {
                "title": title,
                "summary": summary,
                "link": link,
                "source": source_title or "Google News",
            }
        )
    return out


def fetch_news_items(max_per_query: int = 15) -> list[dict[str, Any]]:
    """Fetch news items for configured queries; dedupe by link."""
    seen: set[str] = set()
    combined: list[dict[str, Any]] = []

    for q in QUERIES:
        url = _google_news_rss_url(q)
        batch = _parse_feed(url, q)[:max_per_query]
        for item in batch:
            key = item["link"]
            if key in seen:
                continue
            seen.add(key)
            combined.append(item)

    return combined
