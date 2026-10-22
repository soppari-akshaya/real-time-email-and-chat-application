from werkzeug.security import generate_password_hash
from database import get_db, init_db

def seed_sqlite():
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM messages;")
    cursor.execute("DELETE FROM conversation_members;")
    cursor.execute("DELETE FROM conversations;")
    cursor.execute("DELETE FROM users;")
    cursor.execute("DELETE FROM sqlite_sequence;")

    default_pwd = generate_password_hash('password123')

    users_data = [
        (1, 'Akshaya', 'akshaya@gmail.com', default_pwd, 0),
        (2, 'Harika', 'harika@gmail.com', default_pwd, 0),
        (3, 'Himaja', 'himaja@gmail.com', default_pwd, 0)
    ]
    cursor.executemany("""
        INSERT INTO users (id, name, email, password_hash, is_online, created_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, users_data)

    cursor.execute("INSERT INTO conversations (id, is_group, name, created_at) VALUES (1, 0, NULL, CURRENT_TIMESTAMP)")
    cursor.execute("""
        INSERT INTO conversation_members (conversation_id, user_id, is_admin, last_read_time)
        VALUES (1, 1, 1, CURRENT_TIMESTAMP), (1, 2, 0, CURRENT_TIMESTAMP)
    """)

    cursor.execute("""
        INSERT INTO messages (conversation_id, sender_id, sender_name, text, is_edited, is_deleted, created_at)
        VALUES 
        (1, 1, 'Akshaya', 'Hi Harika, have you started Module 2?', 0, 0, CURRENT_TIMESTAMP),
        (1, 2, 'Harika', 'Hey Akshaya! Yes, the real-time chat with SQLite is working great.', 0, 0, CURRENT_TIMESTAMP)
    """)

    cursor.execute("INSERT INTO conversations (id, is_group, name, created_at) VALUES (2, 1, 'Project Team', CURRENT_TIMESTAMP)")
    cursor.execute("""
        INSERT INTO conversation_members (conversation_id, user_id, is_admin, last_read_time)
        VALUES 
        (2, 1, 1, CURRENT_TIMESTAMP),
        (2, 2, 0, CURRENT_TIMESTAMP),
        (2, 3, 0, CURRENT_TIMESTAMP)
    """)

    cursor.execute("""
        INSERT INTO messages (conversation_id, sender_id, sender_name, text, is_edited, is_deleted, created_at)
        VALUES (2, 1, 'Akshaya', 'Welcome everyone to our project chat on SQLite!', 0, 0, CURRENT_TIMESTAMP)
    """)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    seed_sqlite()
