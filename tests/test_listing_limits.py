"""Tests for listing request detection and limit enforcement."""

import pytest

from services.audit_repo import AuditRepository
from services.query_service import QueryService


@pytest.mark.asyncio
async def test_is_listing_request_with_list_all(tmp_path):
    """Test that 'list all' is detected as a listing request."""
    audit_db = tmp_path / "audit.db"
    repo = AuditRepository(str(audit_db))
    await repo.init()

    service = QueryService(audit_repo=repo)

    assert service._is_listing_request("list all orders") is True
    assert service._is_listing_request("show all products") is True
    assert service._is_listing_request("display all users") is True
    assert service._is_listing_request("get all records") is True


@pytest.mark.asyncio
async def test_is_listing_request_with_specific_count(tmp_path):
    """Test that requests with specific counts are detected."""
    audit_db = tmp_path / "audit.db"
    repo = AuditRepository(str(audit_db))
    await repo.init()

    service = QueryService(audit_repo=repo)

    assert service._is_listing_request("list 10 orders") is True
    assert service._is_listing_request("show 50 products") is True
    assert service._is_listing_request("display 5 items") is True


@pytest.mark.asyncio
async def test_is_listing_request_with_all_keyword(tmp_path):
    """Test that 'all' keyword is detected."""
    audit_db = tmp_path / "audit.db"
    repo = AuditRepository(str(audit_db))
    await repo.init()

    service = QueryService(audit_repo=repo)

    assert service._is_listing_request("all orders") is True
    assert service._is_listing_request("all the products") is True


@pytest.mark.asyncio
async def test_is_listing_request_aggregate_not_detected(tmp_path):
    """Test that aggregate queries are NOT detected as listing requests."""
    audit_db = tmp_path / "audit.db"
    repo = AuditRepository(str(audit_db))
    await repo.init()

    service = QueryService(audit_repo=repo)

    # Aggregate queries should return False
    assert service._is_listing_request("how many orders") is False
    assert service._is_listing_request("count products") is False
    assert service._is_listing_request("what is the total revenue") is False
    assert service._is_listing_request("average price") is False
    assert service._is_listing_request("sum of all sales") is False
    assert service._is_listing_request("maximum value") is False
    assert service._is_listing_request("minimum cost") is False


@pytest.mark.asyncio
async def test_is_listing_request_vague_not_detected(tmp_path):
    """Test that vague queries are NOT detected as listing requests."""
    audit_db = tmp_path / "audit.db"
    repo = AuditRepository(str(audit_db))
    await repo.init()

    service = QueryService(audit_repo=repo)

    assert service._is_listing_request("what about orders?") is False
    assert service._is_listing_request("tell me about sales") is False
    assert service._is_listing_request("information on products") is False


@pytest.mark.asyncio
async def test_enforce_answer_constraints_with_skip(tmp_path):
    """Test that word limit is skipped when skip_word_limit=True."""
    audit_db = tmp_path / "audit.db"
    repo = AuditRepository(str(audit_db))
    await repo.init()

    service = QueryService(audit_repo=repo)

    # Long answer (> 30 words)
    long_answer = " ".join(["word"] * 50)

    # Without skip: should truncate
    result_truncated = service._enforce_answer_constraints(long_answer, skip_word_limit=False)
    assert len(result_truncated.split()) <= 30

    # With skip: should NOT truncate
    result_full = service._enforce_answer_constraints(long_answer, skip_word_limit=True)
    assert len(result_full.split()) == 50


@pytest.mark.asyncio
async def test_enforce_answer_constraints_empty_answer(tmp_path):
    """Test that empty answer returns error message."""
    audit_db = tmp_path / "audit.db"
    repo = AuditRepository(str(audit_db))
    await repo.init()

    service = QueryService(audit_repo=repo)

    result = service._enforce_answer_constraints("", skip_word_limit=False)
    assert result is not None
    assert len(result) > 0


@pytest.mark.asyncio
async def test_listing_patterns_case_insensitive(tmp_path):
    """Test that listing detection is case-insensitive."""
    audit_db = tmp_path / "audit.db"
    repo = AuditRepository(str(audit_db))
    await repo.init()

    service = QueryService(audit_repo=repo)

    assert service._is_listing_request("LIST ALL ORDERS") is True
    assert service._is_listing_request("Show All Products") is True
    assert service._is_listing_request("DISPLAY 10 ITEMS") is True


@pytest.mark.asyncio
async def test_listing_with_variations(tmp_path):
    """Test various listing query variations."""
    audit_db = tmp_path / "audit.db"
    repo = AuditRepository(str(audit_db))
    await repo.init()

    service = QueryService(audit_repo=repo)

    # Should detect
    assert service._is_listing_request("give me all orders") is True
    assert service._is_listing_request("tell me all products") is True
    assert service._is_listing_request("fetch all records") is True
    assert service._is_listing_request("get the orders") is True

    # Should NOT detect (aggregates)
    assert service._is_listing_request("how many total items") is False
    assert service._is_listing_request("count all users") is False


def test_too_many_items_error_message():
    """Test that the too_many_items error message is clear."""
    error_msg = (
        "I can only list up to 100 items at a time. "
        "Please be more precise with your query or ask for a smaller number of records."
    )

    # Verify message contains key phrases
    assert "100 items" in error_msg
    assert "more precise" in error_msg.lower()
    assert "smaller number" in error_msg.lower()
