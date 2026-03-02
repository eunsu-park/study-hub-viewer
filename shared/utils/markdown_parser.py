"""Markdown parsing utilities with syntax highlighting and LaTeX support."""
import os
import re
from functools import lru_cache

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.toc import TocExtension

# LaTeX protection: prevent markdown from mangling $...$ and $$...$$ blocks
_LATEX_PLACEHOLDER = "\x00LATEX%d\x00"


def _protect_latex(content: str) -> tuple[str, list[str]]:
    """Extract LaTeX blocks and replace with placeholders before markdown processing."""
    blocks = []

    # First, protect fenced code blocks from LaTeX extraction
    code_blocks = []
    def save_code(m):
        code_blocks.append(m.group(0))
        return f"\x00CODE{len(code_blocks) - 1}\x00"
    content = re.sub(r'```[\s\S]*?```', save_code, content)

    # Protect $$...$$ (display math) first
    def save_display(m):
        blocks.append(m.group(0))
        return _LATEX_PLACEHOLDER % (len(blocks) - 1)
    content = re.sub(r'\$\$[\s\S]+?\$\$', save_display, content)

    # Protect $...$ (inline math)
    def save_inline(m):
        blocks.append(m.group(0))
        return _LATEX_PLACEHOLDER % (len(blocks) - 1)
    content = re.sub(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', save_inline, content)

    # Restore code blocks
    for i, code in enumerate(code_blocks):
        content = content.replace(f"\x00CODE{i}\x00", code)

    return content, blocks


def _restore_latex(html: str, blocks: list[str]) -> str:
    """Restore LaTeX blocks from placeholders after markdown processing."""
    for i, block in enumerate(blocks):
        html = html.replace(_LATEX_PLACEHOLDER % i, block)
    return html


def parse_markdown(content: str) -> dict:
    """
    Parse Markdown content to HTML with syntax highlighting and LaTeX support.

    Returns:
        dict: {
            "html": rendered HTML,
            "toc": table of contents HTML,
            "title": extracted title (first H1)
        }
    """
    # Extract title before any processing
    title = extract_title(content)

    # Protect LaTeX from markdown processing
    content, latex_blocks = _protect_latex(content)

    md = markdown.Markdown(
        extensions=[
            "fenced_code",
            "tables",
            "toc",
            CodeHiliteExtension(
                css_class="highlight",
                linenums=False,
                guess_lang=True,
            ),
            TableExtension(),
            TocExtension(
                permalink=True,
                permalink_class="header-link",
                toc_depth="2-4",
            ),
        ]
    )

    html = md.convert(content)
    toc = md.toc

    # Restore LaTeX blocks
    html = _restore_latex(html, latex_blocks)

    return {
        "html": html,
        "toc": toc,
        "title": title,
    }


def extract_title(content: str) -> str:
    """Extract the first H1 heading from Markdown content."""
    # Match # heading at the start of a line
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return ""


_CACHE_SIZE = 64


def parse_markdown_cached(filepath: str) -> dict:
    """Cached version of parse_markdown. Cache invalidated by file mtime."""
    mtime = os.path.getmtime(filepath)
    return _parse_markdown_cached(filepath, mtime)


@lru_cache(maxsize=_CACHE_SIZE)
def _parse_markdown_cached(filepath: str, mtime: float) -> dict:
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    return parse_markdown(content)


def estimate_reading_time(content: str) -> int:
    """Estimate reading time in minutes (~200 wpm text, ~100 wpm code)."""
    code_blocks = re.findall(r'```[\s\S]*?```', content)
    text = re.sub(r'```[\s\S]*?```', '', content)
    text_words = len(text.split())
    code_words = sum(len(b.split()) for b in code_blocks)
    minutes = text_words / 200 + code_words / 100
    return max(1, round(minutes))


def extract_excerpt(content: str, max_length: int = 200) -> str:
    """Extract a plain text excerpt from Markdown content."""
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", content)
    # Remove inline code
    text = re.sub(r"`[^`]+`", "", text)
    # Remove headers
    text = re.sub(r"^#+\s+.+$", "", text, flags=re.MULTILINE)
    # Remove links but keep text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove images
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    # Remove bold/italic markers
    text = re.sub(r"[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", text)
    # Remove extra whitespace
    text = " ".join(text.split())

    if len(text) > max_length:
        return text[:max_length].rsplit(" ", 1)[0] + "..."
    return text
