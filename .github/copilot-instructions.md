# GitHub Copilot Instructions - CTBFashion Bot

## Project Overview

This is a production-ready Telegram bot that translates natural language questions into safe SQL queries using LLM (OpenRouter). The bot provides conversational access to PostgreSQL databases with built-in safety, access control, and audit logging.

## Architecture

### Service Layer Pattern

- **Separation of concerns**: Each service has a single responsibility
- **Dependency injection**: Services are injected into handlers, not imported directly
- **Async-first**: All I/O operations use async/await

### Key Services

1. **AuditRepository** (`services/audit_repo.py`) - SQLite persistence for users and audit logs
2. **AccessControl** (`services/access_control.py`) - User permission management
3. **SchemaService** (`services/schema_service.py`) - Live PostgreSQL schema introspection with filtering
4. **SqlGuard** (`services/sql_guard.py`) - SQL validation (read-only, table/column restrictions)
5. **LlmService** (`services/llm_service.py`) - OpenRouter integration with structured JSON responses
6. **QueryService** (`services/query_service.py`) - Orchestrates the full NL→SQL→Answer pipeline
7. **InspireService** (`services/inspire_service.py`) - Generates sample questions from schema

### Data Flow

```
User Message → Profanity Check → Small-talk Check → Access Control
→ Schema Fetch → LLM (SQL Generation) → Guard Validation
→ Execute (Read-only) → Redact Excluded Columns → LLM (Answer Generation)
→ Enforce Constraints → Audit Log → Reply to User
```

## Code Style & Conventions

### Python Version

- **Python 3.13+** required
- Use modern type hints: `list[str]`, `dict[str, Any]`, `str | None`
- Prefer `dataclass(frozen=True)` for immutable data structures

### Formatting & Linting

- **Ruff** for formatting and linting (line-length: 100)
- **Format on save** enabled in VS Code
- **Pre-commit hooks** run ruff + pytest automatically
- Run `uv run ruff format` before committing
- Run `uv run ruff check --fix` to auto-fix linting issues

### Naming Conventions

- **Snake_case** for functions, variables, file names
- **PascalCase** for classes
- **SCREAMING_SNAKE_CASE** for constants and env vars
- Prefix private methods with `_` (e.g., `_execute_sql`)

### Import Organization

```python
# Standard library
import asyncio
import re

# Third-party
from telegram import Update
from sqlalchemy import create_engine

# Local - absolute imports from src/
from config.base import DATABASE_URL
from services.query_service import QueryService
```

## Error Handling Guidelines

### User-Facing Errors

- **NEVER** expose internal error details, stack traces, or SQL to users
- Use randomized error messages from `utils/responses.py`
- Log detailed errors with `LOGGER.error()` for debugging
- Always return graceful fallback responses

### Example Pattern

```python
try:
    result = await dangerous_operation()
except Exception as exc:
    LOGGER.error(f"Operation failed: {exc}")  # Log details
    return get_random_error()  # Generic message to user
```

### LLM Error Handling

- Wrap all LLM calls in try/except (API can return 502, timeouts, etc.)
- Retry up to `LLM_MAX_RETRIES` times with error context
- Fall back to safe error messages on exhaustion

## Security Requirements

### Database Safety

1. **Read-only transactions** - Always use `SET TRANSACTION READ ONLY` for PostgreSQL
2. **SQL validation** - Run all SQL through `SqlGuard.validate()` before execution
3. **Column redaction** - Remove `DATABASE_EXCLUDED_COLUMNS` from results
4. **Soft-delete awareness** - LLM is instructed to add `WHERE deleted_at IS NULL`
5. **Result limits** - Maximum 100 items per query, enforce in LLM prompt

### Access Control

- Check `access_control.is_allowed()` before processing any user message
- Admin-only commands: `/adduser`, `/remuser`
- Audit all queries with user ID, question, SQL, and result

### Environment Variables

- **NEVER** commit `.env` file
- All secrets in environment variables (injected at runtime)
- Required vars: `TG_BOT_TOKEN`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`
- Use `.env.example` for documentation only

## Testing Guidelines

### Test Structure

- **Pytest** with async support (`pytest-asyncio`)
- Tests in `tests/` directory mirror `src/` structure
- Mock external dependencies (Telegram, OpenRouter, PostgreSQL)
- Use `tmp_path` fixture for temporary file operations

### Test Patterns

```python
@pytest.mark.asyncio
async def test_feature_name(tmp_path):
    # Given: Setup
    repo = AuditRepository(str(tmp_path / "test.db"))
    await repo.init()

    # When: Action
    result = await repo.some_method()

    # Then: Assert
    assert result is not None
```

### Coverage Goals

- Core business logic: 80%+ coverage
- Integration points (LLM, DB): mocked and tested
- Error paths: test failure scenarios
- Edge cases: empty inputs, invalid data, API failures

### Running Tests

```bash
# All tests
uv run pytest

# Specific file
uv run pytest tests/test_profanity.py

# With coverage
uv run pytest --cov=src tests/

