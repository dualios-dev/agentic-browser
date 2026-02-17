"""HTML → clean Markdown sanitizer.

Strips hidden elements, scripts, iframes, zero-width characters,
and other potentially dangerous or irrelevant content before
converting to clean Markdown for AI consumption.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Comment, Tag
from markdownify import markdownify

# Zero-width and invisible Unicode characters
_ZERO_WIDTH_RE = re.compile(
    "[\u200b\u200c\u200d\u200e\u200f\u2060\u2061\u2062\u2063\u2064"
    "\ufeff\u00ad\u034f\u061c\u180e\u2800]"
)

# Default tags to strip entirely (including their content)
_DEFAULT_STRIP_TAGS = {
    "script", "style", "noscript", "iframe", "object", "embed", "svg",
    "link", "meta",
}

# CSS properties/values that indicate hidden elements
_HIDDEN_PATTERNS = [
    re.compile(r"display\s*:\s*none", re.IGNORECASE),
    re.compile(r"visibility\s*:\s*hidden", re.IGNORECASE),
    re.compile(r"opacity\s*:\s*0(?:[;\s]|$)", re.IGNORECASE),
    re.compile(r"font-size\s*:\s*0", re.IGNORECASE),
    re.compile(r"width\s*:\s*0", re.IGNORECASE),
    re.compile(r"height\s*:\s*0", re.IGNORECASE),
    re.compile(r"overflow\s*:\s*hidden", re.IGNORECASE),
    re.compile(r"position\s*:\s*absolute.*?left\s*:\s*-\d{4,}", re.IGNORECASE | re.DOTALL),
]

# Attributes that might contain hidden text injections
_SUSPICIOUS_ATTRS = {"aria-hidden", "data-prompt", "data-instruction"}


def _is_hidden(tag: Tag) -> bool:
    """Check if an HTML element is visually hidden."""
    if not hasattr(tag, 'attrs') or tag.attrs is None:
        return False
    style = tag.get("style", "")
    if isinstance(style, str):
        for pattern in _HIDDEN_PATTERNS:
            if pattern.search(style):
                return True

    # Check aria-hidden
    if tag.get("aria-hidden") == "true":
        return True

    # Check class names that typically hide content
    classes = tag.get("class", [])
    if isinstance(classes, list):
        class_str = " ".join(classes).lower()
        if any(h in class_str for h in ["hidden", "sr-only", "visually-hidden", "offscreen"]):
            return True

    return False


def _remove_hidden_elements(soup: BeautifulSoup) -> None:
    """Remove all visually hidden elements from the DOM."""
    for tag in soup.find_all(True):
        if isinstance(tag, Tag) and _is_hidden(tag):
            tag.decompose()


def _remove_comments(soup: BeautifulSoup) -> None:
    """Remove all HTML comments."""
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()


def _remove_strip_tags(soup: BeautifulSoup, tags: set[str] | None = None) -> None:
    """Remove specified tags and all their content."""
    strip = tags or _DEFAULT_STRIP_TAGS
    for tag_name in strip:
        for tag in soup.find_all(tag_name):
            tag.decompose()


def _remove_suspicious_attrs(soup: BeautifulSoup) -> None:
    """Remove attributes that might contain hidden prompt injections."""
    for tag in soup.find_all(True):
        if not isinstance(tag, Tag):
            continue
        for attr in list(tag.attrs.keys()):
            if attr.startswith("data-") or attr in _SUSPICIOUS_ATTRS:
                del tag[attr]


def _strip_zero_width(text: str) -> str:
    """Remove zero-width and invisible Unicode characters."""
    return _ZERO_WIDTH_RE.sub("", text)


def _collapse_whitespace(text: str) -> str:
    """Collapse excessive whitespace and blank lines."""
    # Collapse multiple blank lines to maximum two
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    # Remove trailing whitespace on each line
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    return text.strip()


def sanitize_html(
    html: str,
    max_length: int = 50000,
    strip_tags: set[str] | None = None,
    strip_hidden: bool = True,
    strip_zero_width: bool = True,
    config: dict[str, Any] | None = None,
) -> str:
    """Convert raw HTML to clean, safe Markdown.

    Pipeline:
    1. Parse HTML
    2. Remove dangerous tags (script, style, iframe, etc.)
    3. Remove HTML comments
    4. Remove hidden elements (display:none, aria-hidden, etc.)
    5. Remove suspicious data attributes
    6. Convert to Markdown
    7. Strip zero-width characters
    8. Collapse whitespace
    9. Truncate to max length

    Args:
        html: Raw HTML string.
        max_length: Maximum output length in characters.
        strip_tags: Tags to remove (defaults to scripts, styles, etc.).
        strip_hidden: Whether to remove hidden elements.
        strip_zero_width: Whether to strip zero-width chars.
        config: Optional sanitizer config dict.

    Returns:
        Clean Markdown string safe for AI consumption.
    """
    cfg = config or {}
    max_length = cfg.get("max_length", max_length)

    soup = BeautifulSoup(html, "html.parser")

    # 1. Remove dangerous tags
    tags_to_strip = strip_tags or set(cfg.get("strip_tags", _DEFAULT_STRIP_TAGS))
    _remove_strip_tags(soup, tags_to_strip)

    # 2. Remove comments
    _remove_comments(soup)

    # 3. Remove hidden elements
    if cfg.get("strip_hidden", strip_hidden):
        _remove_hidden_elements(soup)

    # 4. Remove suspicious attributes
    _remove_suspicious_attrs(soup)

    # 5. Convert to markdown
    markdown = markdownify(str(soup), heading_style="ATX", strip=["img"])

    # 6. Strip zero-width characters
    if cfg.get("strip_zero_width", strip_zero_width):
        markdown = _strip_zero_width(markdown)

    # 7. Collapse whitespace
    markdown = _collapse_whitespace(markdown)

    # 8. Truncate
    if len(markdown) > max_length:
        markdown = markdown[:max_length] + "\n\n[... truncated]"

    return markdown


def extract_text_only(html: str) -> str:
    """Extract plain text from HTML, stripping all tags."""
    soup = BeautifulSoup(html, "html.parser")
    _remove_strip_tags(soup)
    return _strip_zero_width(soup.get_text(separator=" ", strip=True))
