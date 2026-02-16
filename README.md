# CTBFashion Bot

A production-ready Telegram bot that translates natural language questions into safe SQL queries using LLM (OpenRouter). Query your PostgreSQL database conversationally with built-in access control, audit logging, and safety features.

## Features

- 🤖 **Natural Language to SQL** — Ask questions in plain English, get data-driven answers
- 🔒 **Access Control** — Admin and user roles with configurable permissions
- 📊 **Database Safety** — Read-only queries, table/column restrictions, soft-delete awareness
- 💰 **Currency Formatting** — Configurable currency symbols (e.g., $, €, Tk)
- 🛡️ **Profanity Filter** — Maintains professional conversations
- 💬 **Smart Responses** — Small-talk detection, randomized messages, off-topic handling
- 📝 **Audit Logging** — Complete query history with SQLite persistence
- 🚫 **Result Limits** — Max 100 items per query, prevents performance issues
- 🐳 **Docker Ready** — Production deployment with docker-compose

## Requirements

- Python 3.13+
- PostgreSQL database (or SQLite for testing)
- Telegram Bot Token ([create one](https://t.me/BotFather))
- OpenRouter API Key ([get one](https://openrouter.ai/))

## Quick Start

### 1. Clone & Install

```bash
git clone <your-repo>
cd CTBFashionBot

# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials:
# - TG_BOT_TOKEN (required)
# - OPENROUTER_API_KEY (required)
# - OPENROUTER_MODEL (required)
# - DATABASE_URL (required)
# - ADMIN_IDS (your Telegram user ID)
```

### 3. Run

```bash
# Local development
uv run src/main.py

# Or with Docker
docker compose up --build
```

## Development

### Project Structure

```
src/
├── config/          # Environment and configuration
├── services/        # Core business logic
│   ├── audit_repo.py      # SQLite audit logging
│   ├── access_control.py  # User permissions
│   ├── schema_service.py  # DB schema introspection
│   ├── sql_guard.py       # Query validation
│   ├── llm_service.py     # OpenRouter integration
│   ├── query_service.py   # Query orchestration
│   └── inspire_service.py # Sample question generator
├── utils/           # Helpers (responses, profanity, smalltalk)
└── main.py          # Telegram bot handlers
tests/               # Pytest test suite
storage/
├── data/            # SQLite audit DB
└── logs/            # Application logs
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_profanity.py

# Run with coverage
uv run pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Fix linting issues
uv run ruff check --fix

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TG_BOT_TOKEN` | ✅ | — | Telegram bot token from @BotFather |
| `OPENROUTER_API_KEY` | ✅ | — | OpenRouter API key |
| `OPENROUTER_MODEL` | ✅ | — | LLM model (e.g., `openrouter/aurora-alpha`) |
| `DATABASE_URL` | ❌ | SQLite | PostgreSQL connection string |
| `ADMIN_IDS` | ❌ | `[]` | Comma-separated Telegram user IDs |
| `USER_IDS` | ❌ | `[]` | Comma-separated Telegram user IDs |
| `DATABASE_ALLOWED_TABLES` | ❌ | All | Restrict to specific tables |
| `DATABASE_RESTRICTED_TABLES` | ❌ | None | Block specific tables |
| `DATABASE_EXCLUDED_COLUMNS` | ❌ | None | Hide columns (e.g., passwords) |
| `CURRENCY_SYMBOL` | ❌ | `$` | Currency symbol for formatting |
| `SMALLTALK_ENABLED` | ❌ | `true` | Handle greetings/farewells |
| `PROFANITY_FILTER_ENABLED` | ❌ | `true` | Filter offensive language |
| `RESPONSE_MAX_WORDS` | ❌ | `30` | Answer word limit (skip for lists) |
| `LLM_MAX_RETRIES` | ❌ | `3` | Retry attempts on errors |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level |
| `DEBUG` | ❌ | `false` | Debug mode |

### Database Restrictions Example

```bash
# Only allow queries on these tables
DATABASE_ALLOWED_TABLES=orders,products,customers

# Block these tables completely
DATABASE_RESTRICTED_TABLES=admin_logs,internal_notes

# Hide sensitive columns (excluded from SELECT *)
DATABASE_EXCLUDED_COLUMNS=password_hash,secret_key,api_token
```

## Usage

### Bot Commands

- `/start` — Introduction and keyboard
- `/help` — List all commands with descriptions
- `/inspire` — Get sample questions based on your schema
- `/adduser <user_id>` — Add user (admin only)
- `/remuser <user_id>` — Remove user (admin only)

### Example Queries

```
User: "How many orders did we get today?"
Bot: "Today we received 47 orders."

User: "List 10 recent products"
Bot: [Lists 10 products with full details]

User: "Show me all invoices over $1000"
Bot: [Lists matching invoices]

User: "What's the average order value?"
Bot: "The average order value is $237.50."
```

## Deployment

### Docker Compose (Recommended)

```bash
# Production deployment
docker compose up -d

# View logs
docker compose logs -f bot

# Restart
docker compose restart bot
```

### Coolify / Cloud Platforms

1. Set required environment variables in platform UI
2. Deploy using docker-compose.yml
3. Ensure volumes are mounted for persistent data

## Security Features

- ✅ **Read-only queries** — No INSERT/UPDATE/DELETE/DDL allowed
- ✅ **SQL validation** — Guards against table/column access violations
- ✅ **Column redaction** — Sensitive columns never returned
- ✅ **Soft-delete awareness** — Automatically excludes deleted records
- ✅ **Rate limits** — Max 100 items per query
- ✅ **Access control** — Admin/user role separation
- ✅ **Audit trail** — All queries logged with user ID

## Troubleshooting

**Bot doesn't respond:**
- Check `TG_BOT_TOKEN` is correct
- Verify bot is running: `docker compose ps`
- Check logs: `docker compose logs bot`

**Database connection fails:**
- Verify `DATABASE_URL` format: `postgres://user:pass@host:port/db`
- Ensure database is accessible from bot container
- Check network connectivity

**LLM errors (502):**
- OpenRouter API may be down (check status page)
- Bot will retry 3 times automatically
- Users see "couldn't process that right now" on failure

## License

MIT

## Support

For issues or questions, open a GitHub issue or contact the maintainer.
