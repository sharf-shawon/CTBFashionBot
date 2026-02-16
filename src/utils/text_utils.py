import re
from collections.abc import Iterable

WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def truncate_to_words(text: str, max_words: int) -> str:
    if max_words <= 0:
        return ""
    words = WORD_RE.findall(text or "")
    if len(words) <= max_words:
        return text
    kept = words[:max_words]
    return " ".join(kept)


def normalize_name_set(values: Iterable[str]) -> set[str]:
    return {value.strip().lower() for value in values if value and value.strip()}


def normalize_csv_list(value: Iterable[str]) -> list[str]:
    return [item.strip() for item in value if item and item.strip()]
