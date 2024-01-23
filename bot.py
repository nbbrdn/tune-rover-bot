import os
import logging
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from datetime import datetime

DB_FILE = "database.db"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    exit("Specify TELEGRAM_BOT_TOKEN env variable")


def create_table():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users
        (user_id INTEGER PRIMARY KEY, username TEXT, created_at TIMESTAMP, updated_at TIMESTAMP)
        """
    )
    conn.commit()
    conn.close()


def add_user(user_id, username):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()

    if not existing_user:
        cursor.execute(
            "INSERT INTO users (user_id, username, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, username, current_time, current_time),
        )
        conn.commit()
    else:
        cursor.execute(
            "UPDATE users SET username = ?, updated_at = ? WHERE user_id = ?",
            (username, current_time, user_id),
        )
        conn.commit()
    conn.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username)
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!"
    )


def main():
    create_table()

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
