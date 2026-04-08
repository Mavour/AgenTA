import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "journal.db")


def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT user_id 
        FROM journal 
        WHERE created_at >= datetime('now', '-7 days')
    """)
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users


def get_all_chat_ids():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM user_settings")
    chat_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return chat_ids


if __name__ == "__main__":
    users = get_all_users()
    print(f"Active users this week: {users}")