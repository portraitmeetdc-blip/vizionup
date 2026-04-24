import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "media.db")

PLATFORMS = [
    "Adobe Stock",
    "Shutterstock",
    "Getty Images",
    "iStock",
    "Alamy",
    "Pond5",
    "500px",
    "Dreamstime",
    "EyeEm",
    "Other",
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS media_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            width INTEGER DEFAULT 0,
            height INTEGER DEFAULT 0,
            title TEXT DEFAULT '',
            description TEXT DEFAULT '',
            keywords TEXT DEFAULT '',
            category TEXT DEFAULT '',
            date_added TEXT NOT NULL,
            date_taken TEXT DEFAULT '',
            camera_model TEXT DEFAULT '',
            location TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            upload_date TEXT,
            asset_id TEXT DEFAULT '',
            review_status TEXT DEFAULT 'pending',
            notes TEXT DEFAULT '',
            FOREIGN KEY (media_id) REFERENCES media_files(id)
        );

        CREATE TABLE IF NOT EXISTS earnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            media_id INTEGER,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            earning_date TEXT NOT NULL,
            earning_type TEXT DEFAULT 'royalty',
            notes TEXT DEFAULT '',
            FOREIGN KEY (media_id) REFERENCES media_files(id)
        );

        CREATE TABLE IF NOT EXISTS platform_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL UNIQUE,
            username TEXT DEFAULT '',
            contributor_id TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            date_added TEXT NOT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_media_path
            ON media_files(file_path);

        CREATE INDEX IF NOT EXISTS idx_uploads_media
            ON uploads(media_id);

        CREATE INDEX IF NOT EXISTS idx_earnings_platform
            ON earnings(platform);
    """)
    conn.commit()
    conn.close()


# --- Media Files ---

def add_media_file(file_path, file_name, file_type, file_size=0,
                   width=0, height=0, title="", description="",
                   keywords="", category="", date_taken="", camera_model="",
                   location=""):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO media_files
               (file_path, file_name, file_type, file_size, width, height,
                title, description, keywords, category, date_added,
                date_taken, camera_model, location)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (file_path, file_name, file_type, file_size, width, height,
             title, description, keywords, category, datetime.now().isoformat(),
             date_taken, camera_model, location),
        )
        conn.commit()
        media_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        media_id = None  # Already exists
    conn.close()
    return media_id


def get_media_files(file_type=None, category=None, limit=100, offset=0):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM media_files WHERE 1=1"
    params = []
    if file_type:
        query += " AND file_type = ?"
        params.append(file_type)
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY date_added DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_media_file(media_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM media_files WHERE id = ?", (media_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_media_file(media_id, **kwargs):
    conn = get_connection()
    cursor = conn.cursor()
    allowed = {"title", "description", "keywords", "category", "location"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [media_id]
        cursor.execute(f"UPDATE media_files SET {set_clause} WHERE id = ?", params)
        conn.commit()
    conn.close()


def delete_media_file(media_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM uploads WHERE media_id = ?", (media_id,))
    cursor.execute("DELETE FROM media_files WHERE id = ?", (media_id,))
    conn.commit()
    conn.close()


def get_media_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM media_files")
    total = cursor.fetchone()["total"]
    cursor.execute("SELECT file_type, COUNT(*) as count FROM media_files GROUP BY file_type")
    by_type = {row["file_type"]: row["count"] for row in cursor.fetchall()}
    conn.close()
    return {"total": total, "by_type": by_type}


# --- Uploads ---

def add_upload(media_id, platform, status="pending", asset_id="", notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO uploads (media_id, platform, status, upload_date, asset_id, notes)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (media_id, platform, status, datetime.now().isoformat(), asset_id, notes),
    )
    conn.commit()
    upload_id = cursor.lastrowid
    conn.close()
    return upload_id


def update_upload(upload_id, status=None, review_status=None, asset_id=None, notes=None):
    conn = get_connection()
    cursor = conn.cursor()
    updates = []
    params = []
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if review_status is not None:
        updates.append("review_status = ?")
        params.append(review_status)
    if asset_id is not None:
        updates.append("asset_id = ?")
        params.append(asset_id)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    if updates:
        params.append(upload_id)
        cursor.execute(
            f"UPDATE uploads SET {', '.join(updates)} WHERE id = ?", params
        )
        conn.commit()
    conn.close()


def get_uploads_for_media(media_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM uploads WHERE media_id = ? ORDER BY upload_date DESC", (media_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_upload_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT platform, status, COUNT(*) as count
        FROM uploads GROUP BY platform, status
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# --- Earnings ---

def add_earning(platform, amount, earning_date, media_id=None,
                earning_type="royalty", notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO earnings (platform, media_id, amount, earning_date,
           earning_type, notes)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (platform, media_id, amount, earning_date, earning_type, notes),
    )
    conn.commit()
    conn.close()


def get_earnings(platform=None, start_date=None, end_date=None):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM earnings WHERE 1=1"
    params = []
    if platform:
        query += " AND platform = ?"
        params.append(platform)
    if start_date:
        query += " AND earning_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND earning_date <= ?"
        params.append(end_date)
    query += " ORDER BY earning_date DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_earnings_summary():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT platform,
               SUM(amount) as total,
               COUNT(*) as transactions,
               MIN(earning_date) as first_earning,
               MAX(earning_date) as last_earning
        FROM earnings
        GROUP BY platform
        ORDER BY total DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT SUM(amount) as grand_total FROM earnings")
    grand = cursor.fetchone()["grand_total"] or 0
    conn.close()
    return {"by_platform": rows, "grand_total": grand}


# --- Platform Accounts ---

def add_platform_account(platform, username="", contributor_id=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO platform_accounts (platform, username, contributor_id, date_added)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(platform) DO UPDATE SET
               username = excluded.username,
               contributor_id = excluded.contributor_id""",
        (platform, username, contributor_id, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_platform_accounts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM platform_accounts WHERE is_active = 1 ORDER BY platform")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
