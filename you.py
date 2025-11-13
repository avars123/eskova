import os
import json
import datetime
import random
import traceback
import requests
import google.generativeai as genai
from telebot import TeleBot, types
from telebot.util import quick_markup

# Константы
BOT_TOKEN = "8354515031:AAEnTTa0qdU8teKjwMv373llShkM4alH62Q"
ADMIN_GROUP_ID = -1003205923977
CHANNEL_ID = -1002658375841
POSTS_FILE = "posts.json"
APPLICATIONS_FILE = "admin_applications.json"

# Google Gemini API
GEMINI_API_KEY = "AIzaSyB2B09tZ87T6uxQZP9QmPWwlnQEvyRKx6g"

# Инициализация бота
bot = TeleBot(BOT_TOKEN)

# Инициализация Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro')
    GEMINI_AVAILABLE = True
    print("✅ Gemini API подключен успешно!")
except Exception as e:
    GEMINI_AVAILABLE = False
    print(f"❌ Ошибка подключения Gemini: {e}")

# Хранилище истории для нейросети
user_history = {}

# Функция для отправки ошибок в чат админов
def send_error_to_admins(error_message, user_info=""):
    try:
        full_message = f"🚨 ОШИБКА БОТА\n\n"
        if user_info:
            full_message += f"👤 Пользователь: {user_info}\n"
        full_message += f"⏰ Время: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
        full_message += f"🔧 Ошибка: {error_message}"
        
        bot.send_message(ADMIN_GROUP_ID, full_message)
    except Exception as e:
        print(f"Не удалось отправить ошибку админам: {e}")

# Крутые фишки - списки для рандомных ответов
FUNNY_RESPONSES = [
    "Ого, вот это заявка! 👀", 
    "Вау, нам бы таких админов побольше! ✨",
    "Хм, интересно... очень интересно... 🤔",
    "Так, это надо обсудить! 💬",
    "Прям в яблочко! 🎯",
    "Наш будущий админ? 👑",
    "Стильно, модно, молодежно! 💫",
    "Лайк за креативность! 👍"
]

ADMIN_REACTIONS = {
    "approve": ["🎉 Принят!", "✅ Одобрено!", "👑 Добро пожаловать!", "💫 Принят в команду!"],
    "reject": ["😕 Отклонено", "❌ Не подошёл", "🚫 Не принят", "💔 Отказ"]
}

