# WebSift — Development Guide
> A personal AI-powered web content extraction assistant

---

## 1. Project Overview

**Name**: WebSift  
**Description**: A personal web content extraction assistant powered by AI. Fetch, parse, and structure web pages into clean, readable content — with support for batch processing, file link detection, and smart export.  
**Language**: Python  
**Target User**: Individual / Personal use  
**Deployment**: Local machine (localhost)

---

## 2. Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Web Framework | FastAPI | Async-first, lightweight, auto API docs |
| Frontend | Jinja2 + HTMX | Pure Python ecosystem, no JS framework needed |
| Database | SQLite + SQLAlchemy | Zero-ops, single file, perfect for personal tools |
| HTTP Crawler | httpx | Async HTTP client, faster than requests |
| HTML Parser | BeautifulSoup4 | Mature, stable HTML parsing |
| Dynamic Pages | Playwright | Headless browser fallback for JS-rendered pages |
| AI Parser | Anthropic Python SDK | Claude for content standardization |
| File Export | python-docx | Generate .docx exports |
| CSV/Excel Input | pandas | Parse uploaded batch files |
| Task Management | asyncio | Built-in async, no Celery needed |

---

## 3. Project File Structure

```
websift/
├── main.py                     # FastAPI app entry point
├── config.py                   # Settings, API keys, constants
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (never commit)
├── .env.example                # Template for .env
│
├── database/
│   ├── __init__.py
│   ├── db.py                   # SQLAlchemy engine & session
│   └── models.py               # ORM models: Task, Record, FileLink
│
├── crawler/
│   ├── __init__.py
│   ├── fetcher.py              # httpx-based HTTP fetcher
│   ├── browser.py              # Playwright fallback fetcher
│   └── cleaner.py              # HTML noise removal & pre-processing
│
├── parser/
│   ├── __init__.py
│   ├── prompt.py               # Claude prompt templates
│   └── llm_parser.py           # Anthropic SDK call & response handler
│
├── tasks/
│   ├── __init__.py
│   ├── single_task.py          # Single URL parsing workflow
│   └── batch_task.py           # Batch task manager with pause/resume
│
├── api/
│   ├── __init__.py
│   ├── routes_single.py        # POST /parse/single
│   └── routes_batch.py         # POST /batch, GET /batch/{id}, etc.
│
├── exports/
│   ├── docx_exporter.py        # Convert parsed content to .docx
│   └── txt_exporter.py         # Convert parsed content to .txt
│
├── templates/                  # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html              # Home / single URL input
│   ├── result.html             # Single result detail page
│   ├── batch.html              # Batch upload & task list page
│   └── batch_detail.html       # Batch task progress & record list
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── htmx.min.js
│
└── tmp/                        # Temporary export file storage (auto-cleaned)
```

---

## 4. Database Models

### 4.1 Task (批量任务)
```
id              INTEGER PRIMARY KEY
name            TEXT            # 任务名（文件名或用户自定义）
status          TEXT            # pending | running | paused | done | failed
total           INTEGER         # 总条数
completed       INTEGER         # 已完成条数
created_at      DATETIME
updated_at      DATETIME
```

### 4.2 Record (每条 URL 解析记录)
```
id              INTEGER PRIMARY KEY
task_id         INTEGER         # NULL = 单条解析
url             TEXT
status          TEXT            # pending | running | done | failed | invalid
page_status     TEXT            # valid | empty | invalid | file_only | content_only | mixed
title           TEXT
content         TEXT            # Markdown 格式正文
summary         TEXT
raw_html        TEXT            # 清洗后的 HTML（用于 debug）
error_msg       TEXT
created_at      DATETIME
updated_at      DATETIME
```

### 4.3 FileLink (文件链接)
```
id              INTEGER PRIMARY KEY
record_id       INTEGER
name            TEXT
url             TEXT
file_type       TEXT            # pdf | docx | xlsx | zip | other
```

---

## 5. Core Workflows

### 5.1 Single URL Parsing Flow
```
User Input URL
    │
    ▼
[fetcher.py] HTTP GET (httpx)
    │
    ├─ 404 / Connection Error ──► status=invalid, page_status=invalid
    │
    ▼
[cleaner.py] Remove <script>, <style>, ads, nav
    │
    ├─ Cleaned content is empty ──► page_status=empty
    │
    ▼
[llm_parser.py] Send to Claude with structured prompt
    │
    ▼
Claude returns JSON:
{
  "page_status": "content_only | file_only | mixed | empty | invalid",
  "title": "...",
  "content": "...(Markdown)...",
  "file_links": [{"name": "...", "url": "...", "type": "pdf"}],
  "summary": "..."
}
    │
    ▼
Save to DB (Record + FileLink)
    │
    ▼
Return result to frontend
```