# Watch mode
uv run pytest-watch
```

## LLM Integration Patterns

### Structured Output

- Always request JSON from LLM with specific schema
- Strip markdown fences: `json...` → `{...}`
- Validate response structure before using
- Handle `invalid_json` gracefully

### Prompt Engineering

- **System message**: Define role, output format, rules
- **User message**: Question + context (schema, constraints)
- **Error context**: On retry, include previous error for correction
- Keep prompts concise but complete

### Status Codes

- `ok` - Valid SQL generated
- `out_of_scope` - Not a database question or exceeds limits
- Notes: `off_topic`, `too_many_items`, `invalid_json`

## Configuration Management

### Environment-Driven

- All settings in `config/base.py` load from env vars
- Provide sensible defaults for optional settings
- Required settings: empty string or None (fail fast if missing)

### Feature Flags

- `SMALLTALK_ENABLED` (default: true) - Handle greetings without LLM
- `PROFANITY_FILTER_ENABLED` (default: true) - Block offensive language
- `DEBUG` (default: false) - Verbose logging

### Database Restrictions

- `DATABASE_ALLOWED_TABLES` - If set, only these tables accessible
- `DATABASE_RESTRICTED_TABLES` - Block specific tables completely
- `DATABASE_EXCLUDED_COLUMNS` - Hide columns from results (passwords, secrets)

## Bot Command Patterns

### Handler Structure

```python
async def command_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Brief description."""
    services: AppServices = context.bot_data["services"]
    user = update.effective_user

    # Check access
    if not await services.access_control.is_allowed(user.id):
        await update.message.reply_text(blocked_message(user.id))
        return

    # Handle command
    # ...
```

### Message Flow

1. Extract services from `context.bot_data`
2. Check access control
3. Validate input
4. Call service layer
5. Reply with result
6. Log errors (don't expose to user)

## Utilities

### Randomized Responses

- Use `get_random_*()` functions from `utils/responses.py`
- Categories: affirmative, negative, waiting, error, db_unavailable, access_denied
- Easy to add more variations for natural conversation

### Text Processing

- `count_words()`, `truncate_to_words()` from `utils/text_utils.py`
- Word limit bypassed for explicit listing requests
- Use `_is_listing_request()` to detect list queries

### Small-talk Detection

- Regex patterns in `utils/smalltalk.py`
- Detects greetings, farewells, acknowledgments
- Avoids LLM cost for non-data questions

### Profanity Filter

- Word boundary detection in `utils/profanity.py`
- 30+ common profanities
- Professional warning messages
- ENV-controllable

## Database Patterns

### Connection Management

- Create engine per request (no connection pooling needed for bot)
- Always dispose engine after use
- Use `normalize_database_url()` for postgres:// → postgresql+psycopg://

### Schema Introspection

- Cached per instance (single-threaded bot)
- Graceful degradation on connection failures (connection_error flag)
- Filter tables and columns before exposing to LLM

### Audit Persistence

- SQLite for audit logs (async via aiosqlite)
- Separate from production database
- Schema: users (user_id, role) + audits (user_id, question, sql, result, success)

## Docker Deployment

### Multi-stage Build

- Alpine base for minimal footprint
- Non-root user (appuser)
- Volume mounts for persistent data: `storage/data`, `storage/logs`

### Environment Variables

- Pass all vars through docker-compose.yml
- Required vars use `${VAR:?err}` syntax
- Optional vars use `${VAR:-default}` syntax

## Common Patterns to Follow

### Adding a New Service

1. Create file in `src/services/`
2. Define class with clear responsibility
3. Add type hints for all parameters and returns
4. Use async for I/O operations
5. Add to `AppServices` dataclass in `main.py`
6. Write tests in `tests/test_<service>.py`

### Adding a New Command

1. Create handler function with `async def` signature
2. Extract services from `context.bot_data`
3. Check access control
4. Use existing services, don't duplicate logic
5. Register in `main()` with `application.add_handler()`

### Adding a New Utility

1. Create file in `src/utils/`
2. Keep functions pure and stateless where possible
3. Add comprehensive docstrings
4. Write unit tests
5. Import in services as needed

## Troubleshooting Common Issues

### Import Errors

- Ensure `sys.path` includes `src/` (done in `conftest.py`)
- Use absolute imports: `from config.base import ...`
- Not relative: `from ..config.base import ...`

### Async Errors

- All bot handlers must be async
- Use `asyncio.to_thread()` for sync operations (DB, file I/O)
- Don't mix sync and async incorrectly

### Test Failures

- Check mocks are properly configured
- Verify async fixtures use `@pytest.mark.asyncio`
- Use `tmp_path` for file operations
- Clean up resources (close DBs, dispose engines)

## Performance Considerations

### Query Optimization

- Always include LIMIT clause (max 100)
- Fetch only needed columns
- Use indexes on frequently queried columns
- Monitor slow queries in audit logs

### LLM Cost Optimization

- Small-talk detection avoids unnecessary API calls
- Cache schema introspection results
- Short prompts with essential context only
- Retry only on transient failures

### Memory Management

- Don't load entire result sets into memory
- Use `fetchmany(50)` not `fetchall()`
- Dispose database engines after use
- Truncate long answers to word limits

## Future Enhancement Ideas

When adding features, consider:

- Backwards compatibility with existing env vars
- Graceful degradation if feature disabled
- Security implications (especially for database access)
- Test coverage for new code paths
- Documentation updates (README, docstrings)
- User experience (clear error messages, helpful feedback)

## Questions to Ask Before Committing

1. Did I add tests for new functionality?
2. Did I handle errors gracefully (no details to users)?
3. Did I update relevant docstrings and type hints?
4. Did I run `uv run ruff format` and `uv run ruff check`?
5. Did I test locally before pushing?
6. Did I update .env.example if I added env vars?
7. Did I ensure backwards compatibility?

---

**Remember**: This bot handles sensitive data and provides database access. Security, reliability, and user experience are paramount. When in doubt, err on the side of caution.
