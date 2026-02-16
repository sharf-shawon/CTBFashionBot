#!/usr/bin/env python
from dataclasses import dataclass

from telegram import ReplyKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config.base import (
    ADMIN_IDS,
    AUDIT_DB_PATH,
    LOGGER,
    PROFANITY_FILTER_ENABLED,
    SMALLTALK_ENABLED,
    TG_BOT_NAME,
    TG_BOT_TOKEN,
    USER_IDS,
)
from services.access_control import AccessControl
from services.audit_repo import AuditRepository
from services.inspire_service import InspireService
from services.query_service import QueryService
from utils.format import markdown_to_html
from utils.profanity import contains_profanity, get_random_profanity_warning
from utils.responses import (
    get_random_access_denied,
    get_random_error,
    get_random_waiting,
)
from utils.sanitize import (
    is_suspicious_sql_pattern,
    sanitize_for_markdown,
    sanitize_message,
    sanitize_user_id,
)
from utils.smalltalk import handle_small_talk, is_small_talk


@dataclass(frozen=True)
class AppServices:
    audit_repo: AuditRepository
    access_control: AccessControl
    query_service: QueryService
    inspire_service: InspireService


def build_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["/start", "/help", "/inspire"],
            ["/adduser", "/remuser", "/listuser"],
            ["/addadmin", "/remadmin", "/listadmin"],
        ],
        resize_keyboard=True,
        input_field_placeholder="Ask a question",
    )


def blocked_message(user_id: int) -> str:
    return (
        f"{get_random_access_denied()} "
        f"This bot is for {TG_BOT_NAME} members. "
        f"Ask an admin to add your ID ({user_id}) if you should have access."
    )


def parse_user_id(argument: str | None) -> int | None:
    """Parse and sanitize user ID from command argument."""
    if not argument:
        return None
    return sanitize_user_id(argument)


def format_numbered_list(
    user_ids: list[int],
    label: str,
    protected_ids: set[int] | None = None,
) -> str:
    if not user_ids:
        return f"No {label} found."
    protected_ids = protected_ids or set()
    lines = [
        f"{idx + 1}. {user_id}{' (P)' if user_id in protected_ids else ''}"
        for idx, user_id in enumerate(user_ids)
    ]
    note = "\n\n(P) = Permanent, cannot be removed." if protected_ids else ""
    return f"{label.title()}:\n" + "\n".join(lines) + note


