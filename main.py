import os
import json
import datetime
from telebot import TeleBot, types
from telebot.util import quick_markup

# Константы
BOT_TOKEN = "8354515031:AAEnTTa0qdU8teKjwMv373llShkM4alH62Q"
ADMIN_GROUP_ID = -5026479411
CHANNEL_ID = -1002658375841
POSTS_FILE = "posts.json"
APPLICATIONS_FILE = "admin_applications.json"

# Инициализация бота
bot = TeleBot(BOT_TOKEN)

# Загрузка данных из JSON
def load_posts():
    if os.path.exists(POSTS_FILE):
        with open(POSTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                data = {"posts": {}, "user_states": {}}
                save_posts(data)
            return data
    return {"posts": {}, "user_states": {}}

def load_applications():
    if os.path.exists(APPLICATIONS_FILE):
        with open(APPLICATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"applications": {}, "user_states": {}}

# Сохранение данных в JSON
def save_posts(data):
    with open(POSTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_applications(data):
    with open(APPLICATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Генерация ID
def generate_post_id():
    data = load_posts()
    if not data["posts"]:
        return 1
    return max([int(i) for i in data["posts"].keys()]) + 1

def generate_application_id():
    data = load_applications()
    if not data["applications"]:
        return 1
    return max([int(i) for i in data["applications"].keys()]) + 1

# Главное меню
def main_menu():
    return quick_markup({
        '📝 Отправить пост': {'callback_data': 'send_post'},
        '📂 Мои посты': {'callback_data': 'my_posts'},
        '👑 Стать админом': {'callback_data': 'become_admin'}
    }, row_width=1)

# Меню после публикации
def after_publish_menu():
    return quick_markup({
        '📝 Отправить новый пост': {'callback_data': 'send_post'},
        '📂 Мои посты': {'callback_data': 'my_posts'}
    }, row_width=1)

# Кнопки модерации постов
def moderation_buttons(post_id):
    return quick_markup({
        '✅ Принять': {'callback_data': f'approve_{post_id}'},
        '❌ Отклонить': {'callback_data': f'reject_{post_id}'},
        '🚫 Заблокировать': {'callback_data': f'ban_{post_id}'}
    }, row_width=2)

# Кнопки модерации с разблокировкой
def moderation_buttons_unban(post_id):
    return quick_markup({
        '✅ Принять': {'callback_data': f'approve_{post_id}'},
        '❌ Отклонить': {'callback_data': f'reject_{post_id}'},
        '✅ Разблокировать': {'callback_data': f'unban_{post_id}'}
    }, row_width=2)

# Кнопки для анкеты админа
def admin_application_buttons(app_id):
    return quick_markup({
        '✅ Одобрить': {'callback_data': f'app_approve_{app_id}'},
        '❌ Отклонить': {'callback_data': f'app_reject_{app_id}'},
        '💬 Собеседование': {'callback_data': f'app_interview_{app_id}'}
    }, row_width=2)

# Проверка, находится ли пользователь в процессе заполнения анкеты админа
def is_in_admin_application_process(user_id):
    data = load_applications()
    return str(user_id) in data.get("user_states", {})

# Проверка, находится ли пользователь в процессе собеседования
def is_in_interview_process(user_id):
    data = load_applications()
    user_state = data.get("user_states", {}).get(str(user_id), {})
    return user_state.get("state") == "admin_interview"

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать в бот-предложку!\n\n"
        "Здесь вы можете предложить пост для публикации в канале или подать заявку на админа.",
        reply_markup=main_menu()
    )

# НОВЫЙ ФУНКЦИОНАЛ: Анкета для админа
@bot.callback_query_handler(func=lambda call: call.data == 'become_admin')
def start_admin_application(call):
    data = load_applications()
    user_id = call.from_user.id
    
    # Проверяем, не подавал ли пользователь уже заявку
    for app_id, application in data["applications"].items():
        if application["user_id"] == user_id and application["status"] == "pending":
            bot.answer_callback_query(call.id, "❌ Вы уже отправили заявку. Дождитесь ответа!")
            return
    
    # Начинаем процесс заполнения анкеты
    bot.send_message(
        call.message.chat.id,
        "👑 *Анкета на Админа в канал \"Вика Лайк\"* 👑\n\n"
        "Привет, подписчик! Решил(а) подать заявку на вакантное место в нашей тусовке? Отлично! "
        "Заполни эту форму, и мы её рассмотрим.\n\n"
        "*1. Твоё имя (или как тебя называть):*",
        parse_mode="Markdown"
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

# Обработчик текстовых сообщений для анкеты админа
@bot.message_handler(func=lambda message: is_in_admin_application_process(message.from_user.id))
def handle_admin_application(message):
    data = load_applications()
    user_id = message.from_user.id
    user_state = data["user_states"][str(user_id)]
    app_data = user_state["application_data"]
    current_state = user_state["state"]
    
    if current_state == "admin_app_1":
        app_data["name"] = message.text
        user_state["state"] = "admin_app_2"
        bot.send_message(message.chat.id, "*2. Твой возраст (просто цифра, нам не верить, а для статистики):*", parse_mode="Markdown")
    
    elif current_state == "admin_app_2":
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "❌ Пожалуйста, введите возраст цифрами:")
            return
        app_data["age"] = message.text
        user_state["state"] = "admin_app_3"
        bot.send_message(
            message.chat.id, 
            "*3. Расскажи, почему ты хочешь стать админом именно в этом канале?*\n"
            "(Не пиши \"потому что Вика крутая\", мы это и так знаем 😉):",
            parse_mode="Markdown"
        )
    
    elif current_state == "admin_app_3":
        app_data["reason"] = message.text
        user_state["state"] = "admin_app_4"
        bot.send_message(
            message.chat.id,
            "*4. Опыт есть? Был(а) ли админом/модератором в других чатах или каналах? Если да — где и что делал(а)?*",
            parse_mode="Markdown"
        )
    
    elif current_state == "admin_app_4":
        app_data["experience"] = message.text
        user_state["state"] = "admin_app_5"
        bot.send_message(
            message.chat.id,
            "*5. Представь, в комментариях начался хейт и срач из-за нового видео. Твои первые 3 действия?*",
            parse_mode="Markdown"
        )
    
    elif current_state == "admin_app_5":
        app_data["conflict_solution"] = message.text
        user_state["state"] = "admin_app_6"
        bot.send_message(
            message.chat.id,
            "*6. Сколько времени в сутки ты готов(а) уделять каналу?*\n(Будь честен, мы всё равно проверим 😜):",
            parse_mode="Markdown"
        )
    
    elif current_state == "admin_app_6":
        app_data["time"] = message.text
        user_state["state"] = "admin_app_7"
        bot.send_message(
            message.chat.id,
            "*7. Наша фишка — мемы и ирония. Предложи идею для нового рубрики или поста в канал:*",
            parse_mode="Markdown"
        )
    
    elif current_state == "admin_app_7":
        app_data["idea"] = message.text
        user_state["state"] = "admin_app_8"
        bot.send_message(
            message.chat.id,
            "*8. Твоё главное оружие как админа (строгость, чувство юмора, невероятное обаяние или что-то другое)?*",
            parse_mode="Markdown"
        )
    
    elif current_state == "admin_app_8":
        app_data["weapon"] = message.text
        user_state["state"] = "admin_app_9"
        bot.send_message(
            message.chat.id,
            "*9. Ссылка на твой Telegram-аккаунт (обязательно):*",
            parse_mode="Markdown"
        )
    
    elif current_state == "admin_app_9":
        app_data["telegram_link"] = message.text
        app_data["username"] = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        app_data["user_id"] = user_id
        
        # Завершаем анкету и отправляем в группу админов
        application_id = generate_application_id()
        data["applications"][str(application_id)] = {
            **app_data,
            "status": "pending",
            "date": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        
        # Удаляем состояние пользователя
        del data["user_states"][str(user_id)]
        
        # Формируем сообщение для админов
        admin_message = (
            "👑 *НОВАЯ ЗАЯВКА НА АДМИНА* 👑\n\n"
            f"🆔 *ID заявки:* #{application_id}\n"
            f"👤 *Пользователь:* {app_data['username']}\n"
            f"🔗 *Telegram:* {app_data['telegram_link']}\n"
            f"🆔 *User ID:* {user_id}\n"
            f"📅 *Дата подачи:* {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"*1. Имя:* {app_data['name']}\n"
            f"*2. Возраст:* {app_data['age']}\n"
            f"*3. Причина:* {app_data['reason']}\n"
            f"*4. Опыт:* {app_data['experience']}\n"
            f"*5. Решение конфликтов:* {app_data['conflict_solution']}\n"
            f"*6. Время:* {app_data['time']}\n"
            f"*7. Идея:* {app_data['idea']}\n"
            f"*8. Оружие:* {app_data['weapon']}\n"
        )
        
        # Отправляем в группу админов
        bot.send_message(
            ADMIN_GROUP_ID,
            admin_message,
            parse_mode="Markdown",
            reply_markup=admin_application_buttons(application_id)
        )
        
        save_applications(data)
        
        bot.send_message(
            message.chat.id,
            "✅ *Твоя анкета отправлена на рассмотрение! Ожидай ответа в ближайшее время.*\n\n"
            "*Удачи! И да пребудет с тобой лайк!* ✨",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
        return
    
    save_applications(data)

# Обработка действий админов с заявками
@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_approve_', 'app_reject_', 'app_interview_')))
def handle_admin_application_action(call):
    if call.message.chat.id != ADMIN_GROUP_ID:
        bot.answer_callback_query(call.id, "❌ Эта функция доступна только администраторам.")
        return
    
    data = load_applications()
    action, app_id = call.data.split('_', 2)[1:]
    application = data["applications"].get(app_id)
    
    if not application:
        bot.answer_callback_query(call.id, "❌ Заявка не найдена.")
        return
    
    admin_username = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
    
    if action == "approve":
        application["status"] = "approved"
        application["moderated_by"] = admin_username
        
        # Уведомляем пользователя
        try:
            bot.send_message(
                application["user_id"],
                "🎉 *Поздравляем! Твоя заявка на админа одобрена!*\n\n"
                "Скоро с тобой свяжутся для дальнейших инструкций. Добро пожаловать в команду! 👑",
                parse_mode="Markdown"
            )
        except:
            pass
        
        # Обновляем сообщение в группе
        new_text = f"{call.message.text}\n\n✅ ОДОБРЕНО {admin_username}"
        try:
            bot.edit_message_text(
                new_text,
                ADMIN_GROUP_ID,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=None
            )
        except:
            pass
        
    elif action == "reject":
        application["status"] = "rejected"
        application["moderated_by"] = admin_username
        
        # Уведомляем пользователя
        try:
            bot.send_message(
                application["user_id"],
                "😕 *К сожалению, твоя заявка на админа не была одобрена.*\n\n"
                "Не расстраивайся! Ты можешь продолжать участвовать в жизни канала и предложить пост.",
                parse_mode="Markdown"
            )
        except:
            pass
        
        # Обновляем сообщение в группе
        new_text = f"{call.message.text}\n\n❌ ОТКЛОНЕНО {admin_username}"
        try:
            bot.edit_message_text(
                new_text,
                ADMIN_GROUP_ID,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=None
            )
        except:
            pass
    
    elif action == "interview":
        # Сохраняем состояние для собеседования
        if "user_states" not in data:
            data["user_states"] = {}
        
        data["user_states"][str(application["user_id"])] = {
            "state": "admin_interview",
            "application_id": app_id,
            "interviewer": call.from_user.id
        }
        
        # Уведомляем админов в группе
        bot.send_message(
            ADMIN_GROUP_ID,
            f"💬 *Начат процесс собеседования с {application['username']}*\n\n"
            f"Админ {admin_username} проводит собеседование. Все сообщения от пользователя "
            f"будут пересылаться сюда для коллективного обсуждения.",
            parse_mode="Markdown"
        )
        
        # Уведомляем пользователя
        try:
            bot.send_message(
                application["user_id"],
                "💬 *Начат процесс собеседования!*\n\n"
                "Администраторы начали с тобой диалог. Отвечай на их вопросы здесь - все твои сообщения "
                "будут видны команде для принятия окончательного решения.",
                parse_mode="Markdown"
            )
        except:
            pass
        
        bot.answer_callback_query(call.id, "💬 Начат процесс собеседования")
    
    save_applications(data)
    if action != "interview":
        bot.answer_callback_query(call.id, "✅ Действие выполнено")

# Обработчик сообщений во время собеседования
@bot.message_handler(func=lambda message: is_in_interview_process(message.from_user.id))
def handle_interview_message(message):
    data = load_applications()
    user_id = message.from_user.id
    user_state = data["user_states"][str(user_id)]
    app_id = user_state["application_id"]
    application = data["applications"][app_id]
    
    # Пересылаем сообщение в группу админов
    try:
        forwarded_msg = bot.forward_message(ADMIN_GROUP_ID, message.chat.id, message.message_id)
        
        # Добавляем кнопки для завершения собеседования
        if hasattr(forwarded_msg, 'text') and forwarded_msg.text:
            bot.edit_message_text(
                f"💬 *Собеседование с {application['username']}:*\n\n{forwarded_msg.text}",
                ADMIN_GROUP_ID,
                forwarded_msg.message_id,
                parse_mode="Markdown",
                reply_markup=quick_markup({
                    '✅ Завершить (Принять)': {'callback_data': f'app_approve_{app_id}'},
                    '❌ Завершить (Отклонить)': {'callback_data': f'app_reject_{app_id}'}
                }, row_width=2)
            )
        else:
            # Для медиа-сообщений отправляем отдельное текстовое сообщение с кнопками
            bot.send_message(
                ADMIN_GROUP_ID,
                f"💬 *Медиа-сообщение от {application['username']} во время собеседования*",
                parse_mode="Markdown",
                reply_markup=quick_markup({
                    '✅ Завершить (Принять)': {'callback_data': f'app_approve_{app_id}'},
                    '❌ Завершить (Отклонить)': {'callback_data': f'app_reject_{app_id}'}
                }, row_width=2)
            )
    except Exception as e:
        print(f"Ошибка при пересылке сообщения собеседования: {e}")

# Обработчик команды /post{id}
@bot.message_handler(regexp=r'^/post\d+$')
def show_post(message):
    data = load_posts()
    post_id = message.text.replace('/post', '')
    
    if post_id not in data["posts"]:
        bot.send_message(message.chat.id, "❌ Пост не найден.")
        return
    
    post = data["posts"][post_id]
    
    if str(post["user_id"]) != str(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Это не ваш пост.")
        return
    
    # Отправка медиа в зависимости от типа
    if post["media_type"] == "text":
        bot.send_message(message.chat.id, f"📝 Текст поста:\n\n{post['text']}")
    
    elif post["media_type"] == "photo":
        bot.send_photo(message.chat.id, post["file_id"], caption=post["text"])
    
    elif post["media_type"] == "video":
        bot.send_video(message.chat.id, post["file_id"], caption=post["text"])
    
    elif post["media_type"] == "sticker":
        bot.send_sticker(message.chat.id, post["file_id"])
        if post["text"]:
            bot.send_message(message.chat.id, f"📝 Подпись:\n\n{post['text']}")
    
    elif post["media_type"] == "voice":
        bot.send_voice(message.chat.id, post["file_id"], caption=post["text"])
    
    elif post["media_type"] == "video_note":
        bot.send_video_note(message.chat.id, post["file_id"])
        if post["text"]:
            bot.send_message(message.chat.id, f"📝 Подпись:\n\n{post['text']}")
    
    elif post["media_type"] == "media_group":
        if post["text"]:
            bot.send_message(message.chat.id, f"📝 Подпись альбома:\n\n{post['text']}")
        else:
            bot.send_message(message.chat.id, "📷 Медиа-альбом (без подписи)")

# Обработчик callback-запросов для постов
@bot.callback_query_handler(func=lambda call: call.data in ['send_post', 'my_posts', 'back_to_main'])
def callback_handler(call):
    data = load_posts()
    user_id = call.from_user.id
    
    # Проверяем структуру данных
    if "user_states" not in data:
        data["user_states"] = {}
    if "posts" not in data:
        data["posts"] = {}
    
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
        for post_id, post in data["posts"].items():
            if str(post["user_id"]) == str(user_id):
                status_emoji = {
                    "approved": "✅",
                    "rejected": "❌", 
                    "pending": "⏳"
                }.get(post["status"], "⏳")
                
                date = post.get("date", "Неизвестно")
                user_posts.append(f"🆔 /post{post_id} — {status_emoji} {post['status']} ({date})")
        
        if user_posts:
            bot.edit_message_text(
                "\n".join(user_posts),
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
            "Здесь вы можете предложить пост для публикации в канале или подать заявку на админа.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu()
        )
        bot.answer_callback_query(call.id)

# Обработка модерации постов
@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_', 'ban_', 'unban_')))
def moderation_handler(call):
    if call.message.chat.id != ADMIN_GROUP_ID:
        bot.answer_callback_query(call.id, "❌ Эта функция доступна только администраторам.")
        return
    
    data = load_posts()
    action, post_id = call.data.split('_', 1)
    post = data["posts"].get(post_id)
    
    if not post:
        bot.answer_callback_query(call.id, "❌ Пост не найден.")
        return
    
    admin_username = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
    
    if action == 'approve':
        # Публикация поста в канал
        try:
            if post["media_type"] == "text":
                bot.send_message(CHANNEL_ID, post["text"])
            elif post["media_type"] == "photo":
                bot.send_photo(CHANNEL_ID, post["file_id"], caption=post["text"])
            elif post["media_type"] == "video":
                bot.send_video(CHANNEL_ID, post["file_id"], caption=post["text"])
            elif post["media_type"] == "sticker":
                bot.send_sticker(CHANNEL_ID, post["file_id"])
            elif post["media_type"] == "voice":
                bot.send_voice(CHANNEL_ID, post["file_id"], caption=post["text"])
            elif post["media_type"] == "video_note":
                bot.send_video_note(CHANNEL_ID, post["file_id"])
            elif post["media_type"] == "media_group":
                if post["text"]:
                    bot.send_message(CHANNEL_ID, post["text"])
            
            post["status"] = "approved"
            post["moderated_by"] = admin_username
            
            # Уведомление пользователя
            try:
                bot.send_message(
                    post["user_id"],
                    "🎉 Ваш пост опубликован!\nХотите отправить новый?",
                    reply_markup=after_publish_menu()
                )
            except:
                pass  # Пользователь мог заблокировать бота
            
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ Ошибка публикации: {e}")
            return
    
    elif action == 'reject':
        post["status"] = "rejected"
        post["moderated_by"] = admin_username
        
        # Уведомление пользователя
        try:
            bot.send_message(post["user_id"], "😕 Ваш пост был отклонён.")
        except:
            pass  # Пользователь мог заблокировать бота
    
    elif action == 'ban':
        data["user_states"][str(post["user_id"])] = "banned"
        # Замена кнопки на разблокировку
        try:
            bot.edit_message_reply_markup(
                ADMIN_GROUP_ID,
                call.message.message_id,
                reply_markup=moderation_buttons_unban(post_id)
            )
        except:
            pass
        bot.answer_callback_query(call.id, "✅ Пользователь заблокирован")
    
    elif action == 'unban':
        if str(post["user_id"]) in data["user_states"]:
            del data["user_states"][str(post["user_id"])]
        # Замена кнопки на блокировку
        try:
            bot.edit_message_reply_markup(
                ADMIN_GROUP_ID,
                call.message.message_id,
                reply_markup=moderation_buttons(post_id)
            )
        except:
            pass
        bot.answer_callback_query(call.id, "✅ Пользователь разблокирован")
    
    # Обновление сообщения в группе модерации только для текстовых сообщений
    if action in ['approve', 'reject']:
        try:
            # Получаем текущий текст сообщения
            current_text = call.message.text or call.message.caption or ""
            
            status_text = {
                'approve': f"✅ Принято {admin_username}",
                'reject': f"❌ Отклонено {admin_username}"
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
            print(f"Ошибка при редактировании сообщения: {e}")
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
    if action not in ['ban', 'unban']:
        bot.answer_callback_query(call.id, "✅ Действие выполнено")

# Обработчик текстовых сообщений (посты)
@bot.message_handler(content_types=['text'])
def handle_text(message):
    # Пропускаем сообщения, если пользователь заполняет анкету или в собеседовании
    if is_in_admin_application_process(message.from_user.id) or is_in_interview_process(message.from_user.id):
        return
    
    data = load_posts()
    user_id = message.from_user.id
    
    if str(user_id) in data.get("user_states", {}) and data["user_states"].get(str(user_id)) == "banned":
        bot.send_message(message.chat.id, "❌ Вы заблокированы и не можете отправлять посты.")
        return
    
    post_id = generate_post_id()
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    
    # Сохранение поста
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

# Обработчик фото
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    process_media(message, 'photo')

# Обработчик видео
@bot.message_handler(content_types=['video'])
def handle_video(message):
    process_media(message, 'video')

# Обработчик стикеров
@bot.message_handler(content_types=['sticker'])
def handle_sticker(message):
    process_media(message, 'sticker')

# Обработчик голосовых сообщений
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    process_media(message, 'voice')

# Обработчик видео-заметок
@bot.message_handler(content_types=['video_note'])
def handle_video_note(message):
    process_media(message, 'video_note')

# Общий обработчик медиа
def process_media(message, media_type):
    # Пропускаем сообщения, если пользователь заполняет анкету или в собеседовании
    if is_in_admin_application_process(message.from_user.id) or is_in_interview_process(message.from_user.id):
        return
    
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
    data["posts"][str(post_id)] = {
        "user_id": user_id,
        "username": username,
        "text": message.caption or "",
        "media_type": media_type,
        "file_id": file_id,
        "status": "pending",
        "date": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    
    # Отправка в группу модерации
    media_names = {
        'photo': 'фото',
        'video': 'видео', 
        'sticker': 'стикер',
        'voice': 'голосовое сообщение',
        'video_note': 'видео-заметка'
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

# Обработчик медиа-групп (альбомов)
@bot.message_handler(content_types=['media_group'])
def handle_media_group(message):
    # Пропускаем сообщения, если пользователь заполняет анкету или в собеседовании
    if is_in_admin_application_process(message.from_user.id) or is_in_interview_process(message.from_user.id):
        return
    
    data = load_posts()
    user_id = message.from_user.id
    
    if str(user_id) in data.get("user_states", {}) and data["user_states"].get(str(user_id)) == "banned":
        bot.send_message(message.chat.id, "❌ Вы заблокированы и не можете отправлять посты.")
        return
    
    # Для медиа-групп обрабатываем только первое сообщение
    if message.media_group_id:
        # Проверяем, не обрабатывали ли мы уже эту группу
        for post in data["posts"].values():
            if post.get("media_group_id") == message.media_group_id:
                return
    
    post_id = generate_post_id()
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    
    # Сохранение поста
    data["posts"][str(post_id)] = {
        "user_id": user_id,
        "username": username,
        "text": message.caption or "",
        "media_type": "media_group",
        "file_id": None,
        "media_group_id": message.media_group_id,
        "status": "pending",
        "date": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    
    # Отправка в группу модерации
    caption_text = f"\n\n{message.caption}" if message.caption else ""
    admin_message = bot.send_message(
        ADMIN_GROUP_ID,
        f"👤 {username} (ID {user_id}) предложил пост #{post_id} (медиа-альбом){caption_text}",
        reply_markup=moderation_buttons(post_id)
    )
    
    data["posts"][str(post_id)]["admin_message_id"] = admin_message.message_id
    save_posts(data)
    
    bot.send_message(
        message.chat.id,
        "✅ Медиа-альбом отправлен на модерацию!",
        reply_markup=main_menu()
    )

# Запуск бота
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
