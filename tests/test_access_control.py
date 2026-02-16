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


@pytest.mark.asyncio
async def test_access_control_lists_and_removals(tmp_path):
    db_path = tmp_path / "audit.db"
    repo = AuditRepository(str(db_path))
    await repo.init()

    access = AccessControl(repo, admin_ids=[1], user_ids=[2])
    await access.seed_from_env()

    await access.add_user(3, added_by=1)
    await access.add_admin(4, added_by=1)

    assert await access.list_users() == [2, 3]
    assert await access.list_admins() == [1, 4]

    assert (await access.remove_user_checked(2)).reason == "env_protected"
    assert (await access.remove_admin_checked(1)).reason == "env_protected"

    assert (await access.remove_user_checked(4)).reason == "not_user"
    assert (await access.remove_admin_checked(3)).reason == "not_admin"

    assert (await access.remove_user_checked(3)).removed is True
    assert (await access.remove_admin_checked(4)).removed is True
