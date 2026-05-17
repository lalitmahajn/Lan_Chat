"""Shared utilities for server and client."""

import re
from datetime import datetime, timezone


# ─── Basic Markdown -> HTML ───────────────────────────────────────────────────

def markdown_to_html(text: str) -> str:
    """Convert basic markdown to HTML.

    Supports:
        **bold** -> <b>bold</b>
        *italic* -> <i>italic</i>
        `code` -> <code>code</code>
        ```code blocks``` -> <pre><code>code blocks</code></pre>
    """
    if not text:
        return text

    # Escape HTML first
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    # Code blocks (``` ... ```) — must be before inline code
    text = re.sub(
        r"```(\w*)\n?(.*?)```",
        r"<pre><code>\2</code></pre>",
        text,
        flags=re.DOTALL,
    )

    # Inline code (`...`)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    # Bold (**...**)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    # Italic (*...*)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)

    # Newlines -> <br>
    text = text.replace("\n", "<br>")

    return text


# ─── Time Utilities ───────────────────────────────────────────────────────────

def utc_now() -> datetime:
    """Current UTC datetime."""
    return datetime.now(timezone.utc)


def format_timestamp(dt: datetime) -> str:
    """Format datetime for display: 'HH:MM' for today, 'Mon DD, HH:MM' otherwise."""
    now = datetime.now(timezone.utc)
    if dt.date() == now.date():
        return dt.strftime("%H:%M")
    return dt.strftime("%b %d, %H:%M")


def format_file_size(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


# ─── Validation ───────────────────────────────────────────────────────────────

def sanitize_filename(filename: str) -> str:
    """Remove unsafe characters from filename."""
    # Keep only alphanumeric, dots, hyphens, underscores, spaces
    sanitized = re.sub(r"[^\w\s\-.]", "", filename)
    # Collapse multiple spaces/dots
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized or "unnamed_file"
