"""
bot_handlers.py
Telegram bot handlers for English Tutor Bot
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import (
    ADMIN_TELEGRAM_ID,
    ALLOWED_USERS,
    BETA_MESSAGE,
    GREETING_RESPONSE,
    CASUAL_RESPONSE,
    THANKS_RESPONSE,
    DISCLAIMER,
    ABUSE_PENALTY_TOKENS
)
from database import (
    get_user,
    create_user,
    update_user_grade,
    update_user_textbook,
    increment_message_count,
    save_conversation,
    get_recent_conversations,
    delete_user_data,
    add_tokens,
    get_token_stats,
    get_token_balance,
    deduct_tokens,
    grant_tokens,
    log_usage,
    get_usage_report,
    get_all_users,
    get_user_stats_summary
)
from classifier import classify_intent
from prompt_builder import build_full_prompt
from yandex_api import call_yandex_gpt

logger = logging.getLogger(__name__)
router = Router()


# ============================================================================
# ACCESS CONTROL HELPER
# ============================================================================

def is_whitelisted(telegram_id: int) -> bool:
    """Check if user is whitelisted (if whitelist is enabled)"""
    if not ALLOWED_USERS:  # Empty list = allow all
        return True
    return telegram_id in ALLOWED_USERS

def is_admin(telegram_id: int) -> bool:
    """Check if user is admin"""
    return telegram_id == ADMIN_TELEGRAM_ID


# ============================================================================
# /start COMMAND - Setup grade and textbook
# ============================================================================

@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Handle /start command
    Shows grade selection buttons regardless of existing setup
    """
    user_id = message.from_user.id
    
    # Check whitelist
    if not is_whitelisted(user_id):
        await message.answer(BETA_MESSAGE)
        return
    
    # Create user if doesn't exist
    user = await get_user(user_id)
    if not user:
        await create_user(user_id)
        logger.info(f"New user registered: {user_id}")
    
    # Show grade selection keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 класс", callback_data="grade_1"),
         InlineKeyboardButton(text="2 класс", callback_data="grade_2"),
         InlineKeyboardButton(text="3 класс", callback_data="grade_3")],
        [InlineKeyboardButton(text="4 класс", callback_data="grade_4"),
         InlineKeyboardButton(text="5 класс", callback_data="grade_5"),
         InlineKeyboardButton(text="6 класс", callback_data="grade_6")],
        [InlineKeyboardButton(text="7 класс", callback_data="grade_7"),
         InlineKeyboardButton(text="8 класс", callback_data="grade_8"),
         InlineKeyboardButton(text="9 класс", callback_data="grade_9")],
        [InlineKeyboardButton(text="10 класс", callback_data="grade_10"),
         InlineKeyboardButton(text="11 класс", callback_data="grade_11")]
    ])
    
    await message.answer(
        "Привет! Я твой English tutor.\n\n"
        "Выбери свой класс:",
        reply_markup=keyboard
    )


