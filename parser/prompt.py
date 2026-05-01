"""Prompt templates used by Claude parser."""

SYSTEM_PROMPT = (
    "You are a web content extraction assistant.\n"
    "Your job is to analyze cleaned HTML content and return a structured JSON object.\n"
    "Always respond with valid JSON only. No explanation, no markdown fences."
)

USER_PROMPT_TEMPLATE = """
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
""".strip()

STRICT_JSON_REMINDER = (
    "Your previous output was not valid JSON.\n"
    "Respond again with only one valid JSON object matching the exact schema.\n"
    "Do not include markdown code fences or any explanation."
)
