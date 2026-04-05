"""Telegram delivery via Bot API (short digest)."""

from __future__ import annotations

import logging
from typing import Any

import requests

from utils.config import Config

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
MAX_MESSAGE_LEN = 4096


def send_telegram_message(config: Config, text: str) -> bool:
    """Send ``text`` if token and chat id are configured; otherwise no-op."""
    if not config.telegram_token or not config.telegram_chat_id:
        logger.debug("Telegram not configured; skipping send.")
        return False

    url = f"{TELEGRAM_API}/bot{config.telegram_token}/sendMessage"
    chunks: list[str] = []
    if len(text) <= MAX_MESSAGE_LEN:
        chunks = [text]
    else:
        parts = text.split("\n\n")
        buf = ""
        for p in parts:
            if len(buf) + len(p) + 2 <= MAX_MESSAGE_LEN:
                buf = f"{buf}\n\n{p}".strip() if buf else p
            else:
                if buf:
                    chunks.append(buf)
                buf = p
                while len(buf) > MAX_MESSAGE_LEN:
                    chunks.append(buf[: MAX_MESSAGE_LEN - 50] + "\n…(truncated)")
                    buf = buf[MAX_MESSAGE_LEN - 50 :]
        if buf:
            chunks.append(buf)

    ok = True
    for i, chunk in enumerate(chunks):
        payload: dict[str, Any] = {
            "chat_id": config.telegram_chat_id,
            "text": chunk,
            "disable_web_page_preview": True,
        }
        try:
            r = requests.post(url, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            if not data.get("ok"):
                logger.error("Telegram API error: %s", data)
                ok = False
        except requests.RequestException as e:
            logger.error("Telegram request failed (part %s): %s", i + 1, e)
            ok = False

    return ok
