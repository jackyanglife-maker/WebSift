"""HTML cleaning helpers for extracting readable page text."""

from bs4 import BeautifulSoup

REMOVE_TAGS = (
    "script",
    "style",
    "nav",
    "header",
    "footer",
    "aside",
    "iframe",
    "noscript",
)


def clean_html(html: str) -> str:
    """Remove noisy tags and return normalized plain text."""
    if not html.strip():
        return ""

    soup = BeautifulSoup(html, "html.parser")
    for tag in REMOVE_TAGS:
        for node in soup.find_all(tag):
            node.decompose()

    return soup.get_text(separator="\n", strip=True)
