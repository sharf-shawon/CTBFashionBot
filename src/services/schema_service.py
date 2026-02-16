import logging
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from utils.db_utils import normalize_database_url
from utils.text_utils import normalize_name_set

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SchemaInfo:
    tables: dict[str, list[str]]
    full_table_columns: dict[str, list[str]]
    schema_text: str
    dialect: str
    connection_error: bool = False


class SchemaService:
    def __init__(
        self,
        database_url: str,
        allowed_tables: Iterable[str],
        restricted_tables: Iterable[str],
        excluded_columns: Iterable[str],
    ) -> None:
        self._database_url = normalize_database_url(database_url)
        LOGGER.debug(f"SchemaService DB URL (normalized): {self._database_url[:80]}...")
        self._allowed_tables = normalize_name_set(allowed_tables)
        self._restricted_tables = normalize_name_set(restricted_tables)
        self._excluded_columns = normalize_name_set(excluded_columns)
        self._engine: Engine | None = None
        self._cached: SchemaInfo | None = None

    def get_schema_info(self) -> SchemaInfo:
        if self._cached:
            return self._cached
        try:
            LOGGER.debug(f"Introspecting schema from: {self._database_url[:50]}...")
            engine = self._get_engine()
            inspector = inspect(engine)
        except SQLAlchemyError as exc:
            LOGGER.error(f"Schema introspection failed: {exc}")
            return SchemaInfo(
                tables={},
                full_table_columns={},
                schema_text="",
                dialect="",
                connection_error=True,
            )
        tables = inspector.get_table_names()
        views = inspector.get_view_names()
        all_tables = tables + views
        LOGGER.debug(f"Found tables: {all_tables}")
        filtered_tables: list[str] = []
        for table_name in all_tables:
            lowered = table_name.lower()
            if self._allowed_tables and lowered not in self._allowed_tables:
                LOGGER.debug(f"Filtering out table (not in allowed): {table_name}")
                continue
            if lowered in self._restricted_tables:
                LOGGER.debug(f"Filtering out table (restricted): {table_name}")
                continue
            filtered_tables.append(table_name)
        LOGGER.debug(f"Filtered tables: {filtered_tables}")

        table_columns: dict[str, list[str]] = {}
        full_table_columns: dict[str, list[str]] = {}
        for table_name in filtered_tables:
            columns = [column["name"] for column in inspector.get_columns(table_name)]
            full_table_columns[table_name] = columns
            filtered_columns = [
                column for column in columns if column.lower() not in self._excluded_columns
            ]
            table_columns[table_name] = filtered_columns

        schema_text = self._format_schema(table_columns)
        info = SchemaInfo(
            tables=table_columns,
            full_table_columns=full_table_columns,
            schema_text=schema_text,
            dialect=engine.dialect.name,
        )
        self._cached = info
        return info

    def _get_engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(
                self._database_url,
                pool_pre_ping=False,
                pool_size=5,
                max_overflow=10,
            )
        return self._engine

    def _format_schema(self, table_columns: dict[str, list[str]]) -> str:
        if not table_columns:
            return ""
        lines = []
        for table_name, columns in sorted(table_columns.items()):
            columns_text = ", ".join(columns) if columns else "(no allowed columns)"
            lines.append(f"Table: {table_name}\nColumns: {columns_text}")
        return "\n\n".join(lines)
