import asyncio
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import create_engine, text

from config.base import (
    CURRENCY_SYMBOL,
    DATABASE_ALLOWED_TABLES,
    DATABASE_EXCLUDED_COLUMNS,
    DATABASE_RESTRICTED_TABLES,
    DATABASE_URL,
    LLM_MAX_RETRIES,
    LOGGER,
    RESPONSE_MAX_WORDS,
    SMALLTALK_ENABLED,
)
from services.audit_repo import AuditRecord, AuditRepository
from services.llm_service import LlmService
from services.schema_service import SchemaService
from services.sql_guard import SqlGuard
from utils.db_utils import normalize_database_url
from utils.responses import (
    get_random_db_unavailable,
    get_random_error,
    get_random_negative,
)
from utils.smalltalk import handle_small_talk, is_small_talk
from utils.text_utils import count_words, truncate_to_words


@dataclass(frozen=True)
class QueryResult:
    answer: str
    sql: str | None
    success: bool


class QueryService:
    def __init__(self, audit_repo: AuditRepository) -> None:
        self._audit_repo = audit_repo
        LOGGER.info(
            f"QueryService init: DATABASE_ALLOWED_TABLES={DATABASE_ALLOWED_TABLES}, "
            f"DATABASE_RESTRICTED_TABLES={DATABASE_RESTRICTED_TABLES}, "
            f"DATABASE_EXCLUDED_COLUMNS={DATABASE_EXCLUDED_COLUMNS}"
        )
        self._schema_service = SchemaService(
            database_url=DATABASE_URL,
            allowed_tables=DATABASE_ALLOWED_TABLES,
            restricted_tables=DATABASE_RESTRICTED_TABLES,
            excluded_columns=DATABASE_EXCLUDED_COLUMNS,
        )
        self._llm = LlmService()

    async def answer_question(self, user_id: int, question: str) -> QueryResult:
        if SMALLTALK_ENABLED and is_small_talk(question):
            LOGGER.debug(f"Small talk detected: {question}")
            response = handle_small_talk(question)
            await self._audit_repo.record_audit(
                AuditRecord(
                    user_id=user_id,
                    question=question,
                    sql=None,
                    result=None,
                    success=True,
                    error=None,
                )
            )
            return QueryResult(answer=response, sql=None, success=True)

        schema_info = await asyncio.to_thread(self._schema_service.get_schema_info)
        LOGGER.debug(f"Schema tables: {list(schema_info.tables.keys())}")
        if schema_info.connection_error:
            LOGGER.error(f"Database connection failed for user {user_id}")
            await self._audit_repo.record_audit(
                AuditRecord(
                    user_id=user_id,
                    question=question,
                    sql=None,
                    result=None,
                    success=False,
                    error="database_unreachable",
                )
            )
            return QueryResult(answer=get_random_db_unavailable(), sql=None, success=False)
        if not schema_info.tables:
            LOGGER.warning(f"No accessible tables for user {user_id}, question: {question}")
            await self._audit_repo.record_audit(
                AuditRecord(
                    user_id=user_id,
                    question=question,
                    sql=None,
                    result=None,
                    success=False,
                    error="no_allowed_tables",
                )
            )
            return QueryResult(answer=get_random_negative(), sql=None, success=False)

        guard = SqlGuard(
            allowed_tables=DATABASE_ALLOWED_TABLES,
            restricted_tables=DATABASE_RESTRICTED_TABLES,
            excluded_columns=DATABASE_EXCLUDED_COLUMNS,
            table_columns=schema_info.full_table_columns,
        )

        last_error = None
        for attempt in range(1, LLM_MAX_RETRIES + 1):
            try:
                generation = await self._llm.generate_sql(
                    question=question,
                    schema_text=schema_info.schema_text,
                    dialect=schema_info.dialect,
                    constraints_text=self._constraints_text(),
                    error_context=last_error,
                )
            except Exception as exc:  # Catch API errors (e.g., 502, connection timeouts)
                LOGGER.error(f"LLM API error on attempt {attempt}/{LLM_MAX_RETRIES}: {exc}")
                last_error = f"llm_api_error: {type(exc).__name__}"
                if attempt >= LLM_MAX_RETRIES:
                    await self._audit_repo.record_audit(
                        AuditRecord(
                            user_id=user_id,
                            question=question,
                            sql=None,
                            result=None,
                            success=False,
                            error=last_error,
                        )
                    )
                    return QueryResult(answer=get_random_error(), sql=None, success=False)
                continue

            if generation.status != "ok" or not generation.sql:
                LOGGER.info(
                    f"LLM returned non-ok status for user {user_id}: "
                    f"status={generation.status}, notes={generation.notes}, "
                    f"question={question[:80]}"
                )
                if generation.notes == "too_many_items":
                    LOGGER.info(f"User {user_id} requested too many items: {question}")
                    reply = (
                        "I can only list up to 100 items at a time. "
                        "Please be more precise with your query "
                        "or ask for a smaller number of records."
                    )
                    await self._audit_repo.record_audit(
                        AuditRecord(
                            user_id=user_id,
                            question=question,
                            sql=None,
                            result=None,
                            success=False,
                            error="too_many_items",
                        )
                    )
                    return QueryResult(answer=reply, sql=None, success=False)
                if generation.notes == "off_topic":
                    LOGGER.info(f"Off-topic question from user {user_id}: {question[:80]}")
                    try:
                        reply = await self._llm.generate_off_topic_reply(question)
                    except Exception as exc:
                        LOGGER.error(f"LLM API error generating off-topic reply: {exc}")
                        reply = get_random_error()
                    await self._audit_repo.record_audit(
                        AuditRecord(
                            user_id=user_id,
                            question=question,
                            sql=None,
                            result=None,
                            success=True,
                            error=None,
                        )
                    )
                    return QueryResult(answer=reply, sql=None, success=True)
                LOGGER.info(
                    f"LLM out_of_scope for user {user_id}: "
                    f"status={generation.status}, notes={generation.notes}"
                )
                await self._audit_repo.record_audit(
                    AuditRecord(
                        user_id=user_id,
                        question=question,
                        sql=None,
                        result=None,
                        success=False,
                        error=generation.notes or "out_of_scope",
                    )
                )
                return QueryResult(answer=get_random_negative(), sql=None, success=False)

            validation = guard.validate(generation.sql)
            if not validation.ok:
                LOGGER.warning(
                    f"SQL guard rejected for user {user_id}: "
                    f"reason={validation.reason}, sql={generation.sql[:100]}"
                )
                last_error = validation.reason or "invalid_sql"
                continue

            try:
                rows = await asyncio.to_thread(self._execute_sql, generation.sql)
            except Exception as exc:  # pragma: no cover - handled via retries
                LOGGER.warning(
                    f"SQL execution failed for user {user_id}: {exc}, "
                    f"sql={generation.sql[:100]}, attempt {attempt}/{LLM_MAX_RETRIES}"
                )
                last_error = f"execution_error: {exc}"
                if attempt >= LLM_MAX_RETRIES:
                    await self._audit_repo.record_audit(
                        AuditRecord(
                            user_id=user_id,
                            question=question,
                            sql=generation.sql,
                            result=None,
                            success=False,
                            error=last_error,
                        )
                    )
                    return QueryResult(answer=get_random_error(), sql=generation.sql, success=False)
                continue

            rows = self._redact_rows(rows)
            if not rows:
                LOGGER.info(f"Query returned no results for user {user_id}: {question[:80]}")
                await self._audit_repo.record_audit(
                    AuditRecord(
                        user_id=user_id,
                        question=question,
                        sql=generation.sql,
                        result=None,
                        success=False,
                        error="no_results",
                    )
                )
                return QueryResult(answer=get_random_negative(), sql=generation.sql, success=False)

            preview = self._format_results(rows)
            try:
                answer = await self._llm.generate_answer(
                    question=question,
                    sql=generation.sql,
                    result_preview=preview,
                    currency_symbol=CURRENCY_SYMBOL,
                )
            except Exception as exc:
                LOGGER.error(f"LLM API error generating answer: {exc}")
                answer = get_random_error()

            # Skip word limit for explicit listing requests
            is_listing = self._is_listing_request(question)
            answer = self._enforce_answer_constraints(answer, skip_word_limit=is_listing)

            await self._audit_repo.record_audit(
                AuditRecord(
                    user_id=user_id,
                    question=question,
                    sql=generation.sql,
                    result=AuditRepository.serialize_result(rows),
                    success=True,
                    error=None,
                )
            )
            return QueryResult(answer=answer, sql=generation.sql, success=True)

        await self._audit_repo.record_audit(
            AuditRecord(
                user_id=user_id,
                question=question,
                sql=None,
                result=None,
                success=False,
                error=last_error or "retry_exhausted",
            )
        )
        return QueryResult(answer=get_random_error(), sql=None, success=False)

    def _execute_sql(self, sql: str) -> list[dict[str, Any]]:
        engine = create_engine(
            normalize_database_url(DATABASE_URL),
            pool_pre_ping=False,
            pool_size=5,
            max_overflow=10,
        )
        try:
            with engine.connect() as connection:
                with connection.begin():
                    if engine.dialect.name == "postgresql":
                        connection.execute(text("SET TRANSACTION READ ONLY"))
                    result = connection.execute(text(sql))
                    rows = [dict(row) for row in result.mappings().fetchmany(50)]
                    return rows
        finally:
            engine.dispose()

    def _format_results(self, rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "[]"
        limited = rows[:10]
        return AuditRepository.serialize_result(limited)

    def _redact_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return rows
        excluded = {name.lower() for name in DATABASE_EXCLUDED_COLUMNS}
        if not excluded:
            return rows
        redacted = []
        for row in rows:
            filtered = {key: value for key, value in row.items() if key.lower() not in excluded}
            if filtered:
                redacted.append(filtered)
        return redacted

    def _enforce_answer_constraints(self, answer: str, skip_word_limit: bool = False) -> str:
        if not answer:
            return get_random_error()
        if not skip_word_limit and count_words(answer) > RESPONSE_MAX_WORDS:
            return truncate_to_words(answer, RESPONSE_MAX_WORDS)
        return answer

    def _is_listing_request(self, question: str) -> bool:
        """
        Detect if user is asking for a list of records (not aggregates).
        Returns True for: "list all", "show all", "list 10", "show 50 products", etc.
        Returns False for: "how many", "what is total", "average", etc.
        """
        question_lower = question.lower()

        # Aggregate/summary keywords - NOT listing requests
        aggregate_keywords = [
            "how many",
            "count",
            "total",
            "sum",
            "average",
            "avg",
            "maximum",
            "max",
            "minimum",
            "min",
            "statistics",
            "stat",
        ]
        if any(keyword in question_lower for keyword in aggregate_keywords):
            return False

        # Listing keywords
        listing_patterns = [
            r"\b(list|show|display|get|fetch|give me|tell me)\s+(all|the|me|every)",
            r"\b(list|show|display)\s+\d+",  # "list 10", "show 50"
            r"\ball\s+(the\s+)?\w+s?\b",  # "all orders", "all the products"
        ]
        for pattern in listing_patterns:
            if re.search(pattern, question_lower):
                return True

        return False

    def _constraints_text(self) -> str:
        return (
            "Allowed tables: "
            + ", ".join(DATABASE_ALLOWED_TABLES or ["(any)"])
            + "\nRestricted tables: "
            + ", ".join(DATABASE_RESTRICTED_TABLES or ["(none)"])
            + "\nExcluded columns: "
            + ", ".join(DATABASE_EXCLUDED_COLUMNS or ["(none)"])
            + f"\nCurrency symbol: {CURRENCY_SYMBOL} - "
            + "Use this symbol when formatting any monetary values in results "
            + f"(e.g., {CURRENCY_SYMBOL}100.50)"
        )
