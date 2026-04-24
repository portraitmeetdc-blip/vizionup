import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "portfolio.db")

FAMILY_PROFILES = [
    {"name": "Michael", "icon": "👨🏾", "role": "Dad"},
    {"name": "Charlene", "icon": "👩🏾", "role": "Mom"},
    {"name": "Sean", "icon": "👦🏾", "role": "Son"},
    {"name": "Jaxxon", "icon": "👶🏾", "role": "Son"},
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            icon TEXT DEFAULT '',
            role TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL DEFAULT 1,
            ticker TEXT NOT NULL,
            shares REAL NOT NULL,
            avg_cost REAL NOT NULL,
            date_added TEXT NOT NULL,
            notes TEXT DEFAULT '',
            UNIQUE(profile_id, ticker),
            FOREIGN KEY (profile_id) REFERENCES profiles(id)
        );

        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL DEFAULT 1,
            ticker TEXT NOT NULL,
            target_price REAL,
            date_added TEXT NOT NULL,
            notes TEXT DEFAULT '',
            UNIQUE(profile_id, ticker),
            FOREIGN KEY (profile_id) REFERENCES profiles(id)
        );

        CREATE TABLE IF NOT EXISTS dividend_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            amount REAL NOT NULL,
            ex_date TEXT,
            pay_date TEXT,
            recorded_at TEXT NOT NULL
        );
    """)

    # Seed family profiles if empty
    cursor.execute("SELECT COUNT(*) FROM profiles")
    if cursor.fetchone()[0] == 0:
        for p in FAMILY_PROFILES:
            cursor.execute(
                "INSERT INTO profiles (name, icon, role) VALUES (?, ?, ?)",
                (p["name"], p["icon"], p["role"]),
            )

    conn.commit()
    conn.close()


def get_profiles():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles ORDER BY id")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def add_holding(ticker, shares, avg_cost, notes="", profile_id=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO holdings (profile_id, ticker, shares, avg_cost, date_added, notes)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(profile_id, ticker) DO UPDATE SET
               shares = shares + excluded.shares,
               avg_cost = excluded.avg_cost,
               notes = excluded.notes""",
        (profile_id, ticker.upper(), shares, avg_cost, datetime.now().isoformat(), notes),
    )
    conn.commit()
    conn.close()


def remove_holding(ticker, profile_id=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM holdings WHERE ticker = ? AND profile_id = ?", (ticker.upper(), profile_id))
    conn.commit()
    conn.close()


def get_holdings(profile_id=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings WHERE profile_id = ? ORDER BY ticker", (profile_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def update_holding(ticker, shares=None, avg_cost=None, notes=None, profile_id=1):
    conn = get_connection()
    cursor = conn.cursor()
    updates = []
    params = []
    if shares is not None:
        updates.append("shares = ?")
        params.append(shares)
    if avg_cost is not None:
        updates.append("avg_cost = ?")
        params.append(avg_cost)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    if updates:
        params.extend([ticker.upper(), profile_id])
        cursor.execute(
            f"UPDATE holdings SET {', '.join(updates)} WHERE ticker = ? AND profile_id = ?", params
        )
        conn.commit()
    conn.close()


def add_to_watchlist(ticker, target_price=None, notes="", profile_id=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO watchlist (profile_id, ticker, target_price, date_added, notes)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(profile_id, ticker) DO UPDATE SET
               target_price = excluded.target_price,
               notes = excluded.notes""",
        (profile_id, ticker.upper(), target_price, datetime.now().isoformat(), notes),
    )
    conn.commit()
    conn.close()


def remove_from_watchlist(ticker, profile_id=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM watchlist WHERE ticker = ? AND profile_id = ?", (ticker.upper(), profile_id))
    conn.commit()
    conn.close()


def get_watchlist(profile_id=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM watchlist WHERE profile_id = ? ORDER BY ticker", (profile_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def save_dividend_history(ticker, amount, ex_date=None, pay_date=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO dividend_history (ticker, amount, ex_date, pay_date, recorded_at)
           VALUES (?, ?, ?, ?, ?)""",
        (ticker.upper(), amount, ex_date, pay_date, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