@router.callback_query(lambda c: c.data.startswith("grade_"))
async def process_grade_selection(callback: CallbackQuery):
    """
    Handle grade button click
    Save grade and show textbook selection
    """
    user_id = callback.from_user.id
    grade = int(callback.data.split("_")[1])
    
    # Save grade to database
    await update_user_grade(user_id, grade)
    logger.info(f"User {user_id} selected grade {grade}")
    
    # Show textbook selection
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Spotlight", callback_data="textbook_spotlight")],
        [InlineKeyboardButton(text="Unknown edition", callback_data="textbook_unknown")]
    ])
    
    await callback.message.edit_text(
        f"Класс {grade} выбран!\n\n"
        "Теперь выбери учебник:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("textbook_"))
async def process_textbook_selection(callback: CallbackQuery):
    """
    Handle textbook button click
    Save textbook and confirm setup complete
    """
    user_id = callback.from_user.id
    textbook_type = callback.data.split("_")[1]
    
    # Get user's grade
    user = await get_user(user_id)
    grade = user['grade']
    
    # Format textbook name
    if textbook_type == "spotlight":
        textbook = f"Spotlight Grade {grade}"
    else:
        textbook = "Unknown edition (FGOS general)"
    
    # Save to database
    await update_user_textbook(user_id, textbook)
    logger.info(f"User {user_id} selected textbook: {textbook}")
    
    await callback.message.edit_text(
        f"Настройка завершена!\n"
        f"Класс: {grade}\n"
        f"Учебник: {textbook}\n\n"
        "Теперь можешь задавать вопросы по английскому языку.\n"
        "Используй /help для справки."
    )
    await callback.answer()


# ============================================================================
# /help COMMAND - Bot instructions
# ============================================================================

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show help information"""
    help_text = """📚 **Как использовать бота:**

**Настройка:**
• /start - Выбрать класс и учебник

**Обучение:**
• Задавай вопросы на русском или английском
• Бот поможет с грамматикой, словами, упражнениями
• Бот НЕ делает домашнюю работу, но помогает понять как

**Команды:**
• /stats - Посмотреть баланс токенов
• /report - Отчёт за 7 дней (для родителей)
• /reset - Сбросить профиль
• /help - Показать эту справку
• /id - Показать свой ID (для доступа)

**О токенах:**
• Каждый вопрос расходует токены
• Баланс показывается в /stats
• При достижении 0 токенов бот остановится

**Поддержка:**
• Вопросы или проблемы? Напиши администратору"""
    
    await message.answer(help_text)


# ============================================================================
# /id COMMAND - Show user's Telegram ID
# ============================================================================

@router.message(Command("id"))
async def cmd_id(message: Message):
    """Show user's Telegram ID for whitelist requests"""
    user_id = message.from_user.id
    await message.answer(
        f"🆔 Твой Telegram ID:\n\n"
        f"`{user_id}`\n\n"
        f"Отправь этот ID администратору для получения доступа."
    )


# ============================================================================
# /stats COMMAND - Show token usage
# ============================================================================

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """
    Handle /stats command
    Display user's token usage statistics with xxx/yyy format
    """
    user_id = message.from_user.id
    
    # Check whitelist
    if not is_whitelisted(user_id):
        await message.answer(BETA_MESSAGE)
        return
    
    # Get token statistics
    stats = await get_token_stats(user_id)
    
    # Calculate approximate cost (at 0.40 RUB per 1000 tokens, non-discount rate)
    cost_today = (stats['tokens_today'] / 1000) * 0.40
    cost_total = (stats['tokens_total'] / 1000) * 0.40
    
    # Calculate initial grant (for xxx/yyy format)
    from config import INITIAL_TOKEN_GRANT
    consumed = stats['tokens_total']
    remaining = stats['token_balance']
    total_granted = consumed + remaining
    
    await message.answer(
        f"📊 Статистика использования:\n\n"
        f"💰 Баланс токенов: {remaining:,}\n"
        f"📈 Использовано: {consumed:,} / {total_granted:,}\n\n"
        f"Сегодня:\n"
        f"├─ Сообщений: {stats['messages_today']}\n"
        f"├─ Токенов: {stats['tokens_today']:,}\n"
        #f"└─ Стоимость: {cost_today:.2f} ₽\n\n" #commented so that user should not see costs
        f"Всего:\n"
        f"├─ Токенов: {stats['tokens_total']:,}\n"
       # f"└─ Стоимость: {cost_total:.2f} ₽" #commented so that user should not see costs
    )


# ============================================================================
# /report COMMAND - Detailed usage report for parents
# ============================================================================

@router.message(Command("report"))
async def cmd_report(message: Message):
    """
    Handle /report command
    Show detailed 7-day usage breakdown for parental monitoring
    """
    user_id = message.from_user.id
    
    # Check whitelist
    if not is_whitelisted(user_id):
        await message.answer(BETA_MESSAGE)
        return
    
    # Get 7-day report from audit log
    report = await get_usage_report(user_id, days=7)
    
    if report['total_messages'] == 0:
        await message.answer("📊 Отчёт пуст. Нет активности за последние 7 дней.")
        return
    
    # Build report message
    report_text = f"📊 Отчёт за последние 7 дней:\n\n"
    report_text += f"Всего:\n"
    report_text += f"├─ Сообщений: {report['total_messages']}\n"
    report_text += f"├─ Обучающих: {report['total_teaching']}\n"
    report_text += f"├─ Casual чатов: {report['total_casual']}\n"
    
    
    report_text += f"└─ Токенов: {report['total_tokens']:,}\n\n"
    
    # Add daily breakdown
    if report['daily_breakdown']:
        report_text += "По дням:\n"
        for day in report['daily_breakdown'][:7]:  # Last 7 days
            date = day['date']
            tokens = day['tokens'] or 0
            teaching = day['teaching_count'] or 0
            casual = day['casual_count'] or 0
            abuse = day['abuse_count'] or 0
            
            report_text += f"\n{date}:\n"
            report_text += f"  ├─ Обучающих: {teaching}\n"
            report_text += f"  ├─ Casual: {casual}\n"
            report_text += f"  └─ Токенов: {tokens:,}\n"
    
    # Calculate cost
    cost_total = (report['total_tokens'] / 1000) * 0.40
    
    await message.answer(report_text)


# ============================================================================
# /reset COMMAND - Delete user data
# ============================================================================

@router.message(Command("reset"))
async def cmd_reset(message: Message):
    """
    Handle /reset command
    Delete all user data and allow fresh setup
    """
    user_id = message.from_user.id
    
    # Check whitelist
    if not is_whitelisted(user_id):
        await message.answer(BETA_MESSAGE)
        return
    
    await delete_user_data(user_id)
    logger.info(f"User {user_id} reset their profile")
    
    await message.answer(
        "Твой профиль сброшен.\n"
        "Баланс токенов сохранён.\n"
        "Используй /start для новой настройки."
    )


# ============================================================================
# ADMIN COMMANDS
# ============================================================================

@router.message(Command("grant"))
async def cmd_grant(message: Message):
    """Admin: Grant tokens to user"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Parse: /grant user_id tokens
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer("Использование: /grant [user_id] [tokens]")
            return
        
        target_user_id = int(parts[1])
        tokens = int(parts[2])
        
        await grant_tokens(target_user_id, tokens)
        await message.answer(f"✅ Выдано {tokens:,} токенов пользователю {target_user_id}")
        logger.info(f"Admin {message.from_user.id} granted {tokens} tokens to {target_user_id}")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    """Admin: Broadcast message to all users"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Extract message after /broadcast
        broadcast_text = message.text.replace("/broadcast", "").strip()
        if not broadcast_text:
            await message.answer("Использование: /broadcast [сообщение]")
            return
        
        users = await get_all_users()
        sent_count = 0
        
        for user in users:
            try:
                from aiogram import Bot
                bot = message.bot
                await bot.send_message(user['telegram_id'], broadcast_text)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send to {user['telegram_id']}: {e}")
        
        await message.answer(f"✅ Сообщение отправлено {sent_count} пользователям")
        logger.info(f"Admin {message.from_user.id} broadcast to {sent_count} users")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command("adminstats"))