### 5.2 Dynamic Page Fallback Strategy
```
httpx fetch
    │
    ├─ content length < 500 chars OR empty body
    │       │
    │       ▼
    │   [browser.py] Playwright headless fetch
    │       │
    │       ▼
    │   Return rendered HTML
    │
    └─ Normal content ──► Continue with httpx result
```

### 5.3 Batch Task Flow
```
Upload CSV/Excel
    │
    ▼
Parse file, extract URL column
    │
    ▼
Create Task record (status=pending)
Create N Record rows (status=pending)
    │
    ▼
User clicks "Start"
    │
    ▼
asyncio loop: process records one by one
    │
    ├─ Each record: run Single URL Parsing Flow
    ├─ Update record status in real-time
    ├─ Update task.completed counter
    │
    ├─ User clicks "Pause" ──► set task.status=paused, stop loop
    ├─ User clicks "Resume" ──► continue from next pending record
    │
    └─ All done ──► task.status=done
```

---

## 6. Claude Prompt Design

### 6.1 System Prompt
```
You are a web content extraction assistant. 
Your job is to analyze cleaned HTML content and return a structured JSON object.
Always respond with valid JSON only. No explanation, no markdown fences.
```

### 6.2 User Prompt Template
```
Analyze the following web page content extracted from: {url}

--- PAGE CONTENT START ---
{cleaned_text}
--- PAGE CONTENT END ---

Return a JSON object with these exact fields:
{{
  "page_status": one of ["valid", "empty", "invalid", "file_only", "content_only", "mixed"],
  "title": "page title or empty string",
  "content": "main body content in clean Markdown format, empty string if none",
  "file_links": [
    {{"name": "filename or link text", "url": "absolute URL", "type": "pdf|docx|xlsx|zip|other"}}
  ],
  "summary": "2-3 sentence summary of the content, empty string if no content"
}}

Rules:
- page_status="empty" if the page has no meaningful content
- page_status="invalid" if the content looks like an error page
- page_status="file_only" if there are only file download links, no readable text
- page_status="content_only" if there is text content but no file links
- page_status="mixed" if there is both text content and file links
- For file_links, only include actual downloadable files (pdf, docx, xlsx, zip, etc.), not regular page links
- Convert content to clean Markdown: use # for headings, - for lists, preserve tables
- file_links array should be empty [] if no files found
```

---

## 7. API Endpoints

### Single Parsing
```
POST /api/parse/single
Body: { "url": "https://..." }
Response: { "record_id": 1, "status": "done", ... }

GET /api/record/{record_id}
Response: full record with file_links

GET /api/record/{record_id}/export/txt
GET /api/record/{record_id}/export/docx
```

### Batch Tasks
```
POST /api/batch/upload
Body: multipart form with CSV/Excel file
Response: { "task_id": 1, "total": 50 }

POST /api/batch/{task_id}/start
POST /api/batch/{task_id}/pause
POST /api/batch/{task_id}/resume

GET /api/batch/{task_id}/status
Response: { "status": "running", "completed": 12, "total": 50, "progress": 24 }

GET /api/batch/{task_id}/records
Response: list of records with status

GET /api/record/{record_id}   (same as single)
```

---

## 8. Development Phases

> ⚠️ **Core Principle**: Each phase must be fully working and testable before moving to the next. Never skip ahead.

---

### Phase 1 — Project Skeleton & Database
**Goal**: Runnable FastAPI app with DB models, nothing more.

Tasks:
1. Create project folder structure
2. Write `requirements.txt`
3. Write `config.py` with settings class (read from .env)
4. Write `database/db.py` — SQLAlchemy engine + session factory
5. Write `database/models.py` — Task, Record, FileLink models
6. Write `main.py` — bare FastAPI app with DB init on startup
7. Write `templates/base.html` + `templates/index.html` (empty shell)
8. Run app, confirm DB file is created, tables exist

**Exit Criteria**: `uvicorn main:app` starts without error. DB tables exist.

---

### Phase 2 — Crawler Module
**Goal**: Given a URL, return cleaned text content.

Tasks:
1. Write `crawler/fetcher.py` — httpx async GET, handle 404/timeout/error
2. Write `crawler/cleaner.py` — remove script/style/nav tags, extract main text
3. Write `crawler/browser.py` — Playwright fetch (stub first, implement after fetcher works)
4. Add fallback logic: if cleaned text < 500 chars → use browser fetcher
5. Write a CLI test script `test_crawler.py` to manually test with 3-4 URLs

