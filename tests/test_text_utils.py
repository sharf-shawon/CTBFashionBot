from utils.text_utils import count_words, truncate_to_words


def test_truncate_to_words():
    text = "one two three four five"
    assert count_words(text) == 5
    assert truncate_to_words(text, 3) == "one two three"
