"""Tests for profanity detection."""

from utils.profanity import PROFANITY_WARNINGS, contains_profanity, get_random_profanity_warning


def test_profanity_detection_single_word():
    """Test detection of single profanity word."""
    assert contains_profanity("damn") is True
    assert contains_profanity("hell") is True
    assert contains_profanity("crap") is True


def test_profanity_detection_case_insensitive():
    """Test that profanity detection is case-insensitive."""
    assert contains_profanity("DAMN") is True
    assert contains_profanity("Hell") is True
    assert contains_profanity("CrAp") is True


def test_profanity_detection_in_sentence():
    """Test detection of profanity within a sentence."""
    assert contains_profanity("This is damn frustrating") is True
    assert contains_profanity("Hell, I forgot") is True
    assert contains_profanity("What the hell is this?") is True


def test_profanity_detection_word_boundaries():
    """Test that profanity detection respects word boundaries."""
    # "damn" should be detected, but not as part of "damnit" if that's not in list
    assert contains_profanity("This is damn") is True
    # Words that contain profanity as part of a larger word shouldn't match
    # (e.g., "assemble" shouldn't match "ass" because of word boundaries)
    assert contains_profanity("assemble") is False  # "ass" is bounded, not matched in "assemble"
    assert contains_profanity("class") is False  # Doesn't contain "ass" as a word
    # But "fuck you" should match since "fuck" is a complete word
    assert contains_profanity("fuck you") is True


def test_profanity_detection_empty_string():
    """Test that empty string returns False."""
    assert contains_profanity("") is False


def test_profanity_detection_none():
    """Test that None is handled."""
    assert contains_profanity(None) is False  # Python handles None as falsy


def test_profanity_detection_multiple_profanities():
    """Test detection with multiple profanity words."""
    assert contains_profanity("damn hell crap") is True


def test_profanity_detection_clean_text():
    """Test that clean text returns False."""
    assert contains_profanity("How many orders did we sell today?") is False
    assert contains_profanity("What is the revenue?") is False
    assert contains_profanity("Show me the data") is False


def test_profanity_detection_mixed_clean_profane():
    """Test mixed clean and profane text."""
    assert contains_profanity("How the hell did this happen?") is True
    assert contains_profanity("This is damn good") is True


def test_get_random_profanity_warning():
    """Test that warnings are returned and are from the list."""
    warning = get_random_profanity_warning()
    assert warning in PROFANITY_WARNINGS
    assert len(warning) > 0
    assert isinstance(warning, str)


def test_profanity_warnings_list_not_empty():
    """Test that warnings list has content."""
    assert len(PROFANITY_WARNINGS) > 0
    # All warnings should be strings
    for warning in PROFANITY_WARNINGS:
        assert isinstance(warning, str)
        assert len(warning) > 0
        # All warnings should contain a reference to professional/respectful/language
        assert any(
            word in warning.lower()
            for word in ["professional", "respectful", "language", "offensive"]
        )


def test_profanity_warnings_mention_professional():
    """Test that at least one warning mentions professional/respectful."""
    assert any(
        "professional" in w.lower() or "respectful" in w.lower() or "offensive" in w.lower()
        for w in PROFANITY_WARNINGS
    )


def test_multiple_warnings_returned():
    """Test that calling multiple times can return different warnings."""
    warnings = set()
    for _ in range(20):  # Call multiple times
        warnings.add(get_random_profanity_warning())

    # Should have more than one unique warning if randomization works
    assert len(warnings) > 1


def test_specific_profanities_in_list():
    """Test that specific profanities are in the detection list."""
    # Test some common profanities
    assert contains_profanity("damn") is True
    assert contains_profanity("bitch") is True
    assert contains_profanity("fuck") is True
    assert contains_profanity("shit") is True