async def cmd_adminstats(message: Message):
    """Admin: View overall system stats"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        stats = await get_user_stats_summary()
        
        stats_text = f"📊 Статистика системы:\n\n"
        stats_text += f"👥 Пользователей: {stats['total_users']}\n"
        stats_text += f"🔥 Токенов использовано: {stats['total_tokens_consumed']:,}\n"
        stats_text += f"💰 Токенов осталось: {stats['total_tokens_remaining']:,}\n"
        stats_text += f"📈 Среднее сообщений/день: {stats['avg_messages_today']}\n"
        
        await message.answer(stats_text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


# ============================================================================
# MESSAGE HANDLER - Main conversation flow
# ============================================================================

@router.message(F.text)
async def handle_message(message: Message):
    """
    Main message handler
    
    Flow:
    1. Check whitelist
    2. Check if user exists and has grade/textbook
    3. Check token balance
    4. Classify intent (GREETING/CASUAL/TEACHING)
    5. Check for abuse (apply penalty if detected)
    6. Handle accordingly:
       - GREETING/CASUAL: Template response, no API call
       - TEACHING: Full teaching flow with YandexGPT
    """
    user_id = message.from_user.id
    user_message = message.text
    
    # ========================================================================
    # STEP 0: Check whitelist
    # ========================================================================
    if not is_whitelisted(user_id):
        await message.answer(BETA_MESSAGE)
        return
    
    # ========================================================================
    # STEP 1: Check if user exists and is set up
    # ========================================================================
    user = await get_user(user_id)
    
    if not user:
        # User doesn't exist, create and prompt for setup
        await create_user(user_id)
        await message.answer("Пожалуйста, используй /start для настройки профиля.")
        return
    
    if not user['grade'] or not user['textbook']:
        # User exists but hasn't completed setup
        await message.answer("Пожалуйста, используй /start для настройки профиля.")
        return
    
    # ========================================================================
    # STEP 2: Check token balance
    # ========================================================================
    balance = await get_token_balance(user_id)
    if balance <= 0:
        await message.answer(
            "❌ У тебя закончились токены.\n\n"
            "Свяжись с администратором для пополнения баланса."
        )
        return
    
    # ========================================================================
    # STEP 3: TIER-1 CLASSIFIER - Route message
    # ========================================================================
    intent = await classify_intent(user_message)
    logger.info(f"User {user_id} message classified as: {intent}")
    
    # ========================================================================
    # STEP 4: Check for abuse/sexual content
    # ========================================================================
    # Simple backend detection for common abuse words
    abuse_words = ['fuck', 'shit', 'нахуй', 'блять', 'сука', 'хуй', 'пизда', 'ебать', 'секс', 'sex', 'porn', 'идиот', 'тупой', 'глупый', 'тварь', 'урод', 'придурок', 'дебил', 'кретин', 'мудак', 'уебок', 'сука', 'блять', 'пиздец', 'ебать', 'секс', 'трах', 'ебать', 'сиськи', 'член', 'пизда', 'хуй', 'ебля', 'порно', 'минет', 'оргазм', 'Сука', 'Сучек', 'Сучка', 'Сучара', 'Сучёнышь', 'Пиздёнышь', 'Пиздёнка', 'Пизденка', 'Блять', 'Блядь', 'Конча', 'Залупа', 'Хер', 'Пидорас', 'Пидрилла', 'Ублюдок', 'Хуйня', 'Уеблан', 'Уебок', 'Еблан', 'Падла', 'Хуесос', 'Пидор', 'Гондон', 'Шмонь', 'Шмаль', 'Вертихуй', 'Хуйрилла', 'Шлюха', 'Шмара', 'Выблядок', 'Писька', 'Сиська', 'Соси', 'Сиси', 'Пердак', 'Жопа', 'Попка', 'Писечька', 'Дебил', 'Конченный', 'Трахать', 'Трах', 'Сосалка', 'Давалка', 'Утырок', 'Потрахель', 'Проститутка', 'fuck', 'shit', 'asshole', 'bastard', 'bitch', 'damn', 'cunt', 'dick', 'pussy', 'cock', 'motherfucker', 'bullshit', 'piss', 'crap', 'slut', 'whore', 'wanker', 'douchebag', 'arsehole', 'prick', 'twat', 'bollocks', 'bugger', 'sod', 'bloody', 'говно', 'сволочь', 'гандон', 'долбоёб', 'лох', 'козёл', 'чмо', 'иди на хуй', 'пиздец', 'охуеть', 'выёбываться', 'ёбанько', 'засранец', 'пошел ты', 'asshat', 'asswipe', 'boner', 'dipshit', 'doofus', 'dumbass', 'feck', 'goddamn', 'jeez', 'pecker', 'prick', 'schmuck', 'berk', 'bellend', 'chav', 'git', 'minger', 'munter', 'numpty', 'plonker', 'tosser', 'a$$', 'b!tch', 'f4ck', 'fck', 'fuk', 'sh!t', 'sh17', 'sh1t', '5hit']
    is_abuse = any(word in user_message.lower() for word in abuse_words)
    
    if is_abuse:
        # Silently deduct penalty tokens
        await deduct_tokens(user_id, ABUSE_PENALTY_TOKENS, "abuse_penalty")
        await log_usage(user_id, ABUSE_PENALTY_TOKENS, 'abuse_penalty')
        logger.warning(f"User {user_id} penalized {ABUSE_PENALTY_TOKENS} tokens for abuse")
    
    # ========================================================================
    # HANDLE GREETING - Template response, no API call, don't save
    # ========================================================================
    if intent == "GREETING":
        await message.answer(GREETING_RESPONSE)
        return
    
    # ========================================================================
    # HANDLE CASUAL - Template response, no API call, don't save
    # ========================================================================
    if intent == "CASUAL":
        # Check for thanks/спасибо specifically
        if any(word in user_message.lower() for word in ["спасибо", "спс", "пасиб", "пасиба", "пасибки", "благодарю", "благодарствую", "мерси", "сяб", "сяп", "привет", "здравствуйте", "здравствуй", "добрый день", "доброе утро", "добрый вечер", "пожалуйста", "прошу", "извините", "извини", "прости", "простите", "пока", "до свидания", "всего доброго", "thanks", "thank you", "ty", "thx", "thanx", "cheers", "much obliged", "appreciate it", "hello", "hi", "hey", "good morning", "good afternoon", "good evening", "please", "welcome", "you're welcome", "my pleasure", "sorry", "excuse me", "pardon", "goodbye", "bye", "see you", "have a good day"]):
            await message.answer(THANKS_RESPONSE)
        else:
            await message.answer(CASUAL_RESPONSE)
        await log_usage(user_id, tokens_used=0, query_type='casual') 
        return
    
    # ========================================================================
    # HANDLE TEACHING - Full teaching flow with YandexGPT
    # ========================================================================
    try:
        # Load user data
        grade = user['grade']
        textbook = user['textbook']
        
        # Load recent conversations for context
        conversation_history = await get_recent_conversations(user_id)
        
        # Build complete prompt
        full_prompt = build_full_prompt(grade, textbook, user_message, conversation_history)
        
        # Call YandexGPT Pro 5.1
        logger.info(f"Calling YandexGPT for user {user_id}")
        result = await call_yandex_gpt(full_prompt)
        
        # Extract answer and tokens
        answer = result['answer']
        tokens_used = result['tokens']['total']
        
        # Append disclaimer in backend (not in prompt)
        final_response = answer + DISCLAIMER
        
        # Save conversation to database with token tracking
        await save_conversation(user_id, user_message, answer, tokens_used)
        
        # Add tokens to user's counters (deducts from balance)
        await add_tokens(user_id, tokens_used)
        
        # Log to permanent audit trail (never deleted)
        await log_usage(user_id, tokens_used, 'teaching')
        
        # Increment message count
        await increment_message_count(user_id)
        
        # Send response to user
        await message.answer(final_response)
        
        logger.info(f"User {user_id} received response, tokens used: {tokens_used}")
        
    except Exception as e:
        logger.error(f"Error processing message for user {user_id}: {e}")
        await message.answer(
            "Произошла ошибка при обработке запроса.\n"
            "Попробуй ещё раз или обратись в поддержку."
        )
