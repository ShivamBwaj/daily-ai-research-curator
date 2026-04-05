"""Load configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"

load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
SMTP_DEFAULT_HOST = "smtp.gmail.com"
SMTP_DEFAULT_PORT = 587


@dataclass(frozen=True)
class Config:
    # Gemini / Google AI Studio — GEMINI_API_KEY (preferred in docs) or GOOGLE_API_KEY
    google_api_key: str
    gemini_model: str
    email_user: str | None
    email_pass: str | None
    email_to: str | None
    email_smtp_host: str
    email_smtp_port: int
    telegram_token: str | None
    telegram_chat_id: str | None


def load_config() -> Config:
    load_dotenv(PROJECT_ROOT / ".env")
    # Docs use GEMINI_API_KEY; support GOOGLE_API_KEY for the same key.
    api_key = (
        (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    )
    model = (
        os.getenv("GEMINI_MODEL") or os.getenv("GOOGLE_MODEL") or DEFAULT_GEMINI_MODEL
    ).strip()

    email_user = (os.getenv("EMAIL_USER") or "").strip() or None
    email_pass = (os.getenv("EMAIL_PASS") or "").strip() or None
    email_to = (os.getenv("EMAIL_TO") or "").strip() or None
    smtp_host = (os.getenv("EMAIL_SMTP_HOST") or SMTP_DEFAULT_HOST).strip()
    smtp_port_raw = (os.getenv("EMAIL_SMTP_PORT") or str(SMTP_DEFAULT_PORT)).strip()
    try:
        smtp_port = int(smtp_port_raw)
    except ValueError:
        smtp_port = SMTP_DEFAULT_PORT

    token = (os.getenv("TELEGRAM_TOKEN") or "").strip() or None
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip() or None

    return Config(
        google_api_key=api_key,
        gemini_model=model,
        email_user=email_user,
        email_pass=email_pass,
        email_to=email_to,
        email_smtp_host=smtp_host,
        email_smtp_port=smtp_port,
        telegram_token=token,
        telegram_chat_id=chat_id,
    )
