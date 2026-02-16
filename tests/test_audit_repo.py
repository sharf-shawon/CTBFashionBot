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
