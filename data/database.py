import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "journal.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            pair TEXT,
            timeframe TEXT,
            analysis TEXT,
            signal TEXT,
            price_entry REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_seen DATETIME
        )
    """)
    
    conn.commit()
    conn.close()


def get_connection():
    return sqlite3.connect(DB_PATH)


def add_journal(user_id: int, pair: str, timeframe: str, analysis: str, signal: str = None, price_entry: float = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO journal (user_id, pair, timeframe, analysis, signal, price_entry)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, pair, timeframe, analysis, signal, price_entry))
    conn.commit()
    conn.close()


def get_user_journal(user_id: int, limit: int = 10, pair_filter: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    
    if pair_filter:
        cursor.execute("""
            SELECT id, pair, timeframe, analysis, signal, price_entry, created_at
            FROM journal
            WHERE user_id = ? AND pair LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, f"%{pair_filter}%", limit))
    else:
        cursor.execute("""
            SELECT id, pair, timeframe, analysis, signal, price_entry, created_at
            FROM journal
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
    
    results = cursor.fetchall()
    conn.close()
    return results


def clear_user_journal(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM journal WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_weekly_stats(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN signal = 'bullish' THEN 1 ELSE 0 END) as bullish,
            SUM(CASE WHEN signal = 'bearish' THEN 1 ELSE 0 END) as bearish,
            pair,
            COUNT(*) as count
        FROM journal
        WHERE user_id = ? AND created_at >= datetime('now', '-7 days')
        GROUP BY pair
        ORDER BY count DESC
    """, (user_id,))
    
    results = cursor.fetchall()
    conn.close()
    return results


def update_user(user_id: int, username: str = None, first_name: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO user_settings (user_id, username, first_name, last_seen)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, first_name, datetime.now()))
    conn.commit()
    conn.close()


init_db()