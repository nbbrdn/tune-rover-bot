import sqlite3
from datetime import datetime

DB_FILE = "database.db"


def create_table():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY, 
            username TEXT, 
            is_admin INTEGER,
            created_at TIMESTAMP, 
            updated_at TIMESTAMP
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS albums(
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            artist TEXT, 
            title TEXT, 
            label TEXT, 
            release_year INTEGER,
            cover_path TEXT,
            itunes_uri TEXT,
            ymusic_uri TEXT,
            youtube_uri TEXT,
            spotify_uri TEXT,
            created_at TIMESTAMP
        );
        """
    )

    conn.commit()
    conn.close()


def get_user_role(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Получаем роль пользователя
    cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
    role = cursor.fetchone()

    conn.close()

    return role[0] if role else 0


def add_user(user_id, username, is_admin=False):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()

    if not existing_user:
        is_admin = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
        cursor.execute(
            "INSERT INTO users (user_id, username, is_admin, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, is_admin, current_time, current_time),
        )
        conn.commit()
    else:
        cursor.execute(
            "UPDATE users SET username = ?, is_admin = ?, updated_at = ? WHERE user_id = ?",
            (username, is_admin, current_time, user_id),
        )
        conn.commit()
    conn.close()


def get_random_album():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT title, artist, label, release_year, cover_path, itunes_uri, ymusic_uri FROM albums ORDER BY RANDOM() LIMIT 1"
    )
    random_album = cursor.fetchone()

    conn.close()

    return random_album


def add_album(title, artist, label, release_year, cover_path):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO albums (
            title,
            artist,
            label,
            release_year,
            cover_path,
            created_at
        ) VALUES(?, ?, ?, ?, ?, ?);
        """,
        (
            title,
            artist,
            label,
            release_year,
            cover_path,
            current_time,
        ),
    )

    conn.commit()
    conn.close()
