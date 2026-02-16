"""Tests for LLM error handling and currency symbol support."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.llm_service import LlmService


@pytest.mark.asyncio
async def test_llm_service_currency_symbol_parameter():
    """Test that LlmService.generate_answer accepts and uses currency_symbol parameter."""
    with patch("services.llm_service.ChatOpenAI") as mock_chat:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Revenue was Tk50000."
        mock_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat.return_value = mock_instance

        service = LlmService()

        # Call with currency_symbol parameter
        answer = await service.generate_answer(
            question="What was revenue?",
            sql="SELECT SUM(amount) FROM sales",
            result_preview="50000",
            currency_symbol="Tk",
        )

        # Verify call succeeded and answer was returned
        assert answer == "Revenue was Tk50000."

        # Verify the currency symbol appears in the system prompt
        call_args = mock_instance.ainvoke.call_args
        messages = call_args[0][0]
        system_prompt = messages[0].content
        assert "Tk" in system_prompt
        assert "currency symbol" in system_prompt.lower()


@pytest.mark.asyncio
async def test_llm_generate_answer_with_default_currency():
    """Test that generate_answer uses default $ currency symbol when not provided."""
    with patch("services.llm_service.ChatOpenAI") as mock_chat:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Amount is $500."
        mock_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat.return_value = mock_instance

        service = LlmService()

        # Call without currency_symbol to test default
        answer = await service.generate_answer(
            question="What is the amount?",
            sql="SELECT amount FROM orders LIMIT 1",
            result_preview="500",
        )

        assert answer == "Amount is $500."

        # Verify default $ symbol is in prompt
        call_args = mock_instance.ainvoke.call_args
        messages = call_args[0][0]
        system_prompt = messages[0].content
        assert "$" in system_prompt
        assert "currency symbol" in system_prompt.lower()


@pytest.mark.asyncio
async def test_llm_generate_answer_different_currency_symbols():
    """Test generate_answer with various currency symbols."""
    with patch("services.llm_service.ChatOpenAI") as mock_chat:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Price: €100"
        mock_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat.return_value = mock_instance

        service = LlmService()

        # Test with Euro symbol
        answer = await service.generate_answer(
            question="What is the price?",
            sql="SELECT price FROM products",
            result_preview="100",
            currency_symbol="€",
        )

        assert answer == "Price: €100"

        call_args = mock_instance.ainvoke.call_args
        messages = call_args[0][0]
        system_prompt = messages[0].content
        assert "€" in system_prompt


@pytest.mark.asyncio
async def test_llm_generate_off_topic_reply():
    """Test that generate_off_topic_reply method works correctly."""
    with patch("services.llm_service.ChatOpenAI") as mock_chat:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "I'm here for data questions!"
        mock_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat.return_value = mock_instance

        service = LlmService()

        reply = await service.generate_off_topic_reply("What's the meaning of life?")

        assert reply == "I'm here for data questions!"
        # Verify the method was called
        assert mock_instance.ainvoke.called


@pytest.mark.asyncio
async def test_llm_generate_sql_success():
    """Test that generate_sql correctly parses valid JSON responses."""
    with patch("services.llm_service.ChatOpenAI") as mock_chat:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = (
            '{"status": "ok", "sql": "SELECT COUNT(*) FROM users", "notes": null}'
        )
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
        assert result.sql == "SELECT COUNT(*) FROM users"
        assert result.notes is None


@pytest.mark.asyncio
async def test_llm_generate_sql_with_markdown_fences():
    """Test that generate_sql strips markdown code fences from JSON."""
    with patch("services.llm_service.ChatOpenAI") as mock_chat:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        # LLM sometimes wraps JSON in markdown code fences
        mock_response.content = (
            '```json\n{"status": "ok", "sql": "SELECT * FROM products", "notes": null}\n```'
        )
        mock_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat.return_value = mock_instance

        service = LlmService()

        result = await service.generate_sql(
            question="Show products",
            schema_text="Table: products",
            dialect="postgresql",
            constraints_text="Allowed tables: products",
        )

        assert result.status == "ok"
        assert result.sql == "SELECT * FROM products"


@pytest.mark.asyncio
async def test_llm_parse_sql_response_invalid_json():
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

        # Should return out_of_scope with invalid_json note on parse failure
        assert result.status == "out_of_scope"
        assert result.sql is None
        assert result.notes == "invalid_json"


@pytest.mark.asyncio
async def test_llm_parse_sql_response_out_of_scope():
    """Test that _parse_sql_response correctly handles out_of_scope responses."""
    with patch("services.llm_service.ChatOpenAI") as mock_chat:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = '{"status": "out_of_scope", "sql": null, "notes": "off_topic"}'
        mock_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat.return_value = mock_instance

        service = LlmService()

        result = await service.generate_sql(
            question="What is life?",
            schema_text="Schema",
            dialect="postgresql",
            constraints_text="Constraints",
        )

        assert result.status == "out_of_scope"
        assert result.sql is None
        assert result.notes == "off_topic"


@pytest.mark.asyncio
async def test_llm_generate_sql_with_error_context():
    """Test that generate_sql includes error context in retry attempts."""
    with patch("services.llm_service.ChatOpenAI") as mock_chat:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = (
            '{"status": "ok", "sql": "SELECT id FROM orders LIMIT 50", "notes": null}'
        )
        mock_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat.return_value = mock_instance

        service = LlmService()

        result = await service.generate_sql(
            question="Show orders",
            schema_text="Table: orders",
            dialect="postgresql",
            constraints_text="Allowed tables: orders",
            error_context="Previous attempt failed: table not found",
        )

        assert result.status == "ok"
        # Verify error_context was included in the call
        call_args = mock_instance.ainvoke.call_args
        messages = call_args[0][0]
        system_prompt = messages[0].content
        assert "Previous attempt failed" in system_prompt
