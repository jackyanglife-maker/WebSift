# AGENTS.md

This document is the working contract for AI coding agents collaborating on WebSift.

## Mission

Build WebSift into a reliable local web-content extraction tool with phased delivery, strict module boundaries, and reproducible behavior.

Primary source of truth for roadmap: `WebSift_Development_Guide.md`.

## Current Ground Truth (Do Not Hallucinate)

Implemented:

- FastAPI app skeleton in `main.py`
- Env-based config in `config.py`
- SQLAlchemy setup and models in `database/`
- Basic Jinja templates in `templates/`
- Crawler modules:
  - `crawler/cleaner.py` implemented
  - `crawler/fetcher.py` implemented (httpx + fallback decision)
  - `crawler/browser.py` exists as a stub (no real Playwright rendering yet)
- Manual crawler test script: `test_crawler.py`

Not implemented yet:

- parser (`parser/prompt.py`, `parser/llm_parser.py`)
- API routes (`api/routes_single.py`, `api/routes_batch.py`)
- orchestration tasks (`tasks/single_task.py`, `tasks/batch_task.py`)
- export modules (`exports/*.py`)
- full HTMX user flow

## Non-Negotiable Development Rules

1. Phase discipline

- Work strictly phase-by-phase.
- Do not implement future-phase features early.
- Verify current phase exit criteria before proceeding.

2. Architecture boundaries

- Crawler logic stays in `crawler/`.
- LLM logic stays in `parser/`.
- Workflow orchestration stays in `tasks/`.
- API routes remain thin and delegate to tasks/modules.
- DB access uses SQLAlchemy sessions only.

3. Reliability constraints

- Wrap all external calls (`httpx`, Playwright, Anthropic) with error handling.
- Never hardcode keys or secrets.
- Read runtime settings only from `config.py`.
- Preserve `updated_at` semantics on status changes.

4. Code quality

- Add type hints on all function signatures.
- Keep functions focused and small.
- Prefer explicit dataclasses for structured return values where useful.
- Avoid introducing framework complexity not in guide.

## Environment Expectations

- Python: 3.9+ (current workspace uses 3.9)
- Recommended local env:
  - `python3 -m venv .venv`
  - `.venv/bin/pip install -r requirements.txt`
- App start:
  - `.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000`

## Working Method For Future Agents

When asked to continue development:

1. Read `WebSift_Development_Guide.md` and this file.
2. Identify the active phase and its exit criteria.
3. Implement only files required by that phase.
4. Run the smallest meaningful verification:
   - module import checks
   - focused script run
   - API smoke test if route changes
5. Report:
   - what changed
   - what was validated
   - what remains in the current phase

## Phase-by-Phase Completion Checklist

Before declaring any phase done, ensure:

- Required files exist and are wired
- No obvious lint/type/runtime errors in changed modules
- Manual run command for that phase succeeds
- Output matches documented exit criteria

## Known Gaps and Priorities

Immediate priority:

- Finish Playwright fallback implementation in `crawler/browser.py`
- Re-validate Phase 2 against multiple target URLs, including JS-heavy page

After that:

- Move to Phase 3 (`parser/`) and implement JSON-robust Claude parsing with one retry strategy

## Agent Safety Notes

- Never commit `.env` or secrets.
- Never delete existing user data files unless explicitly requested.
- Do not perform destructive git actions.
- If repository state appears unexpectedly modified by outside processes, stop and ask user how to proceed.

## Definition of Good Progress

A change is good only if it is:

- phase-correct,
- runnable,
- testable with a concrete command,
- and easy for the next agent/human to continue.
