import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import get_weekly_stats, get_user_journal
from datetime import datetime, timedelta


def get_all_users():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "journal.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT user_id 
        FROM journal 
        WHERE created_at >= datetime('now', '-7 days')
    """)
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users


def generate_report(user_id: int) -> str:
    from data.journal import format_weekly_report as format_report
    return format_report(user_id)


def run():
    print(f"[{datetime.now()}] Starting weekly report job...")
    
    users = get_all_users()
    print(f"Found {len(users)} active users")
    
    if not users:
        print("No active users found")
        return
    
    print("To send reports to users, this script needs access to the bot.")
    print("In production, use this with cron + bot API.")
    print(f"\nUsers to send: {users}")
    
    print(f"[{datetime.now()}] Weekly report job complete")


if __name__ == "__main__":
    run()