def resolve_user_reference(argument: str | None, user_ids: list[int]) -> int | None:
    if not argument:
        return None
    argument = argument.strip()
    if argument.isdigit():
        index = int(argument)
        if 1 <= index <= len(user_ids):
            return user_ids[index - 1]
    return sanitize_user_id(argument)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    services: AppServices = context.application.bot_data["services"]
    if not await services.access_control.is_allowed(user.id):
        await update.message.reply_text(blocked_message(user.id))
        return
    await update.message.reply_text(
        f"Hi {user.first_name or 'there'}! Ask me a data question.",
        reply_markup=build_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    services: AppServices = context.application.bot_data["services"]
    if not await services.access_control.is_allowed(user.id):
        await update.message.reply_text(blocked_message(user.id))
        return
    await update.message.reply_text(
        "📊 *Available Commands*\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/inspire - Get a sample question based on your data\n"
        "/adduser <id> - Add a user (admin only)\n"
        "/remuser <id|number> - Remove a user (admin only)\n"
        "/listuser - List users (admin only)\n"
        "/addadmin <id> - Add an admin (admin only)\n"
        "/remadmin <id|number> - Remove an admin (admin only)\n"
        "/listadmin - List admins (admin only)\n\n"
        "💬 Just ask any question about your data!",
        parse_mode="Markdown",
        reply_markup=build_keyboard(),
    )


async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    services: AppServices = context.application.bot_data["services"]
    if not await services.access_control.is_admin(user.id):
        await update.message.reply_text(blocked_message(user.id))
        return
    target_id = parse_user_id(context.args[0] if context.args else None)
    if target_id is None:
        await update.message.reply_text("Usage: /adduser <user_id>")
        return
    await services.access_control.add_user(target_id, user.id)
    await update.message.reply_text(f"User {target_id} added.")


async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    services: AppServices = context.application.bot_data["services"]
    if not await services.access_control.is_admin(user.id):
        await update.message.reply_text(blocked_message(user.id))
        return
    target_id = parse_user_id(context.args[0] if context.args else None)
    if target_id is None:
        await update.message.reply_text("Usage: /addadmin <user_id>")
        return
    await services.access_control.add_admin(target_id, user.id)
    await update.message.reply_text(f"Admin {target_id} added.")


async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    services: AppServices = context.application.bot_data["services"]
    if not await services.access_control.is_admin(user.id):
        await update.message.reply_text(blocked_message(user.id))
        return
    user_ids = await services.access_control.list_users()
    target_id = resolve_user_reference(context.args[0] if context.args else None, user_ids)
    if target_id is None:
        await update.message.reply_text("Usage: /remuser <user_id|number>")
        return
    result = await services.access_control.remove_user_checked(target_id)
    if result.removed:
        await update.message.reply_text(f"User {target_id} removed.")
        return
    if result.reason == "env_protected":
        await update.message.reply_text("(P) = Permanent, cannot be removed.")
        return
    if result.reason == "not_user":
        await update.message.reply_text("That ID belongs to an admin. Use /remadmin instead.")
        return
    await update.message.reply_text(f"User {target_id} was not found.")


async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    services: AppServices = context.application.bot_data["services"]
    if not await services.access_control.is_admin(user.id):
        await update.message.reply_text(blocked_message(user.id))
        return
    admin_ids = await services.access_control.list_admins()
    target_id = resolve_user_reference(context.args[0] if context.args else None, admin_ids)
    if target_id is None:
        await update.message.reply_text("Usage: /remadmin <user_id|number>")
        return
    result = await services.access_control.remove_admin_checked(target_id)
    if result.removed:
        await update.message.reply_text(f"Admin {target_id} removed.")
        return
    if result.reason == "env_protected":
        await update.message.reply_text("(P) = Permanent, cannot be removed.")
        return
    if result.reason == "not_admin":
        await update.message.reply_text("That ID is not an admin.")
        return
    await update.message.reply_text(f"Admin {target_id} was not found.")


async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    services: AppServices = context.application.bot_data["services"]
    if not await services.access_control.is_admin(user.id):
        await update.message.reply_text(blocked_message(user.id))
        return
    user_ids = await services.access_control.list_users()
    protected_ids = set(USER_IDS)
    await update.message.reply_text(
        format_numbered_list(user_ids, "users", protected_ids=protected_ids)
    )


async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    services: AppServices = context.application.bot_data["services"]
    if not await services.access_control.is_admin(user.id):
        await update.message.reply_text(blocked_message(user.id))
        return
    admin_ids = await services.access_control.list_admins()
    protected_ids = set(ADMIN_IDS)
    await update.message.reply_text(
        format_numbered_list(admin_ids, "admins", protected_ids=protected_ids)
    )


async def inspire(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return a sample question based on database schema."""
    user = update.effective_user
    if not user or not update.message:
        return
    services: AppServices = context.application.bot_data["services"]
    if not await services.access_control.is_allowed(user.id):
        await update.message.reply_text(blocked_message(user.id))
        return
    question = services.inspire_service.generate_question()
    if question:
        # Sanitize question for safe Markdown display
        safe_question = sanitize_for_markdown(question)
        await update.message.reply_text(
            f"💡 *Try this:*\n\n{safe_question}\n\n"
            f"_Feel free to ask similar questions or modify this one!_",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "I couldn't generate a sample question right now. Try asking about your data directly!"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    services: AppServices = context.application.bot_data["services"]
    if not await services.access_control.is_allowed(user.id):
        await update.message.reply_text(blocked_message(user.id))
        return

    raw_question = update.message.text or ""

    # Sanitize user input (defense in depth)
    question = sanitize_message(raw_question)

    if not question:
        LOGGER.warning(f"Empty question from user {user.id} after sanitization")
        await update.message.reply_text("Please send a valid question.")
        return

    # Log original vs sanitized for debugging
    if raw_question != question:
        LOGGER.debug(
            f"User {user.id} input sanitized: "
            f"original={raw_question[:100]}, sanitized={question[:100]}"
        )

    # Check for suspicious SQL patterns (defense in depth)
    if is_suspicious_sql_pattern(question):
        LOGGER.warning(f"Suspicious SQL pattern from user {user.id}: {question[:100]}")
        return

    # Check for profanity if enabled
    if PROFANITY_FILTER_ENABLED and contains_profanity(question):
        response = get_random_profanity_warning()
        await update.message.reply_text(response)
        return

    # Check for small talk if enabled
    if SMALLTALK_ENABLED and is_small_talk(question):
        response = handle_small_talk(question)
        await update.message.reply_text(response)
        return

    # Process as data query
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    placeholder = await update.message.reply_text(get_random_waiting())

    try:
        result = await services.query_service.answer_question(user.id, question)
        # Convert Markdown to HTML for Telegram rendering
        html_answer = markdown_to_html(result.answer)
        await placeholder.edit_text(html_answer, parse_mode="HTML")
    except Exception as exc:  # pragma: no cover - safe fallback
        LOGGER.exception("Message handling error: %s", exc)
        await placeholder.edit_text(get_random_error())


async def initialize_services(app: Application) -> None:
    audit_repo = AuditRepository(str(AUDIT_DB_PATH))
    await audit_repo.init()
    access_control = AccessControl(audit_repo, ADMIN_IDS, USER_IDS)
    await access_control.seed_from_env()
    query_service = QueryService(audit_repo)
    inspire_service = InspireService(query_service._schema_service)
    app.bot_data["services"] = AppServices(
        audit_repo=audit_repo,
        access_control=access_control,
        query_service=query_service,
        inspire_service=inspire_service,
    )


def main() -> None:
    if not TG_BOT_TOKEN:
        raise RuntimeError("TG_BOT_TOKEN is required")
    application = Application.builder().token(TG_BOT_TOKEN).post_init(initialize_services).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("inspire", inspire))
    application.add_handler(CommandHandler("adduser", add_user))
    application.add_handler(CommandHandler("remuser", remove_user))
    application.add_handler(CommandHandler("listuser", list_users))
    application.add_handler(CommandHandler("addadmin", add_admin))
    application.add_handler(CommandHandler("remadmin", remove_admin))
    application.add_handler(CommandHandler("listadmin", list_admins))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
