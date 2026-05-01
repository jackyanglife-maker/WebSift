# WebSift

WebSift is a local FastAPI tool for extracting readable page content, structuring it with Claude, running batch jobs from CSV/Excel, and exporting results as TXT or DOCX.

## Current Status

The phased implementation in `WebSift_Development_Guide.md` is now covered end to end:

- single URL parsing with inline HTMX results
- batch upload from CSV/Excel with task detail page
- batch start / pause / resume processing
- Playwright fallback for JS-heavy pages
- Claude JSON parsing with retry on API failure and malformed JSON
- TXT and DOCX export endpoints
- error handling for bad URLs, bad files, and parser failures

## Stack

- Python 3.9+
- FastAPI
- Jinja2 + HTMX
- SQLAlchemy + SQLite
- httpx
- BeautifulSoup4
- Playwright
- Anthropic SDK
- pandas
- python-docx

## Quick Start

1. Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

3. Prepare environment variables:

```bash
cp .env.example .env
```

Set `ANTHROPIC_API_KEY` in `.env` if you want live parsing through Claude.

4. Start the app:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000`.

## Main Flows

### Single Parse

- open `/`
- submit one URL
- review parsed content, summary, detected file links
- export result as TXT or DOCX

### Batch Parse

- open `/batch`
- upload a CSV or Excel file with a URL column
- accepted URL column names: `url`, `link`, `address`, `webpage`, `website`, `href`
- open the generated task page
- start, pause, and resume processing

## Configuration

Environment variables loaded by `config.py`:

- `ANTHROPIC_API_KEY`
- `ANTHROPIC_MODEL`
- `DATABASE_URL`
- `MAX_CONTENT_LENGTH`
- `REQUEST_TIMEOUT`
- `PLAYWRIGHT_FALLBACK_THRESHOLD`

Defaults are defined in `.env.example`.

## Notes

- exported files are written to `tmp/`
- on startup, WebSift deletes export files in `tmp/` older than one hour
- batch runtime state is kept in memory, which is acceptable for this local personal tool

## Manual Checks

Crawler smoke test:

```bash
python test_crawler.py https://example.com
```

Parser smoke test without API key:

```bash
python test_parser.py
```

## Project Layout

```text
WebSift/
├── main.py
├── config.py
├── database/
├── crawler/
├── parser/
├── tasks/
├── api/
├── exports/
├── templates/
├── static/
├── tmp/
├── test_crawler.py
├── test_parser.py
└── WebSift_Development_Guide.md
```
