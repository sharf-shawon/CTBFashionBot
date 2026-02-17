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
        # Select quote character based on database dialect
        quote_open = "`" if dialect == "mysql" else '"'
        quote_close = "`" if dialect == "mysql" else '"'
        quote_name = "backticks" if dialect == "mysql" else "double quotes"

        system_parts = [
            "# SQL Generation Task",
            "Generate safe, read-only SQL queries for analytics.",
            "",
            f"## ⚠️ CRITICAL RULE #1: EXACT TABLE NAMES WITH {quote_name.upper()}",
            f"Your database uses {quote_name} for mixed-case table names:",
            "❌ WRONG: SELECT * FROM Employee_task",
            f"✅ CORRECT: SELECT * FROM {quote_open}Employee_task{quote_close}",
            "",
            "RULES:",
            "1. Copy table names EXACTLY as shown in Available Schema (preserve all capitals)",
            f"2. If table name has ANY uppercase letters, wrap it in \
                {quote_name}: {quote_open}Employee_task{quote_close}",
            "3. If table name is all lowercase (e.g., auth_user), NO quotes needed",
            f"4. Column names: same rule - {quote_name} if mixed case, no quotes if lowercase",
            "",
            "Examples from your schema:",
            f"- {quote_open}Business_client{quote_close} (has uppercase)",
            f"- {quote_open}Employee_task{quote_close} (has uppercase)",
            f"- {quote_open}Trade_invoice{quote_close} (has uppercase)",
            "- auth_user (all lowercase, no quotes)",
            "",
            f"If query fails with 'not found' or 'does not exist', you forgot the {quote_name}!",
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
            "## Recognizing Domain Terms",
            "Tables in schema: Trade_voucher, Trade_invoice, Employee_task, etc.",
            "Users may spell/transliterate these differently in other languages.",
            "If question mentions terms like:",
            "- voucher/ভাউচার/வவுச்சர் → check Trade_voucher table",
            "- invoice/ইনভয়েস/चालान → check Trade_invoice table",
            "- task/টাস্ক/कार्य → check Employee_task table",
            "These are database questions, NOT off-topic!",
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
            "## Date Filtering (CRITICAL)",
            "When user asks for 'today', 'yesterday', 'this week', etc.:",
            "1. PREFER the table's transaction date \
                (created_at, invoice_date, voucher_date, payment_date)",
            "2. Use ONLY ONE date column per query - don't mix created_at with invoice_date",
            "3. Use consistent filtering (e.g., \
                use >= CURRENT_DATE - INTERVAL for ranges, not exact dates)",
            "4. Examples by table:",
            "   - Trade_invoice: use 'invoice_date' for 'invoices from ...'",
            "   - Trade_voucher: use 'voucher_date' for 'vouchers from ...'",
            "   - Trade_payment: use 'payment_date' for payment questions",
            "   - created_at: only if table has no domain-specific date column",
            "5. If detail query returns no results but count returns results,",
            "   use the same date column and filtering logic as the count query",
            "",
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
