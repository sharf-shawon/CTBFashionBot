#!/usr/bin/env python
from dataclasses import dataclass

from telegram import ReplyKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

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
from utils.profanity import contains_profanity, get_random_profanity_warning
from utils.responses import (
    get_random_access_denied,
    get_random_error,
    get_random_waiting,
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
        [["/start", "/help", "/inspire"], ["/adduser", "/remuser"]],
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
    if not argument:
        return None
    argument = argument.strip()
    if not argument.isdigit():
        return None
    return int(argument)


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
        "/remuser <id> - Remove a user (admin only)\n\n"
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


async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    services: AppServices = context.application.bot_data["services"]
    if not await services.access_control.is_admin(user.id):
        await update.message.reply_text(blocked_message(user.id))
        return
    target_id = parse_user_id(context.args[0] if context.args else None)
    if target_id is None:
        await update.message.reply_text("Usage: /remuser <user_id>")
        return
    removed = await services.access_control.remove_user(target_id)
    if removed:
        await update.message.reply_text(f"User {target_id} removed.")
    else:
        await update.message.reply_text(f"User {target_id} was not found.")


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
        await update.message.reply_text(
            f"💡 *Try this:*\n\n{question}\n\n"
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

    question = update.message.text or ""

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
        await placeholder.edit_text(result.answer)
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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
