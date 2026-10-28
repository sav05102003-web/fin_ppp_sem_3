"""Обработчики Telegram и периодическая доставка сохранённых таймеров."""

import logging

from telegram import BotCommand, ReplyKeyboardMarkup, Update
from telegram.error import Forbidden, NetworkError, RetryAfter, TelegramError
from telegram.ext import (
    Application, ContextTypes, MessageHandler, filters,
)
from telegram.request import BaseRequest

from src.assistant import CookingAssistant


LOGGER = logging.getLogger(__name__)
BUTTON_COMMANDS = {
    "🍽 Рецепты": "/find", "📅 Меню": "/menu",
    "🛒 Покупки": "/shopping", "⏱ Таймеры": "/timers",
    "🥗 Питание": "/diet", "❔ Помощь": "/help",
}
KEYBOARD = ReplyKeyboardMarkup(
    [["🍽 Рецепты", "📅 Меню"], ["🛒 Покупки", "⏱ Таймеры"],
     ["🥗 Питание", "❔ Помощь"]],
    resize_keyboard=True,
    input_field_placeholder="Например: рис, морковь, перец",
)
COMMANDS = [
    ("start", "Открыть главное меню"), ("help", "Справка по командам"),
    ("find", "Найти рецепты по ингредиентам"),
    ("recipe", "Посмотреть рецепт по ID"), ("diet", "Тип питания"),
    ("exclude", "Исключить продукты"), ("profile", "Мои предпочтения"),
    ("tips", "Рекомендации по питанию"), ("plan", "Составить меню"),
    ("menu", "Меню текущей недели"), ("clear_menu", "Очистить меню недели"),
    ("shopping", "Список покупок"), ("buy", "Отметить покупку"),
    ("timer", "Создать таймер"), ("timers", "Мои таймеры"),
    ("cancel_timer", "Отменить таймер"),
]


def split_message(text: str, limit: int = 3900) -> list[str]:
    """Разбить длинный ответ по строкам с запасом к лимиту Telegram."""
    chunks = []
    while len(text) > limit:
        boundary = text.rfind("\n", 0, limit)
        if boundary <= 0:
            boundary = limit
        chunks.append(text[:boundary])
        text = text[boundary:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


async def handle_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Обработать текст и команду только из личного чата."""
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if message is None or user is None or chat is None:
        return
    if chat.type != "private":
        await message.reply_text(
            "Откройте личный чат с ботом и отправьте /start."
        )
        return
    if message.text is None:
        await message.reply_text(
            "Отправьте продукты текстом или откройте /help."
        )
        return
    assistant = context.bot_data["assistant"]
    text = BUTTON_COMMANDS.get(message.text, message.text)
    response = assistant.execute(user.id, chat.id, text)
    for part in split_message(response):
        await message.reply_text(part, reply_markup=KEYBOARD)


async def deliver_timers(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправить готовые таймеры и сохранить результат доставки."""
    assistant = context.bot_data["assistant"]
    storage = assistant.storage
    for timer in storage.due_timers(assistant.now()):
        try:
            await context.bot.send_message(
                chat_id=timer["chat_id"],
                text=(f"⏱ Таймер #{timer['id']}: "
                      f"{timer['title']}. Время вышло!"),
            )
        except Forbidden:
            storage.finish_timer(timer["id"], "failed")
            LOGGER.warning("Таймер %s: бот заблокирован.", timer["id"])
        except RetryAfter as error:
            delay = error.retry_after
            seconds = (delay.total_seconds()
                       if hasattr(delay, "total_seconds") else delay)
            storage.retry_timer(
                timer["id"], assistant.now() + max(0, seconds - 30))
        except NetworkError:
            storage.retry_timer(timer["id"], assistant.now())
            LOGGER.warning(
                "Таймер %s: временная ошибка доставки.", timer["id"])
        except TelegramError:
            storage.finish_timer(timer["id"], "failed")
            LOGGER.warning(
                "Таймер %s: Telegram отклонил уведомление.", timer["id"])
        else:
            storage.finish_timer(timer["id"], "sent")


async def post_init(application: Application) -> None:
    """Зарегистрировать команды и проверять таймеры раз в секунду."""
    await application.bot.set_my_commands([
        BotCommand(command, description) for command, description in COMMANDS
    ])
    application.job_queue.run_repeating(
        deliver_timers, interval=1, first=1, name="saved-cooking-timers",
        job_kwargs={"max_instances": 1, "coalesce": True},
    )


async def handle_error(
    update: object, context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Сообщить об ошибке без вывода токена, текста сообщения и профиля."""
    LOGGER.error("Ошибка обработчика: %s", type(context.error).__name__)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Не удалось выполнить действие. "
                "Попробуйте ещё раз или откройте /help."
            )
        except TelegramError:
            LOGGER.warning("Не удалось отправить сообщение об ошибке.")


def build_application(
    token: str, assistant: CookingAssistant,
    request: BaseRequest | None = None,
) -> Application:
    """Собрать приложение без сетевых запросов до его запуска."""
    builder = (
        Application.builder().token(token).post_init(post_init)
        .concurrent_updates(False)
    )
    if request is not None:
        builder = builder.request(request)
    application = builder.build()
    if application.job_queue is None:
        raise RuntimeError(
            "Установите зависимости: "
            "python -m pip install -r requirements.txt")
    application.bot_data["assistant"] = assistant
    application.add_handler(MessageHandler(filters.ALL, handle_message))
    application.add_error_handler(handle_error)
    return application
