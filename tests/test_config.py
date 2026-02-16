"""Tests for configuration loading and defaults."""

from config.base import (
    CURRENCY_SYMBOL,
    DATABASE_ALLOWED_TABLES,
    DATABASE_EXCLUDED_COLUMNS,
    DATABASE_RESTRICTED_TABLES,
    LLM_MAX_RETRIES,
    PROFANITY_FILTER_ENABLED,
    RESPONSE_MAX_WORDS,
    SMALLTALK_ENABLED,
)


def test_currency_symbol_default():
    """Test that CURRENCY_SYMBOL has a default value."""
    assert CURRENCY_SYMBOL is not None
    assert isinstance(CURRENCY_SYMBOL, str)
    assert len(CURRENCY_SYMBOL) > 0


def test_currency_symbol_is_tk():
    """Test that CURRENCY_SYMBOL is set to 'Tk' from .env."""
    assert CURRENCY_SYMBOL == "Tk"


def test_config_defaults():
    """Test that config defaults are set correctly."""
    assert isinstance(DATABASE_ALLOWED_TABLES, list)
    assert isinstance(DATABASE_EXCLUDED_COLUMNS, list)
    assert isinstance(DATABASE_RESTRICTED_TABLES, (list, str))
    assert isinstance(RESPONSE_MAX_WORDS, int)
    assert isinstance(LLM_MAX_RETRIES, int)
    assert isinstance(SMALLTALK_ENABLED, bool)
    assert isinstance(PROFANITY_FILTER_ENABLED, bool)


def test_response_max_words_is_positive():
    """Test that RESPONSE_MAX_WORDS is a positive integer."""
    assert RESPONSE_MAX_WORDS > 0


def test_llm_max_retries_is_positive():
    """Test that LLM_MAX_RETRIES is a positive integer."""
    assert LLM_MAX_RETRIES > 0


def test_profanity_filter_enabled_default():
    """Test that PROFANITY_FILTER_ENABLED is enabled by default."""
    assert PROFANITY_FILTER_ENABLED is True
