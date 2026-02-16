from utils.smalltalk import handle_small_talk, is_farewell, is_greeting, is_small_talk


def test_greeting_detection():
    assert is_greeting("hello") is True
    assert is_greeting("Hi there!") is True
    assert is_greeting("what's up") is True
    assert is_greeting("good morning") is True
    assert is_greeting("how are you") is True
    assert is_greeting("data query") is False


def test_farewell_detection():
    assert is_farewell("bye") is True
    assert is_farewell("goodbye") is True
    assert is_farewell("see you") is True
    assert is_farewell("later") is True
    assert is_farewell("hello") is False


def test_small_talk_detection():
    assert is_small_talk("thanks") is True
    assert is_small_talk("ok") is True
    assert is_small_talk("lol") is True
    assert is_small_talk("haha") is True
    assert is_small_talk("cool") is True
    assert is_small_talk("how many users?") is False
    assert is_small_talk("count orders") is False


def test_handle_small_talk():
    response = handle_small_talk("hi")
    assert response is not None
    assert len(response) > 0

    response_bye = handle_small_talk("bye")
    assert response_bye is not None
    assert len(response_bye) > 0
