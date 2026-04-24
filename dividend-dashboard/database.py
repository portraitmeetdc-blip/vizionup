import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "portfolio.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL UNIQUE,
            shares REAL NOT NULL,
            avg_cost REAL NOT NULL,
            date_added TEXT NOT NULL,
            notes TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL UNIQUE,
            target_price REAL,
            date_added TEXT NOT NULL,
            notes TEXT DEFAULT ''
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
    conn.commit()
    conn.close()


def add_holding(ticker, shares, avg_cost, notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO holdings (ticker, shares, avg_cost, date_added, notes)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(ticker) DO UPDATE SET
               shares = shares + excluded.shares,
               avg_cost = excluded.avg_cost,
               notes = excluded.notes""",
        (ticker.upper(), shares, avg_cost, datetime.now().isoformat(), notes),
    )
    conn.commit()
    conn.close()


def remove_holding(ticker):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM holdings WHERE ticker = ?", (ticker.upper(),))
    conn.commit()
    conn.close()


def get_holdings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings ORDER BY ticker")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def update_holding(ticker, shares=None, avg_cost=None, notes=None):
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
        params.append(ticker.upper())
        cursor.execute(
            f"UPDATE holdings SET {', '.join(updates)} WHERE ticker = ?", params
        )
        conn.commit()
    conn.close()


def add_to_watchlist(ticker, target_price=None, notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO watchlist (ticker, target_price, date_added, notes)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(ticker) DO UPDATE SET
               target_price = excluded.target_price,
               notes = excluded.notes""",
        (ticker.upper(), target_price, datetime.now().isoformat(), notes),
    )
    conn.commit()
    conn.close()


def remove_from_watchlist(ticker):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))
    conn.commit()
    conn.close()


def get_watchlist():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM watchlist ORDER BY ticker")
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
