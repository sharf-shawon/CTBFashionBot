import pytest

from services.access_control import AccessControl
from services.audit_repo import AuditRepository


@pytest.mark.asyncio
async def test_access_control_seeds_env(tmp_path):
    db_path = tmp_path / "audit.db"
    repo = AuditRepository(str(db_path))
    await repo.init()

    access = AccessControl(repo, admin_ids=[1], user_ids=[2])
    await access.seed_from_env()

    assert await access.is_admin(1) is True
    assert await access.is_allowed(2) is True
    assert await access.is_allowed(3) is False
