from dataclasses import dataclass

from services.audit_repo import AuditRepository


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str | None = None


class AccessControl:
    def __init__(self, repo: AuditRepository, admin_ids: list[int], user_ids: list[int]):
        self._repo = repo
        self._admin_ids = {int(user_id) for user_id in admin_ids}
        self._user_ids = {int(user_id) for user_id in user_ids}

    async def seed_from_env(self) -> None:
        for admin_id in self._admin_ids:
            await self._repo.upsert_user(admin_id, "admin", None)
        for user_id in self._user_ids:
            if user_id not in self._admin_ids:
                await self._repo.upsert_user(user_id, "user", None)

    async def is_admin(self, user_id: int) -> bool:
        if user_id in self._admin_ids:
            return True
        return await self._repo.is_admin(user_id)

    async def is_allowed(self, user_id: int) -> bool:
        if await self.is_admin(user_id):
            return True
        if user_id in self._user_ids:
            return True
        return await self._repo.is_user(user_id)

    async def add_user(self, user_id: int, added_by: int) -> None:
        await self._repo.upsert_user(user_id, "user", added_by)

    async def remove_user(self, user_id: int) -> bool:
        return await self._repo.remove_user(user_id)
