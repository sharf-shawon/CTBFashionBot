"""Tests for LLM service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.llm_service import LlmService


@pytest.mark.asyncio
async def test_generate_answer_with_currency_symbol():
    """Test that generate_answer includes currency symbol in system prompt."""
    with patch("services.llm_service.ChatOpenAI") as mock_chat:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Today's revenue was Tk50,000."
        mock_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat.return_value = mock_instance

        service = LlmService()
        answer = await service.generate_answer(
            question="What was today's revenue?",
            sql="SELECT SUM(amount) FROM sales",
            result_preview="50000",
            currency_symbol="Tk",
        )

        assert answer == "Today's revenue was Tk50,000."
        # Verify the system prompt included the currency symbol instruction
        call_args = mock_instance.ainvoke.call_args
        assert call_args is not None
        messages = call_args[0][0]
        prompt_text = messages[0].content
        assert "Tk" in prompt_text
        assert "currency symbol" in prompt_text.lower()


@pytest.mark.asyncio
async def test_generate_answer_with_default_currency():
    """Test that generate_answer uses $ as default currency symbol."""
    with patch("services.llm_service.ChatOpenAI") as mock_chat:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Revenue is $25,000."
        mock_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat.return_value = mock_instance

        service = LlmService()
        answer = await service.generate_answer(
            question="What is the revenue?",
            sql="SELECT SUM(amount) FROM sales",
            result_preview="25000",
            # Omit currency_symbol to test default
        )

        assert answer == "Revenue is $25,000."
        # Verify the system prompt included default $ currency
        call_args = mock_instance.ainvoke.call_args
        messages = call_args[0][0]
        prompt_text = messages[0].content
        assert "$" in prompt_text


@pytest.mark.asyncio
async def test_generate_sql_with_proper_formatting():
    """Test that generate_sql returns properly formatted response."""
    with patch("services.llm_service.ChatOpenAI") as mock_chat:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = '{"status": "ok", "sql": "SELECT 1", "notes": null}'
        mock_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat.return_value = mock_instance

        service = LlmService()
        result = await service.generate_sql(
            question="How many users?",
            schema_text="Table: users",
            dialect="postgresql",
            constraints_text="Allowed tables: users",
        )

        assert result.status == "ok"
        assert result.sql == "SELECT 1"
        assert result.notes is None


@pytest.mark.asyncio
async def test_generate_sql_with_markdown_fences():
    """Test that generate_sql strips markdown code fences."""
    with patch("services.llm_service.ChatOpenAI") as mock_chat:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        # LLM sometimes returns JSON in markdown code fences
        mock_response.content = (
            '```json\n{"status": "ok", "sql": "SELECT * FROM users LIMIT 50", "notes": null}\n```'
        )
        mock_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat.return_value = mock_instance

        service = LlmService()
        result = await service.generate_sql(
            question="Show users",
            schema_text="Table: users",
            dialect="postgresql",
            constraints_text="Allowed tables: users",
        )

        assert result.status == "ok"
        assert result.sql == "SELECT * FROM users LIMIT 50"


@pytest.mark.asyncio
async def test_parse_sql_response_invalid_json():
    """Test that _parse_sql_response handles invalid JSON gracefully."""
    with patch("services.llm_service.ChatOpenAI") as mock_chat:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "This is not valid JSON"
        mock_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat.return_value = mock_instance

        service = LlmService()
        result = await service.generate_sql(
            question="Some question",
            schema_text="Schema",
            dialect="postgresql",
            constraints_text="Constraints",
        )

        assert result.status == "out_of_scope"
        assert result.sql is None
        assert result.notes == "invalid_json"
