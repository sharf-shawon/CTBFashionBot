"""Text formatting utilities for Telegram HTML mode."""

import re


def markdown_to_html(text: str) -> str:
    """
    Convert Markdown formatting to HTML for Telegram.

    Supports:
    - **bold** -> <b>bold</b>
    - *italic* -> <i>italic</i>
    - `code` -> <code>code</code>
    """
    if not text:
        return text

    # Escape existing HTML entities to prevent double-escaping
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    # Convert **bold** to <b>bold</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    # Convert *italic* to <i>italic</i> (but not within **bold**)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)

    # Convert `code` to <code>code</code>
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)

    # Convert line breaks (markdown uses \n)
    # Already handled by Telegram

    return text


def strip_markdown(text: str) -> str:
    """Remove Markdown formatting entirely, keeping only text."""
    if not text:
        return text

    # Remove **bold**
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)

    # Remove *italic*
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)

    # Remove `code`
    text = re.sub(r"`(.+?)`", r"\1", text)

    return text
