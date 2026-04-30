# WebSift

Personal AI-powered web content extraction assistant built with FastAPI.

## What This Project Is

WebSift extracts useful text content from web pages, prepares structured data for LLM parsing, and is designed to grow into a local-first tool that supports:

- Single URL parsing
- Batch URL processing from CSV/Excel
- Downloadable file link detection
- Export to TXT and DOCX

The long-term plan is documented in `WebSift_Development_Guide.md`.

## Current Implementation Status

Implemented now:

- Phase 1 complete:
  - FastAPI app bootstrapped in `main.py`
  - Config loading from env in `config.py`
  - SQLite + SQLAlchemy setup in `database/db.py`
  - ORM models in `database/models.py`
  - Base templates and static styles created
- Phase 2 core modules started:
  - `crawler/fetcher.py` (httpx fetch + fallback decision logic)
  - `crawler/cleaner.py` (HTML noise removal + text extraction)
  - `crawler/browser.py` (Playwright fallback stub, not fully implemented yet)
  - `test_crawler.py` (manual CLI test script)

Not implemented yet:

- Claude parser integration
- API routes for single/batch parsing
- Frontend interaction flow with HTMX
- Export endpoints and batch orchestration

## Tech Stack

- Python 3.9+
- FastAPI
- SQLAlchemy + SQLite
- httpx
- BeautifulSoup4
- Playwright (fallback path, pending full implementation)
- Anthropic SDK (planned phases)
- Jinja2 + HTMX (planned UI flow)

## Project Structure

```text
Websift/
├── main.py
├── config.py
├── requirements.txt
├── .env.example
├── database/
│   ├── __init__.py
│   ├── db.py
│   └── models.py
├── crawler/
│   ├── __init__.py
│   ├── fetcher.py
│   ├── cleaner.py
│   └── browser.py
├── api/
├── tasks/
├── parser/
├── exports/
├── templates/
│   ├── base.html
│   └── index.html
├── static/
│   └── css/
│       └── style.css
├── tmp/
├── test_crawler.py
└── WebSift_Development_Guide.md
```

## Quick Start

### 1) Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Prepare env file

```bash
cp .env.example .env
```

At this stage, only crawler + app skeleton are needed, but filling `ANTHROPIC_API_KEY` now avoids later setup interruption.

### 4) Run the app

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open: `http://127.0.0.1:8000`

## Database Notes

On startup, `main.py` calls `init_db()`, which creates:

- `tasks`
- `records`
- `file_links`

Database file location is controlled by `DATABASE_URL` in `.env` (default: `sqlite:///./websift.db`).

## Crawler Manual Testing

Run default test URLs:

```bash
python test_crawler.py
```

Run custom URL:

```bash
python test_crawler.py https://example.com
```

Output includes:

- request status (`ok` / `invalid`)
- source (`httpx` or `playwright`)
- cleaned text length
- text preview and error message (if any)

## Configuration Reference

From `config.py`:

- `ANTHROPIC_API_KEY`
- `DATABASE_URL`
- `MAX_CONTENT_LENGTH`
- `REQUEST_TIMEOUT`
- `PLAYWRIGHT_FALLBACK_THRESHOLD`

## Development Workflow Rules

Follow these rules from `WebSift_Development_Guide.md`:

- Implement one phase at a time
- Ensure each phase is runnable before moving on
- Keep responsibilities separated by module
- Wrap external calls in try/except
- Keep functions small and typed

## Next Recommended Step

Continue Phase 2 by replacing `crawler/browser.py` stub with real Playwright rendering logic and validate fallback behavior on JS-heavy pages.

# WebSift
