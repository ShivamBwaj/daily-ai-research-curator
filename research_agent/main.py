#!/usr/bin/env python3
"""Daily AI Research Curator — entry point."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fetchers.arxiv import fetch_arxiv_papers
from fetchers.news import fetch_news_items
from processor.ranker import rank_items
from utils.config import REPORTS_DIR, load_config
from utils.formatter import format_daily_brief, format_daily_brief_short
from utils.logger import setup_logger

logger = setup_logger()


def _ensure_utf8_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def normalize_item(raw: dict) -> dict[str, str]:
    title = str(raw.get("title", "")).strip()
    link = str(raw.get("link", "")).strip()
    source = str(raw.get("source", "")).strip()
    summary = str(raw.get("summary", "")).strip()
    pub = raw.get("published")
    if pub:
        summary = f"Published: {pub}\n\n{summary}"
    return {
        "title": title,
        "summary": summary,
        "link": link,
        "source": source,
    }


def run_pipeline() -> int:
    _ensure_utf8_stdout()
    cfg = load_config()
    today = date.today()

    from delivery.email import send_email_report
    from delivery.telegram import send_telegram_message

    exit_code = 0

    try:
        logger.info("Fetching arXiv papers…")
        arxiv_items = fetch_arxiv_papers(max_total=20)
        logger.info("Fetched %s arXiv items.", len(arxiv_items))
    except Exception as e:
        logger.exception("arXiv fetch error: %s", e)
        arxiv_items = []

    try:
        logger.info("Fetching news…")
        news_items = fetch_news_items(max_per_query=15)
        logger.info("Fetched %s news items.", len(news_items))
    except Exception as e:
        logger.exception("News fetch error: %s", e)
        news_items = []

    combined = arxiv_items + news_items
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / f"{today.isoformat()}.md"

    if not combined:
        logger.warning("All feeds empty or failed; writing minimal report.")
        markdown = format_daily_brief(today, [])
        short = format_daily_brief_short(today, [])
        try:
            out_path.write_text(markdown, encoding="utf-8")
        except OSError as e:
            logger.error("Could not write report: %s", e)
        print(markdown)
        try:
            send_email_report(cfg, f"Daily AI Brief {today.isoformat()}", markdown)
        except Exception as e:
            logger.exception("Email send error: %s", e)
        try:
            send_telegram_message(cfg, short)
        except Exception as e:
            logger.exception("Telegram send error: %s", e)
        return 0

    normalized = [normalize_item(x) for x in combined]

    ranked: list[dict[str, Any]] = []
    if not cfg.google_api_key:
        logger.error(
            "GEMINI_API_KEY or GOOGLE_API_KEY missing. Set in .env or GitHub Secrets."
        )
        exit_code = 1
    else:
        try:
            ranked = rank_items(cfg, normalized)
        except Exception as e:
            logger.exception("Ranking error: %s", e)
            exit_code = 1

    if not ranked and cfg.google_api_key:
        logger.warning("Ranking returned no items; report will show empty ranking.")
        exit_code = max(exit_code, 1)

    markdown = format_daily_brief(today, ranked)
    short = format_daily_brief_short(today, ranked)

    try:
        out_path.write_text(markdown, encoding="utf-8")
        logger.info("Report saved to %s", out_path)
    except OSError as e:
        logger.error("Could not write report: %s", e)
        exit_code = 1

    print(markdown)

    try:
        send_email_report(cfg, f"Daily AI Research Brief – {today.isoformat()}", markdown)
    except Exception as e:
        logger.exception("Email send error: %s", e)

    try:
        send_telegram_message(cfg, short)
    except Exception as e:
        logger.exception("Telegram send error: %s", e)

    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily AI Research Curator")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Fetch, rank, save report, email, telegram, then exit (default behavior).",
    )
    parser.parse_args()
    code = run_pipeline()
    raise SystemExit(code)


if __name__ == "__main__":
    main()