**Exit Criteria**: Run `python test_crawler.py https://example.com` returns cleaned text.

---

### Phase 3 — LLM Parser Module
**Goal**: Send cleaned text to Claude, receive structured JSON back.

Tasks:
1. Write `parser/prompt.py` — system prompt + user prompt template as constants
2. Write `parser/llm_parser.py` — call Anthropic SDK, parse JSON response
3. Add error handling: JSON parse failure → retry once with stricter prompt
4. Write `test_parser.py` — test with sample cleaned HTML strings

**Exit Criteria**: `python test_parser.py` returns valid structured dict for 3 test cases.

---

### Phase 4 — Single URL Parsing API
**Goal**: Full end-to-end single URL parse via API, result saved to DB.

Tasks:
1. Write `tasks/single_task.py` — orchestrate fetcher → cleaner → llm_parser → save to DB
2. Write `api/routes_single.py` — POST /api/parse/single endpoint
3. Register route in `main.py`
4. Test with curl or browser: POST a URL, check DB record is saved
5. Write GET /api/record/{id} endpoint to retrieve result

**Exit Criteria**: POST a URL → DB record created → GET record returns full data.

---

### Phase 5 — Frontend: Single Parse UI
**Goal**: User can type a URL in a form, see results on screen.

Tasks:
1. Design `templates/index.html` — URL input form with HTMX POST
2. Design `templates/result.html` — show title, content, file links, summary
3. Add route `GET /` in main.py to serve index.html
4. Add route `GET /record/{id}` to serve result.html
5. Wire HTMX: form submits → server returns result partial → render inline
6. Add basic CSS in `static/css/style.css`

**Exit Criteria**: Open browser → enter URL → see parsed result without page reload.

---

### Phase 6 — Export: TXT and DOCX
**Goal**: User can download parsed content as .txt or .docx.

Tasks:
1. Write `exports/txt_exporter.py` — format content + file links as plain text
2. Write `exports/docx_exporter.py` — format content as proper Word document
   - Use Heading styles for Markdown headings
   - Use bullet lists for Markdown lists
   - Append file links section at end
3. Write GET /api/record/{id}/export/txt and /export/docx endpoints
4. Add download buttons to result.html

**Exit Criteria**: Click download → valid .txt or .docx file is downloaded.

---

### Phase 7 — Batch Upload & Task Management
**Goal**: Upload CSV/Excel, create batch task, records visible in list.

Tasks:
1. Write `api/routes_batch.py` — POST /api/batch/upload, parse file with pandas
2. Validate URL column exists in uploaded file
3. Create Task + all pending Records in DB
4. Write `GET /batch/{task_id}` route + `templates/batch_detail.html`
5. Show record list with status badges (pending / running / done / failed)

**Exit Criteria**: Upload CSV → task page shows all URLs with "pending" status.

---

### Phase 8 — Batch Processing: Start / Pause / Resume
**Goal**: Batch task runs record by record, can be paused and resumed.

Tasks:
1. Write `tasks/batch_task.py` — asyncio loop over pending records
2. Implement pause flag: store in-memory dict `{task_id: "running"|"paused"}`
3. Write POST /api/batch/{task_id}/start — kicks off asyncio task
4. Write POST /api/batch/{task_id}/pause — sets pause flag
5. Write POST /api/batch/{task_id}/resume — clears flag, resumes from next pending
6. Write GET /api/batch/{task_id}/status — returns progress numbers
7. Add HTMX polling to batch_detail.html — refresh progress every 3 seconds
8. Disable "View" link for records with status != "done"

**Exit Criteria**: Start → watch progress update live → Pause → Resume → all complete.

---

### Phase 9 — Error Handling & Edge Cases
**Goal**: App handles all error cases gracefully without crashing.

Tasks:
1. Handle: URL unreachable, DNS failure, timeout → record status=failed, error saved
2. Handle: Claude API error / rate limit → retry once, then mark failed
3. Handle: Malformed JSON from Claude → retry with stricter prompt
4. Handle: Empty file upload / wrong column names → friendly error message
5. Add loading indicators on frontend during parsing
6. Add error display on result page if record.status == "failed"

**Exit Criteria**: Bad URL, bad file, API error — all show user-friendly messages.

---

### Phase 10 — Polish & Final Testing
**Goal**: Stable, usable personal tool.

Tasks:
1. Clean up CSS, ensure responsive layout
2. Add page titles and navigation
3. Auto-clean tmp/ folder on startup (delete exports older than 1 hour)
4. Test full workflow: single URL, batch CSV, pause/resume, export
5. Write brief README.md with setup instructions

