"""Format the daily brief as Markdown (full and short)."""

from __future__ import annotations

from datetime import date
from typing import Any


def format_daily_brief(
    report_date: date,
    ranked: list[dict[str, Any]],
) -> str:
    lines: list[str] = [
        f"🧠 Daily AI Research Brief – {report_date.isoformat()}",
        "",
    ]
    if not ranked:
        lines.append("_No ranked items today (no input or ranking failed)._")
        lines.append("")
        return "\n".join(lines)

    for i, item in enumerate(ranked, start=1):
        title = str(item.get("title", "")).strip()
        source = str(item.get("source", "")).strip() or "—"
        reason = str(item.get("reason", "")).strip()
        score = item.get("score", "")
        verdict = str(item.get("verdict", "")).strip()
        link = str(item.get("link", "")).strip()

        lines.append(f"## {i}. {title}")
        lines.append("")
        lines.append(f"- **Source:** {source}")
        lines.append(f"- **Why it matters:** {reason}")
        lines.append(f"- **Score:** {score}/10")
        lines.append(f"- **Verdict:** {verdict}")
        lines.append(f"- **Link:** {link}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def format_daily_brief_short(
    report_date: date,
    ranked: list[dict[str, Any]],
    max_chars: int = 3800,
) -> str:
    """Compact digest for Telegram / email preview; respects Telegram ~4096 limit."""
    head = f"🧠 AI Brief {report_date.isoformat()}\n\n"
    if not ranked:
        return head + "_No items ranked today._\n"

    parts: list[str] = [head]
    for i, item in enumerate(ranked, start=1):
        title = str(item.get("title", "")).strip()
        source = str(item.get("source", "")).strip() or "—"
        reason = str(item.get("reason", "")).strip()
        score = item.get("score", "")
        verdict = str(item.get("verdict", "")).strip()
        link = str(item.get("link", "")).strip()
        block = (
            f"{i}. {title}\n"
            f"   Src: {source} | {score}/10 | {verdict}\n"
            f"   {reason}\n"
            f"   {link}\n\n"
        )
        parts.append(block)

    text = "".join(parts).rstrip() + "\n"
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20].rstrip() + "\n…(truncated)\n"
