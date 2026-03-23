from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from database import get_session, User

# Состояния для разговора
ASK_NAME, ASK_GENDER, ASK_AGE, ASK_HEIGHT, ASK_WEIGHT, ASK_ACTIVITY, ASK_GOAL = range(7)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Приветствие и проверка регистрации.
    """
    user_id = update.effective_user.id
    async with get_session() as session:
        user = await session.get(User, user_id)
        if user:
            # Уже зарегистрирован
            await update.message.reply_text(
                f"С возвращением, {user.name}! 👋\n"
                f"Что сегодня будем делать? Используй меню ниже.",
                reply_markup=main_menu_keyboard()
            )
            return ConversationHandler.END
        else:
            # Начинаем регистрацию
            await update.message.reply_text(
                "🏋️ Привет! Я твой персональный фитнес-помощник.\n"
                "Давай познакомимся. Как тебя зовут?",
                reply_markup=ReplyKeyboardRemove(),
            )
            return ASK_NAME

async def ask_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text
    keyboard = [["Мужской", "Женский"]]
    await update.message.reply_text(
        "Отлично! Теперь укажи свой пол:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return ASK_GENDER

# ... аналогично другие шаги: возраст, рост, вес, активность, цель

async def save_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Сохраняем профиль и рассчитываем КБЖУ.
    """
    goal = update.message.text  # "Похудение", "Поддержание" или "Набор"
    user_data = context.user_data
    user_data['goal'] = goal

    # Рассчитываем норму калорий (упрощенная формула Миффлина-Сан-Жеора)
    bmr = 0
    if user_data['gender'] == "Мужской":
        bmr = 10 * user_data['weight'] + 6.25 * user_data['height'] - 5 * user_data['age'] + 5
    else:
        bmr = 10 * user_data['weight'] + 6.25 * user_data['height'] - 5 * user_data['age'] - 161

    # Корректировка на активность
    activity_factors = {
        "Минимальная": 1.2,
        "Низкая": 1.375,
        "Средняя": 1.55,
        "Высокая": 1.725,
        "Очень высокая": 1.9,
    }
    calories = bmr * activity_factors.get(user_data['activity'], 1.2)

    # Корректировка на цель
    if goal == "Похудение":
        calories -= 300
    elif goal == "Набор":
        calories += 300

    # Сохраняем в БД
    async with get_session() as session:
        user = User(
            id=update.effective_user.id,
            name=user_data['name'],
            gender=user_data['gender'],
            age=user_data['age'],
            height=user_data['height'],
            weight=user_data['weight'],
            activity=user_data['activity'],
            goal=goal,
            daily_calories=int(calories),
        )
        session.add(user)
        await session.commit()

    await update.message.reply_text(
        f"✅ Профиль сохранен!\n\n"
        f"Твоя дневная норма: {int(calories)} ккал.\n"
        f"Помни: это базовая цифра. Слушай свой организм.\n\n"
        f"Теперь я готов помогать тебе каждый день!",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END

# Собираем ConversationHandler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_gender)],
        ASK_GENDER: [MessageHandler(filters.Regex("^(Мужской|Женский)$"), ask_age)],
        # ... остальные состояния
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)