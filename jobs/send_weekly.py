#!/bin/bash
# Cron job untuk Weekly Report
# Setup: crontab -e
# Tambahkan baris ini (setiap Senin jam 08:00 WITA = 00:00 UTC):
# 0 0 * * 1 cd /path/to/AgenTA && python jobs/send_weekly.py >> /var/log/crypto_bot.log 2>&1

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from datetime import datetime


def get_db_path():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "data", "journal.db")


def get_active_users():
    conn = sqlite3.connect(get_db_path())
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
    from data.journal import format_weekly_report
    return format_weekly_report(user_id)


def main():
    print(f"[{datetime.now()}] 📊 Weekly Report Scheduler Started")
    
    users = get_active_users()
    print(f"Found {len(users)} active users this week")
    
    for user_id in users:
        try:
            report = generate_report(user_id)
            print(f"Generated report for user {user_id}")
            # Di production, kirim ke user via bot
            print(f"To send: {report[:100]}...")
        except Exception as e:
            print(f"Error for user {user_id}: {e}")
    
    print(f"[{datetime.now()}] Weekly Report Scheduler Complete")


if __name__ == "__main__":
    main()