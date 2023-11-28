from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
import sqlite3
import threading

# Создаем объект блокировки для безопасного использования SQLite-соединения в разных потоках
db_lock = threading.Lock()

# Список ID чатов, в которые будут публиковаться заказы
group_chat_ids = [-1002086937947, -4080817111]

def create_tables():
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()

    # Таблица заказов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            telegram_id INTEGER,
            login TEXT,
            order_text TEXT
        )
    ''')

    # Таблица забаненных пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS banned_users (
            ban_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            telegram_id INTEGER,
            login TEXT,
            reason TEXT,
            ban_duration INTEGER
        )
    ''')

    # Таблица администраторов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    ''')

    conn.commit()
    conn.close()

def get_admins():
    with db_lock:
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM admins")
        admins = [row[0] for row in cursor.fetchall()]
        conn.close()
    return admins

def add_admin(user_id):
    with db_lock:
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM admins WHERE user_id=?", (user_id,))
        existing_admin = cursor.fetchone()

        if existing_admin is None:
            cursor.execute('''
                INSERT INTO admins (user_id)
                VALUES (?)
            ''', (user_id,))

        conn.commit()
        conn.close()

def add_order(user_id, username, telegram_id, login, order_text):
    with db_lock:
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO orders (user_id, username, telegram_id, login, order_text)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, telegram_id, login, order_text))

        conn.commit()
        conn.close()

def ban_user(user_id, telegram_id, login, reason, ban_duration):
    with db_lock:
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO banned_users (user_id, telegram_id, login, reason, ban_duration)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, telegram_id, login, reason, ban_duration))

        conn.commit()
        conn.close()

def unban_user(user_id):
    with db_lock:
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()

        cursor.execute('DELETE FROM banned_users WHERE user_id=?', (user_id,))

        conn.commit()
        conn.close()

def is_admin(user_id):
    return user_id in get_admins()

def is_banned(user_id):
    with db_lock:
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM banned_users WHERE user_id=?", (user_id,))
        result = cursor.fetchone()
        conn.close()
    return result is not None




def get_last_order_id(user_id):
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()

    # Предполагаем, что в таблице orders есть поле order_id
    cursor.execute('SELECT MAX(order_id) FROM orders WHERE user_id=?', (user_id,))
    last_order_id = cursor.fetchone()[0] or 0  # Если last_order_id равен None, присвоим 0

    conn.close()

    return last_order_id

def ask_confirmation(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    telegram_id = update.message.from_user.id
    login = update.message.from_user.username
    order_text = update.message.text

    # Проверка, что сообщение было отправлено лично (не в группе)
    if update.message.chat.type == 'private':
        keyboard = [[InlineKeyboardButton("Да", callback_data='confirm'),
                     InlineKeyboardButton("Нет", callback_data='cancel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(f'Вы уверены, что хотите разместить следующий заказ:\n{order_text}', reply_markup=reply_markup)

def messand_text_group(user_id,context,query,username,telegram_id,order_text):
            keyboard = []
            reply_markup = InlineKeyboardMarkup(keyboard)

            order_id = get_last_order_id(user_id)

            # Отправка заказа только в тот чат, в котором было отправлено исходное сообщение
            context.bot.send_message(chat_id='-4080817111', text=f'Заказ от пользователя https://t.me/{username} (Заказ #{order_id}):\n{order_text}', reply_markup=reply_markup)

            query.edit_message_text(f'Заказ от пользователя {username} ({telegram_id}):\n{order_text} успешно размещен.')

def confirm_order(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.username
    telegram_id = query.from_user.id
    login = query.from_user.username
    order_text = query.message.text.split('\n', 1)[1]  # Получаем текст заказа из сообщения

    # Проверка, не является ли пользователь забаненным
    if is_banned(user_id):
        query.edit_message_text('Вы забанены. Обратитесь к администратору для уточнения причины и срока бана.')
        return

    # Добавление заказа в базу данных
    add_order(user_id, username, telegram_id, login, order_text)

    # Проверка, является ли пользователь администратором
    if not is_admin(user_id):
        messand_text_group(user_id,context,query,username,telegram_id,order_text)
        return




    # Определение, в каком чате было отправлено исходное сообщение
    messand_text_group(user_id,context,query,username,telegram_id,order_text)

def cancel_order(update: Update, context: CallbackContext):
    query = update.callback_query
    query.edit_message_text("Вы отменили размещение заказа.")

def button(update: Update, context: CallbackContext):
    query = update.callback_query

    if query.data == 'confirm':
        confirm_order(update, context)
    elif query.data == 'cancel':
        cancel_order(update, context)
    elif query.data == 'yes':
        # Логика для подтверждения заказа администраторами
        pass
    elif query.data == 'no':
        query.edit_message_text("Пожалуйста, отправьте новое сообщение.")
    elif query.data == 'ban':
        # Логика для бана пользователя
        pass
    elif query.data == 'delete':
        # Логика для удаления заказа
        pass

if __name__ == "__main__":
    try:
        create_tables()

        # Получаем список администраторов из базы данных и добавляем их
        admins_from_db = get_admins()
        for admin_id in admins_from_db:
            add_admin(admin_id)

        print('start...')
        updater = Updater(token='6515313707:AAEDrizefCL9Ov_zCedCy0OtLfABBK2u9bQ', use_context=True)
        dp = updater.dispatcher

        # Добавляем обработчики
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, ask_confirmation))
        dp.add_handler(CallbackQueryHandler(button))

        # Запускаем бота
        updater.start_polling()


    except Exception as e:
        print(f'Error: {e}')
