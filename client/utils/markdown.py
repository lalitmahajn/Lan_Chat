"""Basic markdown -> HTML renderer for chat messages."""

from common.utils import markdown_to_html


def render_message_content(text: str) -> str:
    """Convert message text (basic markdown) to HTML for Qt rich text display."""
    html = markdown_to_html(text)
    # Wrap in styled div
    return f'<div style="font-family: Segoe UI, sans-serif; font-size: 13px;">{html}</div>'
