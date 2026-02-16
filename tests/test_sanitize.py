"""Test sanitization utilities."""

from utils.sanitize import (
    is_suspicious_sql_pattern,
    sanitize_for_markdown,
    sanitize_message,
    sanitize_user_id,
)


def test_sanitize_message_basic():
    assert sanitize_message("Hello world") == "Hello world"
    assert sanitize_message("  spaces  ") == "spaces"


def test_sanitize_message_limits_length():
    long_text = "a" * 3000
    result = sanitize_message(long_text)
    assert len(result) <= 2000


def test_sanitize_message_removes_null_bytes():
    assert sanitize_message("Hello\x00World") == "HelloWorld"


def test_sanitize_message_escapes_html():
    result = sanitize_message("<script>alert('xss')</script>")
    expected = "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
    assert result == expected


def test_sanitize_message_handles_empty():
    assert sanitize_message("") == ""
    assert sanitize_message(None) == ""


def test_sanitize_user_id_valid():
    assert sanitize_user_id("12345") == 12345
    assert sanitize_user_id("  999  ") == 999


def test_sanitize_user_id_invalid():
    assert sanitize_user_id("abc123") == 123
    assert sanitize_user_id("not_a_number") is None
    assert sanitize_user_id("") is None
    assert sanitize_user_id("-5") is None  # Negative IDs not allowed
    assert sanitize_user_id("0") is None  # Zero not allowed


def test_sanitize_user_id_limits_length():
    very_long = "1" * 100
    result = sanitize_user_id(very_long)
    assert result is not None


def test_sanitize_for_markdown():
    assert sanitize_for_markdown("simple text") == "simple text"
    assert sanitize_for_markdown("table_name") == "table\\_name"
    assert sanitize_for_markdown("*bold*") == "\\*bold\\*"
    assert sanitize_for_markdown("[link](url)") == "\\[link\\]\\(url\\)"


def test_sanitize_for_markdown_all_special_chars():
    text = "_*[]()~`>#+-=|{}.!"
    result = sanitize_for_markdown(text)
    # All should be escaped with backslashes
    assert "\\" in result
    assert result.count("\\") > 5  # Multiple escapes


def test_sanitize_for_markdown_empty():
    assert sanitize_for_markdown("") == ""
    assert sanitize_for_markdown(None) == ""


def test_is_suspicious_sql_pattern_clean():
    assert not is_suspicious_sql_pattern("How many users are there?")
    assert not is_suspicious_sql_pattern("Show me total sales")
    assert not is_suspicious_sql_pattern("What's the count of orders?")


def test_is_suspicious_sql_pattern_detects_injection():
    # SQL injection attempts
    assert is_suspicious_sql_pattern("; DROP TABLE users;")
    assert is_suspicious_sql_pattern("1' OR '1'='1'; DELETE FROM users;")
    assert is_suspicious_sql_pattern("hello; UPDATE users SET admin=1;")
    assert is_suspicious_sql_pattern("test UNION SELECT password FROM users")


def test_is_suspicious_sql_pattern_detects_xss():
    assert is_suspicious_sql_pattern("<script>alert('xss')</script>")
    assert is_suspicious_sql_pattern("javascript:alert(1)")
    assert is_suspicious_sql_pattern("img onerror=alert(1)")


def test_is_suspicious_sql_pattern_detects_command_execution():
    assert is_suspicious_sql_pattern("'; EXEC xp_cmdshell 'dir'")
    assert is_suspicious_sql_pattern("test; execute('malicious code')")


def test_is_suspicious_sql_pattern_case_insensitive():
    assert is_suspicious_sql_pattern("; DrOp TaBlE users;")
    assert is_suspicious_sql_pattern("UNION SELECT * FROM passwords")