**Exit Criteria**: Full end-to-end test passes. App is usable as a daily personal tool.

---

## 9. Development Constraints

These rules must be followed throughout all phases to minimize bugs and LLM hallucination when using Cursor.

### 9.1 Code Quality Rules
- **One file, one responsibility** — never put crawler logic in API routes
- **Never hardcode API keys** — always read from `.env` via `config.py`
- **All DB operations through SQLAlchemy sessions** — never use raw SQL strings
- **All external calls (httpx, Playwright, Anthropic) must have try/except** — no unhandled exceptions
- **Functions must be small** — max ~30 lines per function. Split if larger.
- **Type hints on all function signatures** — helps Cursor understand intent

### 9.2 LLM / Claude API Rules
- **Always ask Claude for JSON only** — system prompt must say "respond with valid JSON only"
- **Always validate Claude's JSON response** with `json.loads()` in a try/except
- **Retry once on JSON parse failure** — do not retry more than once (cost control)
- **Pass only cleaned text to Claude** — never pass raw HTML (token waste + hallucination risk)
- **Cap input text at 8000 characters** — truncate cleaned text if longer before sending
- **Log Claude input/output during development** — helps debug prompt issues quickly

### 9.3 Async Rules
- **FastAPI routes that call crawler or Claude must be `async def`**
- **Use `asyncio.create_task()` for batch processing** — do not block the request thread
- **Pause/resume state lives in memory dict** — acceptable for personal tool, note this in code
- **Do not run Playwright in same event loop as FastAPI** — use `asyncio.to_thread()` wrapper

### 9.4 Database Rules
- **Always close DB sessions** — use `with` context manager or FastAPI dependency injection
- **Add DB indexes on**: `record.task_id`, `record.status`, `task.status`
- **Never delete records** — use status flags instead
- **Use `updated_at` timestamps** — update on every status change

### 9.5 Frontend / HTMX Rules
- **Each HTMX partial response is a standalone HTML fragment** — no full page in partial
- **Progress polling uses `hx-trigger="every 3s"`** — stop polling when status=done/paused
- **File download links open in new tab** — use `target="_blank"`
- **Disable action buttons during processing** — prevent double-submit

### 9.6 Cursor Workflow Rules
- **Implement one Phase at a time** — do not ask Cursor to implement multiple phases together
- **Write the test first** — before asking Cursor to implement a module, describe what the test should verify
- **Review generated code before running** — check imports, function signatures, error handling
- **Commit working code after each Phase** — use git to checkpoint progress
- **If Cursor output is over 200 lines for one file** — ask it to split into smaller functions

---

## 10. Environment Setup

### 10.1 requirements.txt
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
jinja2==3.1.3
python-multipart==0.0.9
httpx==0.27.0
beautifulsoup4==4.12.3
playwright==1.44.0
anthropic==0.25.0
sqlalchemy==2.0.30
pandas==2.2.2
openpyxl==3.1.2
python-docx==1.1.2
python-dotenv==1.0.1
```

### 10.2 .env.example
```
ANTHROPIC_API_KEY=your_key_here
DATABASE_URL=sqlite:///./websift.db
MAX_CONTENT_LENGTH=8000
REQUEST_TIMEOUT=30
PLAYWRIGHT_FALLBACK_THRESHOLD=500
```

### 10.3 First Run Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Start development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 11. Key Implementation Notes

### HTML Cleaning Strategy (cleaner.py)
Remove these tags entirely: `script, style, nav, header, footer, aside, iframe, noscript`  
Keep these: `p, h1-h6, ul, ol, li, table, tr, td, th, a, strong, em, blockquote`  
For `<a>` tags: keep href only if it ends with `.pdf .docx .xlsx .zip .pptx .rar`  
Convert to plain text after cleaning: use `soup.get_text(separator='\n', strip=True)`

### DOCX Export Strategy (docx_exporter.py)
Parse Markdown content line by line:
- Lines starting with `# ` → Heading 1
- Lines starting with `## ` → Heading 2  
- Lines starting with `- ` or `* ` → Bullet list item
- Other lines → Normal paragraph
- Append "Downloadable Files" section at end with hyperlinks for each FileLink

### Batch File Column Detection (routes_batch.py)
Accept these column names as URL column (case-insensitive):  
`url, link, address, webpage, website, href`  
If none found → return error: "Could not find a URL column. Please use column name: url"

---

*Document Version: 1.0 — Generated for WebSift initial development*
