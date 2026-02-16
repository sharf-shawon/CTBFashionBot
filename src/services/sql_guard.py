from dataclasses import dataclass

import sqlglot
from sqlglot import exp

from utils.text_utils import normalize_name_set


@dataclass(frozen=True)
class GuardResult:
    ok: bool
    reason: str | None = None


class SqlGuard:
    def __init__(
        self,
        allowed_tables: list[str],
        restricted_tables: list[str],
        excluded_columns: list[str],
        table_columns: dict[str, list[str]] | None = None,
    ) -> None:
        self._allowed_tables = normalize_name_set(allowed_tables)
        self._restricted_tables = normalize_name_set(restricted_tables)
        self._excluded_columns = normalize_name_set(excluded_columns)
        self._table_columns = table_columns or {}

    def validate(self, sql: str) -> GuardResult:
        try:
            tree = sqlglot.parse_one(sql)
        except sqlglot.errors.ParseError as exc:
            return GuardResult(ok=False, reason=f"parse_error: {exc}")

        if tree.find(exp.Insert) or tree.find(exp.Update) or tree.find(exp.Delete):
            return GuardResult(ok=False, reason="write_operation")
        truncate_expr = getattr(exp, "Truncate", None)
        if (
            tree.find(exp.Create)
            or tree.find(exp.Drop)
            or tree.find(exp.Alter)
            or (truncate_expr and tree.find(truncate_expr))
        ):
            return GuardResult(ok=False, reason="ddl_operation")

        tables = {table.name for table in tree.find_all(exp.Table) if table.name}
        if not tables:
            return GuardResult(ok=False, reason="no_table_reference")

        lowered_tables = {table.lower() for table in tables}
        if self._allowed_tables and not lowered_tables.issubset(self._allowed_tables):
            return GuardResult(ok=False, reason="table_not_allowed")
        if lowered_tables.intersection(self._restricted_tables):
            return GuardResult(ok=False, reason="table_restricted")

        if self._excluded_columns:
            for column in tree.find_all(exp.Column):
                name = column.name or ""
                if name.lower() in self._excluded_columns:
                    return GuardResult(ok=False, reason="excluded_column")
            if tree.find(exp.Star):
                if self._has_excluded_column_in_tables(lowered_tables):
                    return GuardResult(ok=False, reason="wildcard_with_excluded_columns")

        return GuardResult(ok=True)

    def _has_excluded_column_in_tables(self, table_names: set[str]) -> bool:
        for table_name, columns in self._table_columns.items():
            if table_name.lower() not in table_names:
                continue
            for column in columns:
                if column.lower() in self._excluded_columns:
                    return True
        return False
