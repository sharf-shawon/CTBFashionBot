"""Input sanitization utilities to protect against injection attacks."""

import re
from html import escape

# Maximum allowed lengths
MAX_MESSAGE_LENGTH = 2000
MAX_USER_ID_LENGTH = 20


def sanitize_message(text: str) -> str:
    """
    Sanitize user message text to prevent injection attacks.

    - Limits length to prevent bot abuse
    - Removes control characters
    - Escapes HTML entities
    - Strips leading/trailing whitespace
    """
    if not text:
        return ""

    # Limit length
    text = text[:MAX_MESSAGE_LENGTH]

    # Remove control characters (except newlines, tabs)
    text = "".join(char for char in text if char.isprintable() or char in "\n\t")

    # Escape HTML entities (defense in depth)
    text = escape(text)

    # Strip excessive whitespace
    text = text.strip()

    # Remove null bytes (can cause issues in some contexts)
    text = text.replace("\x00", "")

    return text


def sanitize_user_id(user_id_str: str) -> int | None:
    """
    Validate and sanitize user ID input.

    Returns the integer user ID if valid, None otherwise.
    """
    if not user_id_str:
        return None

    # Limit length
    user_id_str = user_id_str[:MAX_USER_ID_LENGTH]

    # Strip whitespace
    user_id_str = user_id_str.strip()

    # Check for negative sign (reject negative IDs)
    if user_id_str.startswith("-"):
        return None

    # Remove any non-digit characters
    user_id_str = re.sub(r"\D", "", user_id_str)

    if not user_id_str:
        return None

    try:
        user_id = int(user_id_str)
        # Telegram user IDs are positive integers
        if user_id <= 0:
            return None
        return user_id
    except (ValueError, OverflowError):
        return None


def sanitize_for_markdown(text: str) -> str:
    """
    Escape special Markdown characters to prevent parse errors.

    Used when displaying user-generated content in Markdown mode.
    """
    if not text:
        return ""

    # Escape Markdown special characters
    markdown_chars = [
        "_",
        "*",
        "[",
        "]",
        "(",
        ")",
        "~",
        "`",
        ">",
        "#",
        "+",
        "-",
        "=",
        "|",
        "{",
        "}",
        ".",
        "!",
    ]
    for char in markdown_chars:
        text = text.replace(char, f"\\{char}")

    return text


def is_suspicious_sql_pattern(text: str) -> bool:
    """
    Check if text contains suspicious SQL patterns.

    This is a defense-in-depth measure since we don't execute user input directly.
    Returns True if suspicious patterns are detected.
    """
    text_lower = text.lower()

    # Suspicious SQL keywords that shouldn't appear in natural language questions
    suspicious_patterns = [
        r";\s*drop\s+",
        r";\s*delete\s+",
        r";\s*update\s+",
        r";\s*insert\s+",
        r";\s*create\s+",
        r";\s*alter\s+",
        r";\s*truncate\s+",
        r"union\s+select",
        r"exec\s*\(",
        r"execute\s*\(",
        r"xp_cmdshell",
        r"<script",
        r"javascript:",
        r"onerror\s*=",
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, text_lower):
            return True

    return False
