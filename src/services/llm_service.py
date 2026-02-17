import json
import logging
from dataclasses import dataclass

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from config.base import OPENROUTER_API_KEY, OPENROUTER_MODEL

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SqlGeneration:
    status: str
    sql: str | None
    notes: str | None = None


class LlmService:
    def __init__(self) -> None:
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is required")
        if not OPENROUTER_MODEL:
            raise ValueError("OPENROUTER_MODEL is required")
        self._client = ChatOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            model=OPENROUTER_MODEL,
            temperature=0.1,
            max_tokens=800,
        )

    async def generate_sql(
        self,
        question: str,
        schema_text: str,
        dialect: str,
        constraints_text: str,
        error_context: str | None = None,
    ) -> SqlGeneration:
        system_parts = [
            "# SQL Generation Task",
            "Generate safe, read-only SQL queries for analytics.",
            "",
            "## ⚠️ CRITICAL RULE #1: EXACT TABLE NAMES WITH QUOTES",
            "PostgreSQL requires double quotes for mixed-case table names:",
            "❌ WRONG: SELECT * FROM Employee_task",
            '✅ CORRECT: SELECT * FROM "Employee_task"',
            "",
            "RULES:",
            "1. Copy table names EXACTLY as shown in Available Schema (preserve all capitals)",
            '2. If table name has ANY uppercase letters, wrap it in double quotes: "Employee_task"',
            "3. If table name is all lowercase (e.g., auth_user), NO quotes needed",
            "4. Column names: same rule - quotes if mixed case, no quotes if lowercase",
            "",
            "Examples from your schema:",
            '- "Business_client" (has uppercase)',
            '- "Employee_task" (has uppercase)',
            '- "Trade_invoice" (has uppercase)',
            "- auth_user (all lowercase, no quotes)",
            "",
            "If query fails with 'relation does not exist', you forgot the quotes!",
            "",
            "## Output Format",
            (
                "Respond with ONLY a JSON object (no markdown, no code fences) "
                "with keys: status, sql, notes"
            ),
            'Example: {"status": "ok", "sql": "SELECT ...", "notes": null}',
            "",
            "## Status Values",
            "- 'ok': Generated valid SQL for a database question",
            (
                "- 'out_of_scope': Question is not database/analytics related "
                "OR cannot answer with available schema"
            ),
            "",
            "## Question Classification",
            (
                "IMPORTANT: If the user question is not about data/databases/analytics, "
                "return status 'out_of_scope' with notes 'off_topic'"
            ),
            (
                "Examples of database questions: "
                "counts, totals, aggregates, filtering, statistics, reports, trends"
            ),
            (
                "Examples of off-topic: "
                "jokes, philosophy, cooking, coding tutorials, non-data advice"
            ),
            "",
            "## SQL Rules",
            "1. Read-only only: NO INSERT/UPDATE/DELETE/DDL operations",
            "2. Never use SELECT * with excluded columns",
            ("3. See CRITICAL RULE #1 above - use exact table/column names from schema"),
            "4. ALWAYS add LIMIT clause to prevent huge result sets",
            ("5. If user asks for 'all records' or 'list all', use LIMIT 100 (maximum allowed)"),
            (
                "6. If user specifies a number (e.g., 'show 10', 'list 50'), "
                "use that as LIMIT but NEVER exceed 100"
            ),
            (
                "7. If user asks for more than 100 items, "
                "return status 'out_of_scope' with notes 'too_many_items'"
            ),
            "8. For vague queries without specific count, default to LIMIT 50",
            "9. Use only allowed/unrestricted tables from schema",
            (
                "10. ALWAYS exclude soft-deleted records: WHERE deleted_at IS NULL "
                "(or equivalent for other soft-delete columns)"
            ),
            (
                "11. If a table has a deleted_at, created_at, updated_at "
                "or similar timestamp column, assume it's for soft-deletes "
                "and exclude null values"
            ),
            "",
            "## Database Info",
            f"Dialect: {dialect}",
            "",
            "## Constraints",
            constraints_text,
            "",
            "## Available Schema",
            "⚠️ COPY TABLE NAMES EXACTLY AS SHOWN BELOW - CHARACTER BY CHARACTER:",
            schema_text or "(No accessible tables)",
        ]
        if error_context:
            system_parts.extend(["", "## Previous Attempt Error", error_context])

        message = SystemMessage(content="\n".join(system_parts))
        user_prompt = f"Question: {question}"
        response = await self._client.ainvoke([message, ("human", user_prompt)])
        raw_response = response.content or ""
        LOGGER.info(f"LLM generated SQL response: {raw_response[:150]}...")
        result = self._parse_sql_response(raw_response)
        LOGGER.info(
            f"Parsed SQL result: status={result.status}, "
            f"has_sql={bool(result.sql)}, notes={result.notes}"
        )
        return result

    async def generate_answer(
        self,
        question: str,
        sql: str,
        result_preview: str,
        currency_symbol: str = "$",
    ) -> str:
        system_parts = [
            "You write short, helpful answers based on SQL results.",
            "Reply in the same language as the user question.",
            "Use 1-3 sentences, max 30 words.",
            "Include numbers from the results.",
            "Do not expose sensitive columns or internal error details.",
            "Paraphrase table and column names into human-friendly wording.",
            (
                f"Format all monetary values with the currency symbol '{currency_symbol}' "
                f"(e.g., {currency_symbol}1,234.56)."
            ),
        ]
        message = SystemMessage(content="\n".join(system_parts))
        user_prompt = f"Question:\n{question}\n\nSQL:\n{sql}\n\nResults:\n{result_preview}"
        response = await self._client.ainvoke([message, ("human", user_prompt)])
        return (response.content or "").strip()

    async def generate_off_topic_reply(self, question: str) -> str:
        """Generate a witty, respectful reply for off-topic questions."""
        system_parts = [
            "You are a helpful and friendly data bot.",
            "The user asked a question that's not related to data or databases.",
            "Reply with a SHORT (1-2 sentences), WITTY, FUNNY but RESPECTFUL response.",
            "Make it clear you're here for data questions, but keep it light and friendly.",
            "Do NOT be dismissive or rude. Be clever and charming.",
            "Max 15 words.",
        ]
        message = SystemMessage(content="\n".join(system_parts))
        user_prompt = f"Off-topic question: {question}"
        response = await self._client.ainvoke([message, ("human", user_prompt)])
        return (response.content or "").strip()

    def _parse_sql_response(self, raw_text: str) -> SqlGeneration:
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            LOGGER.error(f"LLM JSON parse error: {exc}, raw text: {raw_text[:200]}")
            return SqlGeneration(status="out_of_scope", sql=None, notes="invalid_json")
        status = (payload.get("status") or "").lower()
        sql = payload.get("sql")
        notes = payload.get("notes")
        if status not in {"ok", "out_of_scope"}:
            LOGGER.warning(f"LLM returned invalid status: {status}, reverting to out_of_scope")
            status = "out_of_scope"
            sql = None
        if status == "ok" and not isinstance(sql, str):
            LOGGER.warning(f"LLM status ok but no valid SQL: sql={sql}, notes={notes}")
            status = "out_of_scope"
            sql = None
        return SqlGeneration(status=status, sql=sql, notes=notes)
