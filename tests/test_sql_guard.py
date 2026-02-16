from services.sql_guard import SqlGuard


def test_sql_guard_blocks_write_and_restricted():
    guard = SqlGuard(
        allowed_tables=["users"],
        restricted_tables=["admin_logs"],
        excluded_columns=["secret"],
        table_columns={"users": ["id", "name", "secret"]},
    )

    assert guard.validate("SELECT id, name FROM users").ok is True
    assert guard.validate("SELECT * FROM users").ok is False
    assert guard.validate("DELETE FROM users").ok is False
    assert guard.validate("SELECT id FROM admin_logs").ok is False
    assert guard.validate("SELECT secret FROM users").ok is False
