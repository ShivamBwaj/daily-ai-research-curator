# Daily AI Research Curator Agent

Runs on a schedule (GitHub Actions) or locally: pulls recent **arXiv** papers (cs.AI, cs.LG via the Atom API) and **Google News** RSS, ranks the top five items with **Google Gemini** (`google-genai`, default **`gemini-2.5-flash`**), writes `reports/YYYY-MM-DD.md`, emails the **full** Markdown report, and sends a **short** digest to **Telegram**.

Ranking sends a **compact** payload (truncated summaries, max 35 items) to stay under token-per-minute limits.

## Requirements

- Python 3.11+
- [Google AI Studio API key](https://aistudio.google.com/apikey) — set **`GEMINI_API_KEY`** (recommended) or **`GOOGLE_API_KEY`**
- Optional: Gmail (or other SMTP) for email; Telegram bot for push

## Setup (local)

```bash
cd research_agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Yes (for ranking) | Same key; either name works |
| `GEMINI_MODEL` | No | Default `gemini-2.5-flash` |
| `EMAIL_USER` | No | SMTP login (e.g. Gmail address) |
| `EMAIL_PASS` | No | App password (Gmail: [App Passwords](https://support.google.com/accounts/answer/185833)) |
| `EMAIL_TO` | No | Recipient address |
| `EMAIL_SMTP_HOST` | No | Default `smtp.gmail.com` |
| `EMAIL_SMTP_PORT` | No | Default `587` |
| `TELEGRAM_TOKEN` | No | From [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | No | Target chat ID |

If email or Telegram variables are missing, that channel is skipped (no crash).

## Run locally

```bash
python main.py --run-once
```

Same as `python main.py` (default is a single run).

Logs: console (INFO+) and `logs/research_agent.log`.

## GitHub Actions (daily cloud run)

- Workflow schedule: **`30 2 * * *`** (UTC) = **8:00 AM IST** (UTC+5:30).
- Manual run: **Actions** → **Daily AI Research Curator** → **Run workflow**.

### Repository layout and workflow file

GitHub only loads workflows from **`.github/workflows/` at the repository root**.

- **`research_agent/.github/workflows/daily.yml`** — use when this folder is the repo root (clone only `research_agent`).
- **Parent-folder `.github/workflows/daily.yml`** — if the repo root contains `research_agent/` as a subfolder, use the workflow at the parent (with `working-directory: research_agent`). **Do not enable both** in the same repo or the job will run twice.

### Secrets

In the GitHub repo: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

| Secret | Purpose |
|--------|---------|
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Required for ranking (either; same value) |
| `GEMINI_MODEL` | Optional; default `gemini-2.5-flash` |
| `EMAIL_USER` | SMTP user |
| `EMAIL_PASS` | SMTP password / app password |
| `EMAIL_TO` | Recipient |
| `EMAIL_SMTP_HOST` | Optional; omit for Gmail defaults |
| `EMAIL_SMTP_PORT` | Optional |
| `TELEGRAM_TOKEN` | Bot token |
| `TELEGRAM_CHAT_ID` | Chat id |

Workflow passes them as environment variables; the app does not read `.env` on Actions unless you add a step to create it.

### Note on scheduled workflows

GitHub may delay scheduled runs on free repos by a few minutes. `workflow_dispatch` is useful for testing right after you add secrets.

## Example output (report)

```markdown
🧠 Daily AI Research Brief – 2026-04-05

## 1. Paper title

- **Source:** arXiv cs.LG
- **Why it matters:** …
- **Score:** 8/10
- **Verdict:** READ
- **Link:** https://…
```

Telegram receives a shorter compact digest of the same items.

## Project layout

```
research_agent/
  main.py
  fetchers/
    arxiv.py
    news.py
  processor/
    ranker.py
  delivery/
    email.py
    telegram.py
  utils/
    formatter.py
    logger.py
    config.py
  reports/
  .github/workflows/daily.yml
  .env.example
  requirements.txt
  README.md
```

## Behavior

- Empty feeds or API errors are logged; the run continues where possible.
- Gemini responses are validated as JSON (`response_mime_type=application/json`); transient failures are retried.
- Email uses STARTTLS on the configured SMTP port (Gmail: 587).
- Telegram respects the ~4096 character limit (splitting if needed).
