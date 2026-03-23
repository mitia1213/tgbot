import asyncio
import logging
from datetime import datetime

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

from config import BOT_TOKEN
from database import init_db, get_session
from handlers import start, profile, training, nutrition
from utils.calculators import check_nutrition_reminder

# Настройка логирования, чтобы видеть, что происходит под капотом
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """
    Выполняется после запуска бота. Устанавливает команды меню и создает таблицы.
    """
    # Устанавливаем кнопку "Menu" в интерфейсе Telegram
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("profile", "Мой профиль"),
        BotCommand("add_weight", "Записать вес"),
        BotCommand("remind", "Настроить напоминания"),
    ]
    await application.bot.set_my_commands(commands)

    # Инициализация базы данных (создание таблиц, если их нет)
    await init_db()
    logger.info("Бот успешно запущен и готов к работе!")


async def error_handler(update: Update, context) -> None:
    """
    Ловим все ошибки, чтобы бот не падал молча.
    Пишем в лог, пользователю отправляем вежливое сообщение.
    """
    logger.error(msg="Exception:", exc_info=context.error)
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="😕 Произошла техническая ошибка. Мы уже чиним! Попробуйте позже.",
        )


def main() -> None:
    """
    Точка входа. Собираем приложение как конструктор.
    """
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Регистрируем обработчики (handlers)
    # Разбиваем логику на модули, чтобы не было "простыни" из кода
    application.add_handler(start.conv_handler)          # Регистрация профиля
    application.add_handler(profile.profile_handler)     # Просмотр профиля
    application.add_handler(training.training_handler)   # Дневник тренировок
    application.add_handler(nutrition.nutrition_handler) # Дневник питания

    # Простые команды
    application.add_handler(CommandHandler("add_weight", profile.add_weight))
    application.add_handler(CommandHandler("remind", profile.set_reminder))

    # Глобальный обработчик ошибок
    application.add_error_handler(error_handler)

    # Запускаем бота (polling)
    logger.info("Бот запущен. Начинаем прослушивание...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()