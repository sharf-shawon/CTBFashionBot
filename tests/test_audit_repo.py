import pytest

from services.audit_repo import AuditRecord, AuditRepository


@pytest.mark.asyncio
async def test_audit_repo_records(tmp_path):
    db_path = tmp_path / "audit.db"
    repo = AuditRepository(str(db_path))
    await repo.init()

    record = AuditRecord(
        user_id=42,
        question="How many orders?",
        sql="SELECT 1",
        result="[]",
        success=True,
        error=None,
    )
    await repo.record_audit(record)

    assert await repo.is_user(42) is False


@pytest.mark.asyncio
async def test_audit_repo_lists_and_roles(tmp_path):
    db_path = tmp_path / "audit.db"
    repo = AuditRepository(str(db_path))
    await repo.init()

    await repo.upsert_user(10, "admin", added_by=None)
    await repo.upsert_user(20, "user", added_by=10)
    await repo.upsert_user(30, "user", added_by=10)

    assert await repo.list_user_ids() == [10, 20, 30]
    assert await repo.list_user_ids(role="admin") == [10]
    assert await repo.list_user_ids(role="user") == [20, 30]

    assert await repo.get_user_role(10) == "admin"
    assert await repo.get_user_role(20) == "user"
    assert await repo.get_user_role(999) is None
