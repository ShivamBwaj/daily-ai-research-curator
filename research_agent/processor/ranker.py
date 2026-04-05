"""Rank and select top items using Google Gemini API (google-genai SDK)."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from google import genai
from google.genai import types

from utils.config import Config

logger = logging.getLogger(__name__)

MAX_RETRIES = 4
TOP_N = 5
# Keep prompts small to avoid TPM limits (truncate summaries, cap how many items we send).
MAX_ITEMS_FOR_LLM = 35
MAX_SUMMARY_CHARS = 400

SYSTEM_PROMPT = """You are an expert AI research assistant.

User interests:
- AI agents
- LLM systems
- RAG architectures

You will receive a JSON array of items. Each item has: title, summary, link, source.

Task:
1. Select the top 5 most important items.
2. For each item:
   - Explain why it matters (max 2 lines).
   - Give a score (1-10).
   - Verdict: READ or SKIP.

Return valid JSON only. Prefer this object form (no markdown fences):
{"items":[{"title":"","source":"","reason":"","score":0,"verdict":"","link":""}]}

If you must return a bare array instead, it must be:
[{"title":"","source":"","reason":"","score":0,"verdict":"","link":""}, ...]

Fields: copy title, source, link from the chosen input items. "reason" is your explanation. "score" is integer 1-10. "verdict" is exactly "READ" or "SKIP".
"""


def _compact_for_llm(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for it in items[:MAX_ITEMS_FOR_LLM]:
        summary = str(it.get("summary", "") or "")
        if len(summary) > MAX_SUMMARY_CHARS:
            summary = summary[: MAX_SUMMARY_CHARS - 1] + "…"
        out.append(
            {
                "title": str(it.get("title", "")).strip(),
                "summary": summary,
                "link": str(it.get("link", "")).strip(),
                "source": str(it.get("source", "")).strip(),
            }
        )
    return out


def _extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return None
    return None


def _extract_json_array(text: str) -> list[Any] | None:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            return None
    return None


def _validate_items(items: Any) -> list[dict[str, Any]] | None:
    if not isinstance(items, list):
        return None
    cleaned: list[dict[str, Any]] = []
    for it in items[:TOP_N]:
        if not isinstance(it, dict):
            continue
        title = str(it.get("title", "")).strip()
        link = str(it.get("link", "")).strip()
        reason = str(it.get("reason", "")).strip()
        source = str(it.get("source", "")).strip()
        verdict = str(it.get("verdict", "")).strip().upper()
        score_raw = it.get("score", 0)
        try:
            score = int(score_raw)
        except (TypeError, ValueError):
            score = 0
        if verdict not in ("READ", "SKIP"):
            verdict = "SKIP"
        if not title or not link:
            continue
        score = max(1, min(10, score))
        cleaned.append(
            {
                "title": title,
                "source": source or "—",
                "reason": reason,
                "score": score,
                "verdict": verdict,
                "link": link,
            }
        )
    if not cleaned:
        return None
    return cleaned


def _parse_ranking_response(raw: str) -> list[dict[str, Any]] | None:
    obj = _extract_json_object(raw)
    if obj:
        items = obj.get("items")
        validated = _validate_items(items)
        if validated:
            return validated[:TOP_N]
    arr = _extract_json_array(raw)
    if arr is not None:
        validated = _validate_items(arr)
        if validated:
            return validated[:TOP_N]
    return None


def rank_items(config: Config, normalized_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return top ranked items with reason, score, verdict; [] on total failure."""
    if not config.google_api_key:
        logger.error(
            "No API key: set GEMINI_API_KEY or GOOGLE_API_KEY for Gemini ranking."
        )
        return []

    if not normalized_items:
        logger.warning("No items to rank.")
        return []

    compact = _compact_for_llm(normalized_items)
    user_content = "Items to rank:\n" + json.dumps(compact, ensure_ascii=False)

    client = genai.Client(api_key=config.google_api_key)
    gen_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.3,
        response_mime_type="application/json",
        max_output_tokens=8192,
    )

    last_err: str | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=config.gemini_model,
                contents=user_content,
                config=gen_config,
            )
            raw = (response.text or "").strip()
            parsed = _parse_ranking_response(raw)
            if parsed:
                return parsed

            last_err = "Could not parse or validate JSON from model output."
            logger.warning("%s Snippet: %s", last_err, raw[:500])
            time.sleep(1.5 * (attempt + 1))
        except Exception as e:
            last_err = str(e)
            logger.exception("Gemini ranking attempt %s failed: %s", attempt + 1, e)
            time.sleep(1.5 * (attempt + 1))

    logger.error("Ranking failed after retries: %s", last_err)
    return []


# --- Groq (OpenAI-compatible) — disabled; was hitting low TPM limits on large prompts. ---
# from openai import OpenAI
#
# def rank_items_groq(config, normalized_items):
#     client = OpenAI(api_key=config.groq_api_key, base_url=config.groq_base_url)
#     resp = client.chat.completions.create(
#         model=config.groq_model,
#         messages=[...],
#         response_format={"type": "json_object"},
#     )
#     ...
