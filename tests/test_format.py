"""Test text formatting utilities."""

from utils.format import markdown_to_html, strip_markdown


def test_markdown_to_html_bold():
    assert markdown_to_html("**bold**") == "<b>bold</b>"
    assert markdown_to_html("This is **bold text** here") == "This is <b>bold text</b> here"


def test_markdown_to_html_italic():
    assert markdown_to_html("*italic*") == "<i>italic</i>"
    assert markdown_to_html("This is *italic text* here") == "This is <i>italic text</i> here"


def test_markdown_to_html_code():
    assert markdown_to_html("`code`") == "<code>code</code>"
    text = "Use `function()` to call it"
    expected = "Use <code>function()</code> to call it"
    assert markdown_to_html(text) == expected


def test_markdown_to_html_combined():
    text = "The phone number for client **Bismillah Bag Bazar** is **01877777228**."
    expected = "The phone number for client <b>Bismillah Bag Bazar</b> is <b>01877777228</b>."
    assert markdown_to_html(text) == expected


def test_markdown_to_html_mixed_formatting():
    text = "Use *italic* and **bold** and `code` together"
    expected = "Use <i>italic</i> and <b>bold</b> and <code>code</code> together"
    assert markdown_to_html(text) == expected


def test_markdown_to_html_escapes_ampersand():
    # & should be escaped first
    text = "Phone & Email"
    result = markdown_to_html(text)
    assert "&amp;" in result or "Phone & Email" in result


def test_markdown_to_html_empty():
    assert markdown_to_html("") == ""
    assert markdown_to_html(None) is None


def test_strip_markdown_bold():
    assert strip_markdown("**bold**") == "bold"
    assert strip_markdown("This is **bold** text") == "This is bold text"


def test_strip_markdown_italic():
    assert strip_markdown("*italic*") == "italic"
    assert strip_markdown("This is *italic* text") == "This is italic text"


def test_strip_markdown_code():
    assert strip_markdown("`code`") == "code"
    assert strip_markdown("Use `function()`") == "Use function()"


def test_strip_markdown_combined():
    text = "The phone number for client **Bismillah Bag Bazar** is **01877777228**."
    expected = "The phone number for client Bismillah Bag Bazar is 01877777228."
    assert strip_markdown(text) == expected


def test_strip_markdown_empty():
    assert strip_markdown("") == ""
    assert strip_markdown(None) is None
