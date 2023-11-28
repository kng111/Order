import sqlite3

# Создание таблиц в базе данных
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

# Пример добавления администратора в базу данных
def add_admin(user_id):
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO admins (user_id)
        VALUES (?)
    ''', (user_id,))

    conn.commit()
    conn.close()

# Пример использования
if __name__ == '__main__':
    create_tables()

    # Добавление администратора для примера
    add_admin(1377050746)