# Загрузка данных из JSON
def load_posts():
    try:
        if os.path.exists(POSTS_FILE):
            with open(POSTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    data = {"posts": {}, "user_states": {}}
                    save_posts(data)
                return data
        return {"posts": {}, "user_states": {}}
    except Exception as e:
        send_error_to_admins(f"Ошибка загрузки posts: {e}")
        return {"posts": {}, "user_states": {}}

def load_applications():
    try:
        if os.path.exists(APPLICATIONS_FILE):
            with open(APPLICATIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"applications": {}, "user_states": {}, "interview_messages": {}}
    except Exception as e:
        send_error_to_admins(f"Ошибка загрузки applications: {e}")
        return {"applications": {}, "user_states": {}, "interview_messages": {}}

# Сохранение данных в JSON
def save_posts(data):
    try:
        with open(POSTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        send_error_to_admins(f"Ошибка сохранения posts: {e}")

def save_applications(data):
    try:
        with open(APPLICATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        send_error_to_admins(f"Ошибка сохранения applications: {e}")

# Генерация ID
def generate_post_id():
    try:
        data = load_posts()
        if not data["posts"]:
            return 1
        return max([int(i) for i in data["posts"].keys()]) + 1
    except Exception as e:
        send_error_to_admins(f"Ошибка генерации post_id: {e}")
        return int(datetime.datetime.now().timestamp())

def generate_application_id():
    try:
        data = load_applications()
        if not data["applications"]:
            return 1
        return max([int(i) for i in data["applications"].keys()]) + 1
    except Exception as e:
        send_error_to_admins(f"Ошибка генерации application_id: {e}")
        return int(datetime.datetime.now().timestamp())

# Главное меню
def main_menu():
    return quick_markup({
        '📝 Отправить пост': {'callback_data': 'send_post'},
        '📂 Мои посты': {'callback_data': 'my_posts'},
        '👑 Стать админом': {'callback_data': 'become_admin'},
        '🏆 Топ пользователей': {'callback_data': 'top_users'},
        'ℹ️ Помощь': {'callback_data': 'help'},
        '📊 Статистика': {'callback_data': 'stats'},
        '⚖️ Юрист': {'callback_data': 'yourist'}
    }, row_width=2)

# Меню после публикации
def after_publish_menu():
    return quick_markup({
        '📝 Отправить новый пост': {'callback_data': 'send_post'},
        '📂 Мои посты': {'callback_data': 'my_posts'},
        '🔙 Главное меню': {'callback_data': 'back_to_main'}
    }, row_width=2)

# Кнопки модерации постов
def moderation_buttons(post_id):
    return quick_markup({
        '✅ Опубликовать': {'callback_data': f'approve_{post_id}'},
        '❌ Отклонить': {'callback_data': f'reject_{post_id}'},
        '🚫 Заблокировать': {'callback_data': f'ban_{post_id}'},
        '💬 Комментарий': {'callback_data': f'comment_{post_id}'}
    }, row_width=2)

# Кнопки модерации с разблокировкой
def moderation_buttons_unban(post_id):
    return quick_markup({
        '✅ Опубликовать': {'callback_data': f'approve_{post_id}'},
        '❌ Отклонить': {'callback_data': f'reject_{post_id}'},
        '✅ Разблокировать': {'callback_data': f'unban_{post_id}'},
        '💬 Комментарий': {'callback_data': f'comment_{post_id}'}
    }, row_width=2)

# Кнопки для анкеты админа
def admin_application_buttons(app_id):
    return quick_markup({
        '✅ Одобрить': {'callback_data': f'app_approve_{app_id}'},
        '❌ Отклонить': {'callback_data': f'app_reject_{app_id}'},
        '💬 Собеседование': {'callback_data': f'app_interview_{app_id}'},
        '⭐️ В топ': {'callback_data': f'app_top_{app_id}'}
    }, row_width=2)

# Кнопки для завершения собеседования
def interview_finish_buttons(app_id):
    return quick_markup({
        '✅ Завершить (Принять)': {'callback_data': f'app_approve_{app_id}'},
        '❌ Завершить (Отклонить)': {'callback_data': f'app_reject_{app_id}'},
        '🔥 Срочно взять!': {'callback_data': f'app_urgent_{app_id}'}
    }, row_width=2)

# Проверка, находится ли пользователь в процессе заполнения анкеты админа
def is_in_admin_application_process(user_id):
    try:
        data = load_applications()
        return str(user_id) in data.get("user_states", {})
    except Exception as e:
        send_error_to_admins(f"Ошибка проверки анкеты: {e}")
        return False

# Проверка, находится ли пользователь в процессе собеседования
def is_in_interview_process(user_id):
    try:
        data = load_applications()
        user_state = data.get("user_states", {}).get(str(user_id), {})
        return user_state.get("state") == "admin_interview"
    except Exception as e:
        send_error_to_admins(f"Ошибка проверки собеседования: {e}")
        return False

# Получение информации об админе
def get_admin_info(user):
    try:
        username = f"@{user.username}" if user.username else user.first_name
        return f"{username} (ID: {user.id})"
    except Exception as e:
        send_error_to_admins(f"Ошибка получения info админа: {e}")
        return "Неизвестный админ"

# Функция для топ пользователей
def get_top_users():
    try:
        data_posts = load_posts()
        user_stats = {}
        
        # Считаем опубликованные посты
        for post in data_posts.get("posts", {}).values():
            user_id = post.get("user_id")
            if user_id:
                if user_id not in user_stats:
                    user_stats[user_id] = {"posts": 0, "approved": 0, "username": post.get("username", "Unknown")}
                
                user_stats[user_id]["posts"] += 1
                if post.get("status") == "approved":
                    user_stats[user_id]["approved"] += 1
        
        # Сортируем по количеству опубликованных постов
        top_users = sorted(
            [user for user in user_stats.values() if user["approved"] > 0],
            key=lambda x: x["approved"],
            reverse=True
        )[:10]
        
        return top_users
    except Exception as e:
        send_error_to_admins(f"Ошибка получения топа: {e}")
        return []

# Функция общения с Gemini (юрист с юмором)
def ask_llama(user_id, prompt):
    try:
        if not GEMINI_AVAILABLE:
            return generate_fallback_legal_response(prompt)
        
        response = gemini_model.generate_content(
            f"Ты — опытный юрист с отличным чувством юмора. Отвечай на юридические вопросы шутливо и иронично, но при этом давай точные юридические формулировки по российскому законодательству. Используй юридические термины, ссылайся на статьи законов, но разбавляй ответы шутками, мемами и ироничными комментариями. Сохраняй профессиональный подход, но не будь скучным. Отвечай на русском языке. Вопрос: {prompt}"
        )
        
        return response.text
    except Exception as e:
        error_msg = f"Ошибка Gemini: {e}"
        send_error_to_admins(error_msg, f"User ID: {user_id}")
        return generate_fallback_legal_response(prompt)

def generate_fallback_legal_response(prompt):
    """Запасная функция если Gemini не работает"""
    legal_jokes = [
        "⚖️ По статье 158 УК РФ - это называется 'тайное хищение'... или просто 'не будь таким доверчивым!' 😄",
        "📝 Согласно Гражданскому кодексу... а если по-простому: подписал - отвечай, как на допросе! 🎯",
        "🏛️ Конституция гарантирует права, но не освобождает от ответственности... как говорится, 'закон суров, но это закон!' ⚡",
        "💼 По трудовому законодательству... или 'начальник всегда прав, даже когда неправ' - шутка юриста! 😂",
        "🚓 Уголовный кодекс предусматривает... а народная мудрость гласит: 'не знание закона не освобождает от ответственности, а знание - иногда помогает избежать!' 🎭"
    ]
    
    return f"⚖️ Юридическая консультация по вопросу: '{prompt}'\n\n{random.choice(legal_jokes)}\n\n🔍 Для точного ответа нужны детали. Рекомендую обратиться к профессиональному юристу!"

# Команда /yourist для юридических консультаций (доступна всем)
@bot.message_handler(commands=['yourist'])
def yourist_command(message):
    try:
        # Разбираем команду: /yourist вопрос
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            bot.send_message(message.chat.id, 
                "❌ Неверный формат команды. Используйте: /yourist ваш_юридический_вопрос\n\n"
                "Пример: /yourist что будет если не платить за ЖКХ?"
            )
            return
        
        question = parts[1]
        user_id = message.from_user.id
        
        # Отправляем сообщение о обработке
        processing_msg = bot.send_message(
            message.chat.id,
            f"⚖️ Юридический консультант обрабатывает вопрос...\n\n"
            f"❓ Ваш вопрос: {question}\n\n"
            f"⏳ Изучаю законодательство..."
        )
        
        # Получаем ответ от нейросети
        answer = ask_llama(user_id, question)
        
        # Форматируем ответ
        response_text = (
            f"⚖️ ЮРИДИЧЕСКАЯ КОНСУЛЬТАЦИЯ ⚖️\n\n"
            f"👤 Ваш вопрос: {question}\n\n"
            f"💼 Ответ юриста:\n{answer}\n\n"
            f"📝 Примечание: Это AI-консультация. Для точных юридических действий обратитесь к профессиональному юристу."
        )
        
        # Редактируем сообщение с ответом
        bot.edit_message_text(
            response_text,
            message.chat.id,
            processing_msg.message_id
        )
        
        # Добавляем кнопки для продолжения диалога
        follow_up_buttons = quick_markup({
            '💬 Задать уточняющий вопрос': {'callback_data': f'lawyer_followup_{user_id}'},
            '🧹 Очистить историю': {'callback_data': f'lawyer_clear_{user_id}'},
            '⚖️ Новый вопрос': {'callback_data': 'lawyer_new'}
        }, row_width=1)
        
        bot.send_message(
            message.chat.id,
            "💡 Что дальше?",
            reply_markup=follow_up_buttons
        )
            
    except Exception as e:
        error_msg = f"Ошибка в команде /yourist: {e}"
        send_error_to_admins(error_msg, f"User ID: {message.from_user.id}")
        bot.send_message(message.chat.id, 
            "❌ Ошибка при получении юридической консультации. Попробуйте позже.\n\n"
            "А пока шутка от юриста: 'Лучше иметь адвоката, чем стать клиентом исправительной системы!' 😄"
        )

# Обработчик кнопок для юридических консультаций
@bot.callback_query_handler(func=lambda call: call.data.startswith(('lawyer_followup_', 'lawyer_clear_', 'lawyer_new')))
def handle_lawyer_buttons(call):
    try:
        if call.data.startswith('lawyer_followup_'):
            user_id = int(call.data.split('_')[2])
            
            # Запрашиваем уточняющий вопрос
            msg = bot.send_message(
                call.message.chat.id,
                f"💬 Введите ваш уточняющий вопрос для юриста:",
                reply_to_message_id=call.message.message_id
            )
            
            # Сохраняем состояние для ожидания ответа
            data = load_applications()
            if "user_states" not in data:
                data["user_states"] = {}
            data["user_states"][str(user_id)] = {
                "state": "lawyer_followup",
                "waiting_for_response": True,
                "chat_id": call.message.chat.id
            }
            save_applications(data)
            
            bot.answer_callback_query(call.id, "💬 Введите ваш вопрос")
            
        elif call.data.startswith('lawyer_clear_'):
            user_id = int(call.data.split('_')[2])
            
            bot.answer_callback_query(call.id, "🧹 Готово!")
            
            # Обновляем сообщение
            bot.edit_message_text(
                "🧹 Можете задать новый вопрос командой /yourist",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None
            )
            
        elif call.data == 'lawyer_new':
            bot.answer_callback_query(call.id, "⚖️ Задайте новый вопрос командой /yourist")
            
    except Exception as e:
        error_msg = f"Ошибка в обработке кнопок юриста: {e}"
        send_error_to_admins(error_msg, f"User ID: {call.from_user.id}")
        bot.answer_callback_query(call.id, "❌ Ошибка")

# Обработчик уточняющих вопросов для юриста
@bot.message_handler(func=lambda message: 
    any(str(message.from_user.id) in data.get("user_states", {}) 
    and data["user_states"][str(message.from_user.id)].get("state") == "lawyer_followup"
    for data in [load_applications()]))
def handle_lawyer_followup(message):
    try:
        data = load_applications()
        user_id = message.from_user.id
        
        if str(user_id) not in data.get("user_states", {}):
            return
            
        user_state = data["user_states"][str(user_id)]
        
        if user_state.get("state") == "lawyer_followup" and user_state.get("waiting_for_response"):
            question = message.text
            chat_id = user_state.get("chat_id", message.chat.id)
            
            # Отправляем сообщение о обработке
            processing_msg = bot.send_message(
                chat_id,
                f"⚖️ Юрист анализирует уточняющий вопрос...\n\n"
                f"❓ Ваш вопрос: {question}\n\n"
                f"⏳ Изучаю нюансы..."
            )
            
            # Получаем ответ от нейросети
            answer = ask_llama(user_id, question)
            
            # Форматируем ответ
            response_text = (
                f"⚖️ УТОЧНЯЮЩАЯ КОНСУЛЬТАЦИЯ ⚖️\n\n"
                f"👤 Ваш вопрос: {question}\n\n"
                f"💼 Ответ юриста:\n{answer}\n\n"
                f"📝 Примечание: Это AI-консультация"
            )
            
            # Редактируем сообщение с ответом
            bot.edit_message_text(
                response_text,
                chat_id,
                processing_msg.message_id
            )
            
            # Убираем состояние ожидания
            del data["user_states"][str(user_id)]
            save_applications(data)
            
    except Exception as e:
        error_msg = f"Ошибка в обработке уточняющего вопроса: {e}"
        send_error_to_admins(error_msg, f"User ID: {message.from_user.id}")

# Хранилище выбранных прав для каждого пользователя
admin_rights_selections = {}

# Кнопки выбора прав с галочками
def get_admin_rights_buttons(user_id, current_rights=None):
    if current_rights is None:
        current_rights = admin_rights_selections.get(user_id, {})
    
    # Правильные названия прав для каналов в Telegram Bot API
    rights_options = {
        'can_change_info': '✏️ Изменять инфо',
        'can_post_messages': '📝 Публиковать посты', 
        'can_edit_messages': '🔄 Редактировать посты',
        'can_delete_messages': '🗑️ Удалять сообщения',
        'can_invite_users': '👥 Приглашать пользователей',
        'can_restrict_members': '🚫 Банить пользователей',
        'can_pin_messages': '📌 Закреплять сообщения',
        'can_promote_members': '👑 Назначать админов'
    }
    
    buttons = {}
    for right, label in rights_options.items():
        icon = "✅" if current_rights.get(right, False) else "◻️"
        buttons[f"{icon} {label}"] = {'callback_data': f'admin_toggle_{user_id}_{right}'}
    
    # Кнопка подтверждения
    if any(current_rights.values()):
        buttons['🚀 ГОТОВО'] = {'callback_data': f'admin_confirm_{user_id}'}
    
    buttons['❌ Отмена'] = {'callback_data': f'admin_cancel_{user_id}'}
    
    return quick_markup(buttons, row_width=1)

# Команда /admin для назначения админа в канал
@bot.message_handler(commands=['admin'])
def make_admin_command(message):
    try:
        # Проверяем, что команда отправлена в группе админов
        if message.chat.id != ADMIN_GROUP_ID:
            bot.send_message(message.chat.id, "❌ Эта команда доступна только в группе админов.")
            return
        
        # Разбираем команду: /admin ID_пользователя
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте: /admin ID_пользователя")
            return
        
        user_id = parts[1]
        
        # Проверяем, что ID пользователя - число
        if not user_id.isdigit():
            bot.send_message(message.chat.id, "❌ ID пользователя должен быть числом.")
            return
        
        user_id = int(user_id)
        admin_info = get_admin_info(message.from_user)
        
        # Проверяем, что пользователь есть в канале
        try:
            chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
            if chat_member.status == 'left':
                bot.send_message(message.chat.id, f"❌ Пользователь {user_id} не подписан на канал.")
                return
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Пользователь {user_id} не найден в канале или не подписан.")
            return
        
        # Инициализируем выбор прав
        admin_rights_selections[user_id] = {
            'can_change_info': False,
            'can_post_messages': False,
            'can_edit_messages': False,
            'can_delete_messages': False,
            'can_invite_users': False,
            'can_restrict_members': False,
            'can_pin_messages': False,
            'can_promote_members': False
        }
        
        # Показываем кнопки с выбором прав
        bot.send_message(
            ADMIN_GROUP_ID,
            f"👑 Назначение администратора в канал\n\n"
            f"🆔 ID пользователя: {user_id}\n"
            f"📢 Статус в канале: {chat_member.status}\n"
            f"👤 Кто назначает: {admin_info}\n\n"
            f"📋 Выберите права (нажмите для выбора):\n"
            f"◻️ - не выбрано\n"
            f"✅ - выбрано\n\n"
            f"После выбора нажмите 🚀 ГОТОВО",
            reply_markup=get_admin_rights_buttons(user_id),
            reply_to_message_id=message.message_id
        )
            
    except Exception as e:
        error_msg = f"Ошибка в команде /admin: {e}"
        send_error_to_admins(error_msg, f"Admin ID: {message.from_user.id}")
        bot.send_message(message.chat.id, "❌ Ошибка при назначении админа.")

# Обработка переключения прав
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_toggle_'))
def handle_admin_toggle(call):
    try:
        if call.message.chat.id != ADMIN_GROUP_ID:
            bot.answer_callback_query(call.id, "❌ Эта функция доступна только администраторам.")
            return
        
        parts = call.data.split('_')
        if len(parts) < 4:
            bot.answer_callback_query(call.id, "❌ Неверный формат команды.")
            return
        
        user_id = int(parts[2])
        right = '_'.join(parts[3:])  # Объединяем оставшиеся части для правильного названия права
        
        # Переключаем выбранное право
        if user_id in admin_rights_selections:
            # Проверяем, что право существует
            if right in admin_rights_selections[user_id]:
                admin_rights_selections[user_id][right] = not admin_rights_selections[user_id][right]
                
                # Обновляем сообщение с новыми кнопками
                bot.edit_message_reply_markup(
                    ADMIN_GROUP_ID,
                    call.message.message_id,
                    reply_markup=get_admin_rights_buttons(user_id, admin_rights_selections[user_id])
                )
                
                bot.answer_callback_query(call.id, "✅ Право обновлено")
            else:
                bot.answer_callback_query(call.id, "❌ Неизвестное право")
        else:
            bot.answer_callback_query(call.id, "❌ Сессия устарела")
            
    except Exception as e:
        error_msg = f"Ошибка при переключении прав: {e}"
        send_error_to_admins(error_msg, f"Admin ID: {call.from_user.id}")
        bot.answer_callback_query(call.id, "❌ Ошибка")

# Обработка подтверждения назначения
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_confirm_'))
def handle_admin_confirm(call):
    try:
        if call.message.chat.id != ADMIN_GROUP_ID:
            bot.answer_callback_query(call.id, "❌ Эта функция доступна только администраторам.")
            return
        
        user_id = int(call.data.split('_')[2])
        admin_info = get_admin_info(call.from_user)
        
        if user_id not in admin_rights_selections:
            bot.answer_callback_query(call.id, "❌ Сессия устарела")
            return
        
        selected_rights = admin_rights_selections[user_id]
        
        # Проверяем, что выбраны хотя бы какие-то права
        if not any(selected_rights.values()):
            bot.answer_callback_query(call.id, "❌ Выберите хотя бы одно право")
            return
        
        try:
            # Назначаем админа в канал с выбранными правами
            bot.promote_chat_member(
                chat_id=CHANNEL_ID,
                user_id=user_id,
                **selected_rights
            )
            
            # Формируем список выбранных прав для отображения
            rights_list = []
            rights_labels = {
                'can_change_info': '✏️ Изменять инфо канала',
                'can_post_messages': '📝 Публиковать посты', 
                'can_edit_messages': '🔄 Редактировать посты',
                'can_delete_messages': '🗑️ Удалять сообщения',
                'can_invite_users': '👥 Приглашать пользователей',
                'can_restrict_members': '🚫 Банить пользователей',
                'can_pin_messages': '📌 Закреплять сообщения',
                'can_promote_members': '👑 Назначать админов'
            }
            
            for right, label in rights_labels.items():
                if selected_rights[right]:
                    rights_list.append(f"✅ {label}")
            
            rights_text = "\n".join(rights_list)
            
            # Обновляем сообщение
            bot.edit_message_text(
                f"✅ Администратор назначен в канал!\n\n"
                f"🆔 ID пользователя: {user_id}\n"
                f"👤 Кто назначил: {admin_info}\n"
                f"📅 Время: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"🔧 Выданные права:\n{rights_text}",
                ADMIN_GROUP_ID,
                call.message.message_id,
                reply_markup=None
            )
            
            # Уведомляем пользователя
            try:
                bot.send_message(
                    user_id,
                    f"🎉 Поздравляем! Вы были назначены администратором канала!\n\n"
                    f"🔧 Ваши права:\n{rights_text}\n\n"
                    f"📅 Дата назначения: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"Добро пожаловать в команду! 👑"
                )
            except:
                pass  # Пользователь мог заблокировать бота
            
            # Удаляем из хранилища
            if user_id in admin_rights_selections:
                del admin_rights_selections[user_id]
            
            bot.answer_callback_query(call.id, "✅ Админ назначен!")
            
        except Exception as e:
            error_msg = f"Не удалось назначить админа {user_id}: {e}"
            bot.edit_message_text(
                f"❌ Ошибка назначения админа\n\n{error_msg}",
                ADMIN_GROUP_ID,
                call.message.message_id,
                reply_markup=None
            )
            send_error_to_admins(error_msg, f"Admin: {admin_info}")
            bot.answer_callback_query(call.id, "❌ Ошибка назначения")
            
    except Exception as e:
        error_msg = f"Ошибка при подтверждении назначения админа: {e}"
        send_error_to_admins(error_msg, f"Admin ID: {call.from_user.id}")
        bot.answer_callback_query(call.id, "❌ Ошибка")

# Обработка отмены назначения админа
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_cancel_'))
def handle_admin_cancel(call):
    try:
        if call.message.chat.id != ADMIN_GROUP_ID:
            return
        
        user_id = int(call.data.split('_')[2])
        admin_info = get_admin_info(call.from_user)
        
        # Удаляем из хранилища
        if user_id in admin_rights_selections:
            del admin_rights_selections[user_id]
        
        bot.edit_message_text(
            f"❌ Назначение админа отменено\n\n"
            f"🆔 ID пользователя: {user_id}\n"
            f"👤 Кто отменил: {admin_info}",
            ADMIN_GROUP_ID,
            call.message.message_id,
            reply_markup=None
        )
        
        bot.answer_callback_query(call.id, "❌ Назначение отменено")
        
    except Exception as e:
        error_msg = f"Ошибка при отмене назначения админа: {e}"
        send_error_to_admins(error_msg, f"Admin ID: {call.from_user.id}")

# Команда /unadmin для снятия админа
@bot.message_handler(commands=['unadmin'])
def remove_admin_command(message):
    try:
        # Проверяем, что команда отправлена в группе админов
        if message.chat.id != ADMIN_GROUP_ID:
            bot.send_message(message.chat.id, "❌ Эта команда доступна только в группе админов.")
            return
        
        # Разбираем команду: /unadmin ID_пользователя
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте: /unadmin ID_пользователя")
            return
        
        user_id = parts[1]
        
        # Проверяем, что ID пользователя - число
        if not user_id.isdigit():
            bot.send_message(message.chat.id, "❌ ID пользователя должен быть числом.")
            return
        
        user_id = int(user_id)
        admin_info = get_admin_info(message.from_user)
        
        # Проверяем, что пользователь есть в канале
        try:
            chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
            if chat_member.status not in ['administrator', 'creator']:
                bot.send_message(message.chat.id, f"❌ Пользователь {user_id} не является администратором канала.")
                return
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Пользователь {user_id} не найден в канале.")
            return
        
        # Кнопки подтверждения снятия
        confirm_buttons = quick_markup({
            '✅ Да, снять': {'callback_data': f'unadmin_confirm_{user_id}'},
            '❌ Нет, отмена': {'callback_data': f'unadmin_cancel_{user_id}'}
        }, row_width=2)
        
        bot.send_message(
            ADMIN_GROUP_ID,
            f"🚫 Снятие администратора\n\n"
            f"🆔 ID пользователя: {user_id}\n"
            f"📢 Текущий статус: {chat_member.status}\n"
            f"👤 Кто снимает: {admin_info}\n\n"
            f"Вы уверены, что хотите снять этого администратора?",
            reply_markup=confirm_buttons,
            reply_to_message_id=message.message_id
        )
            
    except Exception as e:
        error_msg = f"Ошибка в команде /unadmin: {e}"
        send_error_to_admins(error_msg, f"Admin ID: {message.from_user.id}")
        bot.send_message(message.chat.id, "❌ Ошибка при снятии админа.")

# Обработка подтверждения снятия админа
@bot.callback_query_handler(func=lambda call: call.data.startswith('unadmin_confirm_'))
def handle_unadmin_confirm(call):
    try:
        if call.message.chat.id != ADMIN_GROUP_ID:
            bot.answer_callback_query(call.id, "❌ Эта функция доступна только администраторам.")
            return
        
        user_id = int(call.data.split('_')[2])
        admin_info = get_admin_info(call.from_user)
        
        try:
            # Снимаем права админа (делаем обычным пользователем)
            bot.promote_chat_member(
                chat_id=CHANNEL_ID,
                user_id=user_id,
                can_change_info=False,
                can_post_messages=False,
                can_edit_messages=False,
                can_delete_messages=False,
                can_invite_users=False,
                can_restrict_members=False,
                can_pin_messages=False,
                can_promote_members=False
            )
            
            # Обновляем сообщение
            bot.edit_message_text(
                f"✅ Администратор снят!\n\n"
                f"🆔 ID пользователя: {user_id}\n"
                f"👤 Кто снял: {admin_info}\n"
                f"📅 Время: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}",
                ADMIN_GROUP_ID,
                call.message.message_id,
                reply_markup=None
            )
            
            # Уведомляем пользователя
            try:
                bot.send_message(
                    user_id,
                    f"ℹ️ Вы были сняты с должности администратора канала.\n\n"
                    f"📅 Дата снятия: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"Спасибо за работу в команде! 🙏"
                )
            except:
                pass  # Пользователь мог заблокировать бота
            
            bot.answer_callback_query(call.id, "✅ Админ снят!")
            
        except Exception as e:
            error_msg = f"Не удалось снять админа {user_id}: {e}"
            bot.edit_message_text(
                f"❌ Ошибка снятия админа\n\n{error_msg}",
                ADMIN_GROUP_ID,
                call.message.message_id,
                reply_markup=None
            )
            send_error_to_admins(error_msg, f"Admin: {admin_info}")
            bot.answer_callback_query(call.id, "❌ Ошибка снятия")
            
    except Exception as e:
        error_msg = f"Ошибка при подтверждении снятия админа: {e}"
        send_error_to_admins(error_msg, f"Admin ID: {call.from_user.id}")
        bot.answer_callback_query(call.id, "❌ Ошибка")

# Обработка отмены снятия админа
@bot.callback_query_handler(func=lambda call: call.data.startswith('unadmin_cancel_'))
def handle_unadmin_cancel(call):
    try:
        if call.message.chat.id != ADMIN_GROUP_ID:
            return
        
        user_id = int(call.data.split('_')[2])
        admin_info = get_admin_info(call.from_user)
        
        bot.edit_message_text(
            f"❌ Снятие админа отменено\n\n"
            f"🆔 ID пользователя: {user_id}\n"
            f"👤 Кто отменил: {admin_info}",
            ADMIN_GROUP_ID,
            call.message.message_id,
            reply_markup=None
        )
        
        bot.answer_callback_query(call.id, "❌ Снятие отменено")
        
    except Exception as e:
        error_msg = f"Ошибка при отмене снятия админа: {e}"
        send_error_to_admins(error_msg, f"Admin ID: {call.from_user.id}")

# НОВАЯ ФУНКЦИЯ: Анонимные сообщения пользователям
@bot.message_handler(commands=['msg'])
def send_anonymous_message(message):
    try:
        # Проверяем, что команда отправлена в группе админов
        if message.chat.id != ADMIN_GROUP_ID:
            bot.send_message(message.chat.id, "❌ Эта команда доступна только в группе админов.")
            return
        
        # Разбираем команду: /msg ID_пользователя текст сообщения
        parts = message.text.split(' ', 2)
        if len(parts) < 3:
            bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте: /msg ID_пользователя текст_сообщения")
            return
        
        user_id = parts[1]
        msg_text = parts[2]
        
        # Проверяем, что ID пользователя - число
        if not user_id.isdigit():
            bot.send_message(message.chat.id, "❌ ID пользователя должен быть числом.")
            return
        
        user_id = int(user_id)
        admin_info = get_admin_info(message.from_user)
        
        try:
            # Отправляем сообщение пользователю
            bot.send_message(
                user_id,
                f"💌 Сообщение от команды канала:\n\n{msg_text}\n\n"
                f"📅 {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            
            # Уведомляем админа об успешной отправке
            bot.send_message(
                ADMIN_GROUP_ID,
                f"✅ Сообщение отправлено пользователю ID: {user_id}\n\n"
                f"Текст: {msg_text}\n\n"
                f"Отправил: {admin_info}",
                reply_to_message_id=message.message_id
            )
            
        except Exception as e:
            error_msg = f"Не удалось отправить сообщение пользователю {user_id}: {e}"
            bot.send_message(ADMIN_GROUP_ID, f"❌ {error_msg}")
            send_error_to_admins(error_msg, f"Admin: {admin_info}")
            
    except Exception as e:
        error_msg = f"Ошибка в команде /msg: {e}"
        send_error_to_admins(error_msg, f"Admin ID: {message.from_user.id}")
        bot.send_message(message.chat.id, "❌ Ошибка при отправке сообщения.")

# Функция для статистики
def get_stats():
    try:
        data_posts = load_posts()
        data_apps = load_applications()
        
        total_posts = len(data_posts.get("posts", {}))
        approved_posts = len([p for p in data_posts.get("posts", {}).values() if p.get("status") == "approved"])
        pending_posts = len([p for p in data_posts.get("posts", {}).values() if p.get("status") == "pending"])
        
        total_apps = len(data_apps.get("applications", {}))
        approved_apps = len([a for a in data_apps.get("applications", {}).values() if a.get("status") == "approved"])
        pending_apps = len([a for a in data_apps.get("applications", {}).values() if a.get("status") == "pending"])
        
        return {
            "total_posts": total_posts,
            "approved_posts": approved_posts,
            "pending_posts": pending_posts,
            "total_apps": total_apps,
            "approved_apps": approved_apps,
            "pending_apps": pending_apps
        }
    except Exception as e:
        send_error_to_admins(f"Ошибка получения статистики: {e}")
        return {}

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    try:
        welcome_text = (
            "👋 Добро пожаловать в бот-предложку!\n\n"
            "✨ Что умеет этот бот:\n"
            "• 📝 Отправлять посты в канал\n"
            "• 👑 Подавать заявку на админа\n" 
            "• 🏆 Смотреть топ пользователей\n"
            "• 💬 Проходить собеседования\n"
            "• 📊 Смотреть статистику\n"
            "• ⚖️ Получить юридическую консультацию\n\n"
            "Выбери действие ниже:"
        )
        
        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=main_menu()
        )
    except Exception as e:
        error_msg = f"Ошибка в /start: {e}"
        send_error_to_admins(error_msg, f"User ID: {message.from_user.id}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Попробуйте позже.")

# Обработчик команды /help
@bot.callback_query_handler(func=lambda call: call.data == 'help')
def help_command(call):
    try:
        help_text = (
            "ℹ️ Помощь по боту\n\n"
            "📝 Отправить пост:\n"
            "Просто отправь текст, фото, видео или другой контент - он попадёт на модерацию\n\n"
            "👑 Стать админом:\n" 
            "Заполни анкету из 9 вопросов. Админы рассмотрят её и могут назначить собеседование\n\n"
            "🏆 Топ пользователей:\n"
            "Рейтинг самых активных пользователей по количеству опубликованных постов\n\n"
            "⚖️ Юридическая консультация:\n"
            "Команда /yourist вопрос - получите консультацию от юриста-нейросети\n\n"
            "💬 Собеседование:\n"
            "Если админы начали собеседование - просто общайся здесь, все сообщения видны команде\n\n"
            "📊 Статистика:\n"
            "Общая статистика постов и заявок\n\n"
            "💌 Анонимные сообщения:\n"
            "Админы могут писать пользователям через /msg ID_пользователя текст\n\n"
            "❓ Проблемы?\n"
            "Пиши @vikalike_support"
        )
        
        bot.edit_message_text(
            help_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=quick_markup({'🔙 Назад': {'callback_data': 'back_to_main'}})
        )
        bot.answer_callback_query(call.id)
    except Exception as e:
        error_msg = f"Ошибка в help: {e}"
        send_error_to_admins(error_msg, f"User ID: {call.from_user.id}")
        bot.answer_callback_query(call.id, "❌ Ошибка")

# Топ пользователей
@bot.callback_query_handler(func=lambda call: call.data == 'top_users')
def show_top_users(call):
    try:
        top_users = get_top_users()
        
        if not top_users:
            text = "🏆 Топ пользователей\n\nПока никто не опубликовал посты. Будь первым! ✨"
        else:
            text = "🏆 Топ пользователей\n\n"
            for i, user in enumerate(top_users, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🔸"
                text += f"{medal} {user['username']} - {user['approved']} постов\n"
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=quick_markup({'🔙 Назад': {'callback_data': 'back_to_main'}})
        )
        bot.answer_callback_query(call.id)
    except Exception as e:
        error_msg = f"Ошибка в top_users: {e}"
        send_error_to_admins(error_msg, f"User ID: {call.from_user.id}")
        bot.answer_callback_query(call.id, "❌ Ошибка")

# Статистика
@bot.callback_query_handler(func=lambda call: call.data == 'stats')
def show_stats(call):
    try:
        stats = get_stats()
        
        text = (
            "📊 Статистика бота\n\n"
            f"📝 Посты:\n"
            f"• Всего: {stats.get('total_posts', 0)}\n"
            f"• Опубликовано: {stats.get('approved_posts', 0)}\n"
            f"• На модерации: {stats.get('pending_posts', 0)}\n\n"
            f"👑 Заявки админов:\n"
            f"• Всего: {stats.get('total_apps', 0)}\n"
            f"• Одобрено: {stats.get('approved_apps', 0)}\n"
            f"• На рассмотрении: {stats.get('pending_apps', 0)}"
        )
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=quick_markup({'🔙 Назад': {'callback_data': 'back_to_main'}})
        )
        bot.answer_callback_query(call.id)
    except Exception as e:
        error_msg = f"Ошибка в stats: {e}"
        send_error_to_admins(error_msg, f"User ID: {call.from_user.id}")
        bot.answer_callback_query(call.id, "❌ Ошибка")

# Юрист через кнопку меню
@bot.callback_query_handler(func=lambda call: call.data == 'yourist')
def yourist_callback(call):
    try:
        bot.send_message(
            call.message.chat.id,
            "⚖️ Юридическая консультация\n\n"
            "Задайте ваш юридический вопрос в формате:\n"
            "<code>/yourist ваш вопрос</code>\n\n"
            "Пример:\n"
            "<code>/yourist что будет если не платить за ЖКХ?</code>\n\n"
            "🤖 Ответит AI-юрист с чувством юмора!",
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
    except Exception as e:
        error_msg = f"Ошибка в yourist callback: {e}"
        send_error_to_admins(error_msg, f"User ID: {call.from_user.id}")
        bot.answer_callback_query(call.id, "❌ Ошибка")

# НОВЫЙ ФУНКЦИОНАЛ: Анкета для админа
@bot.callback_query_handler(func=lambda call: call.data == 'become_admin')
def start_admin_application(call):
    try:
        data = load_applications()
        user_id = call.from_user.id
        
        # Проверяем, не подавал ли пользователь уже заявку
        for app_id, application in data.get("applications", {}).items():
            if application.get("user_id") == user_id and application.get("status") == "pending":
                bot.answer_callback_query(call.id, "❌ Вы уже отправили заявку. Дождитесь ответа!")
                return
        
        # Начинаем процесс заполнения анкеты
        bot.send_message(
            call.message.chat.id,
            "👑 Анкета на Админа в канал \"Вика Лайк\" 👑\n\n"
            "Привет, подписчик! Решил(а) подать заявку на вакантное место в нашей тусовке? Отлично! "
            "Заполни эту форму, и мы её рассмотрим.\n\n"
            "1. Твоё имя (или как тебя называть):"
        )
        
        # Сохраняем состояние пользователя
        if "user_states" not in data:
            data["user_states"] = {}
        
        data["user_states"][str(user_id)] = {
            "state": "admin_app_1",
            "application_data": {}
        }
        save_applications(data)
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        error_msg = f"Ошибка в become_admin: {e}"
        send_error_to_admins(error_msg, f"User ID: {call.from_user.id}")
        bot.answer_callback_query(call.id, "❌ Ошибка")

# Обработчик текстовых сообщений для анкеты админа
@bot.message_handler(func=lambda message: is_in_admin_application_process(message.from_user.id))
def handle_admin_application(message):
    try:
        data = load_applications()
        user_id = message.from_user.id
        
        if str(user_id) not in data.get("user_states", {}):
            return
            
        user_state = data["user_states"][str(user_id)]
        app_data = user_state.get("application_data", {})
        current_state = user_state.get("state", "")
        
        if current_state == "admin_app_1":
            app_data["name"] = message.text
            user_state["state"] = "admin_app_2"
            bot.send_message(message.chat.id, "2. Твой возраст (просто цифра, нам не верить, а для статистики):")
        
        elif current_state == "admin_app_2":
            if not message.text.isdigit():
                bot.send_message(message.chat.id, "❌ Пожалуйста, введите возраст цифрами:")
                return
            app_data["age"] = message.text
            user_state["state"] = "admin_app_3"
            bot.send_message(
                message.chat.id, 
                "3. Расскажи, почему ты хочешь стать админом именно в этом канале?\n"
                "(Не пиши \"потому что Вика крутая\", мы это и так знаем 😉):"
            )
        
        elif current_state == "admin_app_3":
            app_data["reason"] = message.text
            user_state["state"] = "admin_app_4"
            bot.send_message(
                message.chat.id,
                "4. Опыт есть? Был(а) ли админом/модератором в других чатах или каналах? Если да — где и что делал(а)?"
            )
        
        elif current_state == "admin_app_4":
            app_data["experience"] = message.text
            user_state["state"] = "admin_app_5"
            bot.send_message(
                message.chat.id,
                "5. Представь, в комментариях начался хейт и срач из-за нового видео. Твои первые 3 действия?"
            )
        
        elif current_state == "admin_app_5":
            app_data["conflict_solution"] = message.text
            user_state["state"] = "admin_app_6"
            bot.send_message(
                message.chat.id,
                "6. Сколько времени в сутки ты готов(а) уделять каналу?\n(Будь честен, мы всё равно проверим 😜):"
            )
        
        elif current_state == "admin_app_6":
            app_data["time"] = message.text
            user_state["state"] = "admin_app_7"
            bot.send_message(
                message.chat.id,
                "7. Наша фишка — мемы и ирония. Предложи идею для нового рубрики или поста в канал:"
            )
        
        elif current_state == "admin_app_7":
            app_data["idea"] = message.text
            user_state["state"] = "admin_app_8"
            bot.send_message(
                message.chat.id,
                "8. Твоё главное оружие как админа (строгость, чувство юмора, невероятное обаяние или что-то другое)?"
            )
        
        elif current_state == "admin_app_8":
            app_data["weapon"] = message.text
            user_state["state"] = "admin_app_9"
            bot.send_message(
                message.chat.id,
                "9. Ссылка на твой Telegram-аккаунт (обязательно):"
            )
        
        elif current_state == "admin_app_9":
            app_data["telegram_link"] = message.text
            app_data["username"] = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
            app_data["user_id"] = user_id
            
            # Завершаем анкету и отправляем в группу админов
            application_id = generate_application_id()
            
            if "applications" not in data:
                data["applications"] = {}
                
            data["applications"][str(application_id)] = {
                **app_data,
                "status": "pending",
                "date": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
                "rating": 0
            }
            
            # Удаляем состояние пользователя
            if str(user_id) in data["user_states"]:
                del data["user_states"][str(user_id)]
            
            # Случайная реакция для веселья
            funny_reaction = random.choice(FUNNY_RESPONSES)
            
            # Формируем сообщение для админов
            admin_message = (
                f"{funny_reaction}\n\n"
                "👑 НОВАЯ ЗАЯВКА НА АДМИНА 👑\n\n"
                f"🆔 ID заявки: #{application_id}\n"
                f"👤 Пользователь: {app_data.get('username', 'Unknown')}\n"
                f"🔗 Telegram: {app_data.get('telegram_link', 'Не указано')}\n"
                f"🆔 User ID: {user_id}\n"
                f"📅 Дата подачи: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"1. Имя: {app_data.get('name', 'Не указано')}\n"
                f"2. Возраст: {app_data.get('age', 'Не указано')}\n"
                f"3. Причина: {app_data.get('reason', 'Не указано')}\n"
                f"4. Опыт: {app_data.get('experience', 'Не указано')}\n"
                f"5. Решение конфликтов: {app_data.get('conflict_solution', 'Не указано')}\n"
                f"6. Время: {app_data.get('time', 'Не указано')}\n"
                f"7. Идея: {app_data.get('idea', 'Не указано')}\n"
                f"8. Оружие: {app_data.get('weapon', 'Не указано')}\n"
            )
            
            # Отправляем в группу админов
            bot.send_message(
                ADMIN_GROUP_ID,
                admin_message,
                reply_markup=admin_application_buttons(application_id)
            )
            
            save_applications(data)
            
            bot.send_message(
                message.chat.id,
                "✅ Твоя анкета отправлена на рассмотрение! Ожидай ответа в ближайшее время.\n\n"
                "Удачи! И да пребудет с тобой лайк! ✨",
                reply_markup=main_menu()
            )
            return
        
        # Сохраняем изменения
        data["user_states"][str(user_id)] = user_state
        save_applications(data)
        
    except Exception as e:
        error_msg = f"Ошибка в анкете админа: {e}"
        send_error_to_admins(error_msg, f"User ID: {message.from_user.id}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка при заполнении анкеты. Попробуйте начать заново.")

# Обработка действий админов с заявками
@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_approve_', 'app_reject_', 'app_interview_', 'app_top_', 'app_urgent_')))
def handle_admin_application_action(call):
    try:
        if call.message.chat.id != ADMIN_GROUP_ID:
            bot.answer_callback_query(call.id, "❌ Эта функция доступна только администраторам.")
            return
        
        data = load_applications()
        parts = call.data.split('_')
        if len(parts) < 3:
            bot.answer_callback_query(call.id, "❌ Неверный формат команды.")
            return
            
        action = parts[1]
        app_id = parts[2]
        
        application = data.get("applications", {}).get(app_id)
        
        if not application:
            bot.answer_callback_query(call.id, "❌ Заявка не найдена.")
            return
        
        admin_info = get_admin_info(call.from_user)
        admin_reaction = random.choice(ADMIN_REACTIONS.get(action, ["✅ Действие выполнено"]))
        
        if action == "approve":
            application["status"] = "approved"
            application["moderated_by"] = admin_info
            application["moderated_at"] = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            
            # Уведомляем пользователя
            try:
                bot.send_message(
                    application["user_id"],
                    "🎉 Поздравляем! Твоя заявка на админа одобрена!\n\n"
                    f"Кто принял: {admin_info}\n"
                    "Скоро с тобой свяжутся для дальнейших инструкций. Добро пожаловать в команду! 👑"
                )
            except Exception as e:
                send_error_to_admins(f"Не удалось уведомить пользователя: {e}")
            
            # Обновляем сообщение в группе
            new_text = f"{call.message.text}\n\n{admin_reaction} {admin_info}"
            try:
                bot.edit_message_text(
                    new_text,
                    ADMIN_GROUP_ID,
                    call.message.message_id,
                    reply_markup=None
                )
            except Exception as e:
                send_error_to_admins(f"Не удалось обновить сообщение: {e}")
            
        elif action == "reject":
            application["status"] = "rejected"
            application["moderated_by"] = admin_info
            application["moderated_at"] = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            
            # Уведомляем пользователя
            try:
                bot.send_message(
                    application["user_id"],
                    "😕 К сожалению, твоя заявка на админа не была одобрена.\n\n"
                    f"Кто отклонил: {admin_info}\n"
                    "Не расстраивайся! Ты можешь продолжать участвовать в жизни канала и предложить пост."
                )
            except Exception as e:
                send_error_to_admins(f"Не удалось уведомить пользователя: {e}")
            
            # Обновляем сообщение в группе
            new_text = f"{call.message.text}\n\n{admin_reaction} {admin_info}"
            try:
                bot.edit_message_text(
                    new_text,
                    ADMIN_GROUP_ID,
                    call.message.message_id,
                    reply_markup=None
                )
            except Exception as e:
                send_error_to_admins(f"Не удалось обновить сообщение: {e}")
        
        elif action == "interview":
            # Сохраняем состояние для собеседования
            if "user_states" not in data:
                data["user_states"] = {}
            if "interview_messages" not in data:
                data["interview_messages"] = {}
            
            data["user_states"][str(application["user_id"])] = {
                "state": "admin_interview",
                "application_id": app_id,
                "interviewer": call.from_user.id,
                "started_at": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            }
            
            # Уведомляем админов в группе
            interview_msg = bot.send_message(
                ADMIN_GROUP_ID,
                f"💬 Начат процесс собеседования с {application.get('username', 'Unknown')}\n\n"
                f"Кто проводит: {admin_info}\n"
                f"Время начала: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"Все сообщения от пользователя будут пересылаться сюда для коллективного обсуждения."
            )
            
            # Сохраняем ID сообщения о начале собеседования
            data["interview_messages"][app_id] = interview_msg.message_id
            
            # Уведомляем пользователя
            try:
                bot.send_message(
                    application["user_id"],
                    "💬 Начат процесс собеседования!\n\n"
                    f"Кто проводит: {admin_info}\n"
                    "Администраторы начали с тобой диалог. Отвечай на их вопросы здесь - все твои сообщения "
                    "будут видны команде для принятия окончательного решения."
                )
            except Exception as e:
                send_error_to_admins(f"Не удалось уведомить пользователя: {e}")
            
            bot.answer_callback_query(call.id, "💬 Начат процесс собеседования")
        
        elif action == "top":
            # Добавляем рейтинг заявке
            application["rating"] = application.get("rating", 0) + 1
            bot.answer_callback_query(call.id, f"⭐️ +1 к рейтингу! Текущий: {application['rating']}")
        
        elif action == "urgent":
            application["status"] = "approved"
            application["moderated_by"] = f"🔥 СРОЧНО - {admin_info}"
            application["moderated_at"] = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            application["urgent"] = True
            
            # Срочное уведомление пользователя
            try:
                bot.send_message(
                    application["user_id"],
                    "🚀 ВАУ! Твоя заявка принята в срочном порядке! 🚀\n\n"
                    f"Кто принял: {admin_info}\n"
                    "Ты произвел(а) сильное впечатление! С тобой свяжутся в ближайшее время. 👑"
                )
            except Exception as e:
                send_error_to_admins(f"Не удалось уведомить пользователя: {e}")
            
            # Обновляем сообщение в группе
            new_text = f"{call.message.text}\n\n🚀 СРОЧНО ПРИНЯТ! {admin_info}"
            try:
                bot.edit_message_text(
                    new_text,
                    ADMIN_GROUP_ID,
                    call.message.message_id,
                    reply_markup=None
                )
            except Exception as e:
                send_error_to_admins(f"Не удалось обновить сообщение: {e}")
            
            bot.answer_callback_query(call.id, "🚀 Срочное принятие!")
        
        save_applications(data)
        if action not in ['interview', 'top', 'urgent']:
            bot.answer_callback_query(call.id, admin_reaction)
            
    except Exception as e:
        error_msg = f"Ошибка в обработке заявки админа: {e}"
        send_error_to_admins(error_msg, f"Admin ID: {call.from_user.id}")
        bot.answer_callback_query(call.id, "❌ Ошибка")

# Обработчик сообщений во время собеседования
@bot.message_handler(func=lambda message: is_in_interview_process(message.from_user.id))
def handle_interview_message(message):
    try:
        data = load_applications()
        user_id = message.from_user.id
        user_state = data.get("user_states", {}).get(str(user_id), {})
        app_id = user_state.get("application_id")
        
        if not app_id:
            return
            
        application = data.get("applications", {}).get(app_id)
        if not application:
            return
        
        try:
            # Пересылаем сообщение в группу админов
            forwarded_msg = bot.forward_message(ADMIN_GROUP_ID, message.chat.id, message.message_id)
            
            # Добавляем кнопки для завершения собеседования
            if hasattr(forwarded_msg, 'text') and forwarded_msg.text:
                bot.edit_message_text(
                    f"💬 Собеседование с {application.get('username', 'Unknown')}:\n\n{forwarded_msg.text}",
                    ADMIN_GROUP_ID,
                    forwarded_msg.message_id,
                    reply_markup=interview_finish_buttons(app_id)
                )
            else:
                # Для медиа-сообщений отправляем отдельное текстовое сообщение с кнопками
                bot.send_message(
                    ADMIN_GROUP_ID,
                    f"💬 Медиа-сообщение от {application.get('username', 'Unknown')} во время собеседования",
                    reply_markup=interview_finish_buttons(app_id)
                )
        except Exception as e:
            send_error_to_admins(f"Ошибка пересылки сообщения собеседования: {e}")
            
    except Exception as e:
        error_msg = f"Ошибка в обработке собеседования: {e}"
        send_error_to_admins(error_msg, f"User ID: {message.from_user.id}")

# Обработчик команды /post{id}
@bot.message_handler(regexp=r'^/post\d+$')
def show_post(message):
    try:
        data = load_posts()
        post_id = message.text.replace('/post', '')
        
        if post_id not in data.get("posts", {}):
            bot.send_message(message.chat.id, "❌ Пост не найден.")
            return
        
        post = data["posts"][post_id]
        
        if str(post.get("user_id")) != str(message.from_user.id):
            bot.send_message(message.chat.id, "❌ Это не ваш пост.")
            return
        
        status_info = ""
        if post.get("status") != "pending" and "moderated_by" in post:
            status_info = f"\n\nМодератор: {post['moderated_by']}"
        
        # Отправка медиа в зависимости от типа
        media_type = post.get("media_type", "text")
        
        if media_type == "text":
            bot.send_message(
                message.chat.id, 
                f"📝 Текст поста:\n\n{post.get('text', '')}\n\nСтатус: {post.get('status', 'unknown')}{status_info}"
            )
        
        elif media_type == "photo":
            bot.send_photo(
                message.chat.id, 
                post.get("file_id"), 
                caption=f"{post.get('text', '')}\n\nСтатус: {post.get('status', 'unknown')}{status_info}"
            )
        
        elif media_type == "video":
            bot.send_video(
                message.chat.id, 
                post.get("file_id"), 
                caption=f"{post.get('text', '')}\n\nСтатус: {post.get('status', 'unknown')}{status_info}"
            )
        
        elif media_type == "sticker":
            bot.send_sticker(message.chat.id, post.get("file_id"))
            if post.get("text"):
                bot.send_message(
                    message.chat.id, 
                    f"📝 Подпись:\n\n{post.get('text', '')}\n\nСтатус: {post.get('status', 'unknown')}{status_info}"
                )
        
        elif media_type == "voice":
            bot.send_voice(
                message.chat.id, 
                post.get("file_id"), 
                caption=f"{post.get('text', '')}\n\nСтатус: {post.get('status', 'unknown')}{status_info}"
            )
        
        elif media_type == "video_note":
            bot.send_video_note(message.chat.id, post.get("file_id"))
            if post.get("text"):
                bot.send_message(
                    message.chat.id, 
                    f"📝 Подпись:\n\n{post.get('text', '')}\n\nСтатус: {post.get('status', 'unknown')}{status_info}"
                )
        
        elif media_type == "media_group":
            if post.get("text"):
                bot.send_message(
                    message.chat.id, 
                    f"📝 Подпись альбома:\n\n{post.get('text', '')}\n\nСтатус: {post.get('status', 'unknown')}{status_info}"
                )
            else:
                bot.send_message(
                    message.chat.id, 
                    f"📷 Медиа-альбом (без подписи)\n\nСтатус: {post.get('status', 'unknown')}{status_info}"
                )
    except Exception as e:
        error_msg = f"Ошибка в show_post: {e}"
        send_error_to_admins(error_msg, f"User ID: {message.from_user.id}")
        bot.send_message(message.chat.id, "❌ Ошибка при загрузке поста.")

# Обработчик callback-запросов для постов
@bot.callback_query_handler(func=lambda call: call.data in ['send_post', 'my_posts', 'back_to_main'])
def callback_handler(call):
    try:
        data = load_posts()
        user_id = call.from_user.id
        
        if call.data == 'send_post':
            if str(user_id) in data.get("user_states", {}) and data["user_states"].get(str(user_id)) == "banned":
                bot.answer_callback_query(call.id, "❌ Вы заблокированы и не можете отправлять посты.")
                return
            
            bot.send_message(
                call.message.chat.id,
                "📤 Отправьте ваш пост (текст, фото, видео, стикер, голосовое сообщение или видео-заметку):"
            )
            bot.answer_callback_query(call.id)
        
        elif call.data == 'my_posts':
            user_posts = []
            for post_id, post in data.get("posts", {}).items():
                if str(post.get("user_id")) == str(user_id):
                    status_emoji = {
                        "approved": "✅",
                        "rejected": "❌", 
                        "pending": "⏳"
                    }.get(post.get("status"), "⏳")
                    
                    date = post.get("date", "Неизвестно")
                    user_posts.append(f"🆔 /post{post_id} — {status_emoji} {post.get('status', 'unknown')} ({date})")
            
            if user_posts:
                bot.edit_message_text(
                    "📂 Ваши посты:\n\n" + "\n".join(user_posts),
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=quick_markup({'🔙 Назад': {'callback_data': 'back_to_main'}})
                )
            else:
                bot.edit_message_text(
                    "📭 У вас пока нет постов.",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=quick_markup({'🔙 Назад': {'callback_data': 'back_to_main'}})
                )
            bot.answer_callback_query(call.id)
        
        elif call.data == 'back_to_main':
            bot.edit_message_text(
                "👋 Добро пожаловать в бот-предложку!\n\n"
                "✨ Что умеет этот бот:\n"
                "• 📝 Отправлять посты в канал\n"
                "• 👑 Подавать заявку на админа\n" 
                "• 🏆 Смотреть топ пользователей\n"
                "• 💬 Проходить собеседования\n"
                "• 📊 Смотреть статистику\n"
                "• ⚖️ Получить юридическую консультацию\n\n"
                "Выбери действие ниже:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=main_menu()
            )
            bot.answer_callback_query(call.id)
    except Exception as e:
        error_msg = f"Ошибка в callback_handler: {e}"
        send_error_to_admins(error_msg, f"User ID: {call.from_user.id}")
        bot.answer_callback_query(call.id, "❌ Ошибка")

# Обработка модерации постов
@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_', 'ban_', 'unban_', 'comment_')))
def moderation_handler(call):
    try:
        if call.message.chat.id != ADMIN_GROUP_ID:
            bot.answer_callback_query(call.id, "❌ Эта функция доступна только администраторам.")
            return
        
        data = load_posts()
        parts = call.data.split('_')
        if len(parts) < 2:
            bot.answer_callback_query(call.id, "❌ Неверный формат команды.")
            return
            
        action = parts[0]
        post_id = parts[1]
        
        post = data.get("posts", {}).get(post_id)
        
        if not post:
            bot.answer_callback_query(call.id, "❌ Пост не найден.")
            return
        
        admin_info = get_admin_info(call.from_user)
        
        if action == 'approve':
            # Публикация поста в канал
            try:
                caption = post.get("text", "")
                if caption:
                    caption += f"\n\n👁‍🗨 Пост предложен: {post.get('username', 'Unknown')}"
                
                media_type = post.get("media_type", "text")
                
                if media_type == "text":
                    bot.send_message(CHANNEL_ID, caption or post.get("text", ""))
                elif media_type == "photo":
                    bot.send_photo(CHANNEL_ID, post.get("file_id"), caption=caption)
                elif media_type == "video":
                    bot.send_video(CHANNEL_ID, post.get("file_id"), caption=caption)
                elif media_type == "sticker":
                    bot.send_sticker(CHANNEL_ID, post.get("file_id"))
                elif media_type == "voice":
                    bot.send_voice(CHANNEL_ID, post.get("file_id"), caption=caption)
                elif media_type == "video_note":
                    bot.send_video_note(CHANNEL_ID, post.get("file_id"))
                elif media_type == "media_group":
                    if caption:
                        bot.send_message(CHANNEL_ID, caption)
                
                post["status"] = "approved"
                post["moderated_by"] = admin_info
                post["moderated_at"] = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
                
                # Уведомление пользователя
                try:
                    bot.send_message(
                        post["user_id"],
                        f"🎉 Ваш пост опубликован!\n\n"
                        f"Кто опубликовал: {admin_info}\n"
                        f"Хотите отправить новый?",
                        reply_markup=after_publish_menu()
                    )
                except Exception as e:
                    send_error_to_admins(f"Не удалось уведомить пользователя: {e}")
                
            except Exception as e:
                bot.answer_callback_query(call.id, f"❌ Ошибка публикации: {e}")
                return
        
        elif action == 'reject':
            post["status"] = "rejected"
            post["moderated_by"] = admin_info
            post["moderated_at"] = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            
            # Уведомление пользователя
            try:
                bot.send_message(
                    post["user_id"], 
                    f"😕 Ваш пост был отклонён.\n\n"
                    f"Кто отклонил: {admin_info}"
                )
            except Exception as e:
                send_error_to_admins(f"Не удалось уведомить пользователя: {e}")
        
        elif action == 'ban':
            if "user_states" not in data:
                data["user_states"] = {}
            data["user_states"][str(post["user_id"])] = "banned"
            # Замена кнопки на разблокировку
            try:
                bot.edit_message_reply_markup(
                    ADMIN_GROUP_ID,
                    call.message.message_id,
                    reply_markup=moderation_buttons_unban(post_id)
                )
            except Exception as e:
                send_error_to_admins(f"Не удалось обновить кнопки: {e}")
            bot.answer_callback_query(call.id, f"🚫 Заблокирован {admin_info}")
            save_posts(data)
            return
        
        elif action == 'unban':
            if str(post["user_id"]) in data.get("user_states", {}):
                del data["user_states"][str(post["user_id"])]
            # Замена кнопки на блокировку
            try:
                bot.edit_message_reply_markup(
                    ADMIN_GROUP_ID,
                    call.message.message_id,
                    reply_markup=moderation_buttons(post_id)
                )
            except Exception as e:
                send_error_to_admins(f"Не удалось обновить кнопки: {e}")
            bot.answer_callback_query(call.id, f"✅ Разблокирован {admin_info}")
            save_posts(data)
            return
        
        elif action == 'comment':
            # Запрос комментария от админа
            msg = bot.send_message(
                ADMIN_GROUP_ID,
                f"💬 Введите комментарий для поста #{post_id}:",
                reply_to_message_id=call.message.message_id
            )
            bot.answer_callback_query(call.id, "💬 Режим комментария")
            save_posts(data)
            return
        
        # Обновление сообщения в группе модерации
        if action in ['approve', 'reject']:
            try:
                # Получаем текущий текст сообщения
                current_text = call.message.text or call.message.caption or ""
                
                status_text = {
                    'approve': f"✅ Опубликовано {admin_info}",
                    'reject': f"❌ Отклонено {admin_info}"
                }.get(action, "")
                
                new_text = f"{current_text}\n\n{status_text}"
                
                # Пытаемся отредактировать сообщение
                if call.message.text:  # Текстовое сообщение
                    bot.edit_message_text(
                        new_text,
                        ADMIN_GROUP_ID,
                        call.message.message_id,
                        reply_markup=None
                    )
                elif call.message.caption:  # Сообщение с медиа
                    bot.edit_message_caption(
                        new_text,
                        ADMIN_GROUP_ID,
                        call.message.message_id,
                        reply_markup=None
                    )
            except Exception as e:
                # Если не удалось отредактировать, просто убираем кнопки
                try:
                    bot.edit_message_reply_markup(
                        ADMIN_GROUP_ID,
                        call.message.message_id,
                        reply_markup=None
                    )
                except:
                    pass
        
        save_posts(data)
        if action not in ['ban', 'unban', 'comment']:
            bot.answer_callback_query(call.id, f"✅ {action} {admin_info}")
            
    except Exception as e:
        error_msg = f"Ошибка в moderation_handler: {e}"
        send_error_to_admins(error_msg, f"Admin ID: {call.from_user.id}")
        bot.answer_callback_query(call.id, "❌ Ошибка")

# Обработчик текстовых сообщений (посты)
@bot.message_handler(content_types=['text'])
def handle_text(message):
    # Пропускаем сообщения, если пользователь заполняет анкету или в собеседовании
    if is_in_admin_application_process(message.from_user.id) or is_in_interview_process(message.from_user.id):
        return
    
    try:
        data = load_posts()
        user_id = message.from_user.id
        
        if str(user_id) in data.get("user_states", {}) and data["user_states"].get(str(user_id)) == "banned":
            bot.send_message(message.chat.id, "❌ Вы заблокированы и не можете отправлять посты.")
            return
        
        post_id = generate_post_id()
        username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        
        # Сохранение поста
        if "posts" not in data:
            data["posts"] = {}
            
        data["posts"][str(post_id)] = {
            "user_id": user_id,
            "username": username,
            "text": message.text,
            "media_type": "text",
            "file_id": None,
            "status": "pending",
            "date": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        
        # Отправка в группу модерации
        admin_message = bot.send_message(
            ADMIN_GROUP_ID,
            f"👤 {username} (ID {user_id}) предложил пост #{post_id}\n\n{message.text}",
            reply_markup=moderation_buttons(post_id)
        )
        
        data["posts"][str(post_id)]["admin_message_id"] = admin_message.message_id
        save_posts(data)
        
        bot.send_message(
            message.chat.id,
            "✅ Пост отправлен на модерацию!",
            reply_markup=main_menu()
        )
    except Exception as e:
        error_msg = f"Ошибка в handle_text: {e}"
        send_error_to_admins(error_msg, f"User ID: {message.from_user.id}")
        bot.send_message(message.chat.id, "❌ Ошибка при отправке поста.")

# Обработчики медиа
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    process_media(message, 'photo')

@bot.message_handler(content_types=['video'])
def handle_video(message):
    process_media(message, 'video')

@bot.message_handler(content_types=['sticker'])
def handle_sticker(message):
    process_media(message, 'sticker')

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    process_media(message, 'voice')

@bot.message_handler(content_types=['video_note'])
def handle_video_note(message):
    process_media(message, 'video_note')

@bot.message_handler(content_types=['media_group'])
def handle_media_group(message):
    process_media(message, 'media_group')

# Общий обработчик медиа
def process_media(message, media_type):
    # Пропускаем сообщения, если пользователь заполняет анкету или в собеседовании
    if is_in_admin_application_process(message.from_user.id) or is_in_interview_process(message.from_user.id):
        return
    
    try:
        data = load_posts()
        user_id = message.from_user.id
        
        if str(user_id) in data.get("user_states", {}) and data["user_states"].get(str(user_id)) == "banned":
            bot.send_message(message.chat.id, "❌ Вы заблокированы и не можете отправлять посты.")
            return
        
        post_id = generate_post_id()
        username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        
        # Получение file_id в зависимости от типа медиа
        file_id = None
        if media_type == 'photo':
            file_id = message.photo[-1].file_id
        elif media_type == 'video':
            file_id = message.video.file_id
        elif media_type == 'sticker':
            file_id = message.sticker.file_id
        elif media_type == 'voice':
            file_id = message.voice.file_id
        elif media_type == 'video_note':
            file_id = message.video_note.file_id
        
        # Сохранение поста
        if "posts" not in data:
            data["posts"] = {}
            
        data["posts"][str(post_id)] = {
            "user_id": user_id,
            "username": username,
            "text": message.caption or "",
            "media_type": media_type,
            "file_id": file_id,
            "status": "pending",
            "date": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        
        # Для медиа-групп
        if media_type == 'media_group':
            data["posts"][str(post_id)]["media_group_id"] = getattr(message, 'media_group_id', None)
        
        # Отправка в группу модерации
        media_names = {
            'photo': 'фото',
            'video': 'видео', 
            'sticker': 'стикер',
            'voice': 'голосовое сообщение',
            'video_note': 'видео-заметка',
            'media_group': 'медиа-альбом'
        }
        
        caption_text = f"\n\n{message.caption}" if message.caption else ""
        admin_text = f"👤 {username} (ID {user_id}) предложил пост #{post_id} ({media_names[media_type]}){caption_text}"
        
        # Отправка соответствующего типа медиа в группу модерации
        try:
            if media_type == 'photo':
                admin_message = bot.send_photo(ADMIN_GROUP_ID, file_id, caption=admin_text, reply_markup=moderation_buttons(post_id))
            elif media_type == 'video':
                admin_message = bot.send_video(ADMIN_GROUP_ID, file_id, caption=admin_text, reply_markup=moderation_buttons(post_id))
            elif media_type == 'sticker':
                msg1 = bot.send_sticker(ADMIN_GROUP_ID, file_id)
                admin_message = bot.send_message(ADMIN_GROUP_ID, admin_text, reply_markup=moderation_buttons(post_id))
            elif media_type == 'voice':
                admin_message = bot.send_voice(ADMIN_GROUP_ID, file_id, caption=admin_text, reply_markup=moderation_buttons(post_id))
            elif media_type == 'video_note':
                msg1 = bot.send_video_note(ADMIN_GROUP_ID, file_id)
                admin_message = bot.send_message(ADMIN_GROUP_ID, admin_text, reply_markup=moderation_buttons(post_id))
            elif media_type == 'media_group':
                admin_message = bot.send_message(ADMIN_GROUP_ID, admin_text, reply_markup=moderation_buttons(post_id))
        except Exception as e:
            # Если не удалось отправить с медиа, отправляем текстовое сообщение
            admin_message = bot.send_message(ADMIN_GROUP_ID, admin_text, reply_markup=moderation_buttons(post_id))
        
        data["posts"][str(post_id)]["admin_message_id"] = admin_message.message_id
        save_posts(data)
        
        bot.send_message(
            message.chat.id,
            f"✅ {media_names[media_type].capitalize()} отправлено на модерацию!",
            reply_markup=main_menu()
        )
    except Exception as e:
        error_msg = f"Ошибка в process_media ({media_type}): {e}"
        send_error_to_admins(error_msg, f"User ID: {message.from_user.id}")
        bot.send_message(message.chat.id, f"❌ Ошибка при отправке {media_type}.")

# Запуск бота
if __name__ == "__main__":
    print("Бот запущен...")
    try:
        bot.infinity_polling()
    except Exception as e:
        error_msg = f"Критическая ошибка бота: {e}"
        send_error_to_admins(error_msg)
        print(f"Критическая ошибка: {e}")
