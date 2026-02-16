from main import format_numbered_list


def test_format_numbered_list_marks_env_ids():
    result = format_numbered_list([1, 2], "users", protected_ids={2})
    assert "1. 1" in result
    assert "2. 2 (env)" in result
    assert "cannot be removed" in result


def test_format_numbered_list_no_users():
    assert format_numbered_list([], "users") == "No users found."


def test_format_numbered_list_no_protected_note():
    result = format_numbered_list([5], "admins", protected_ids=set())
    assert result == "Admins:\n1. 5"
