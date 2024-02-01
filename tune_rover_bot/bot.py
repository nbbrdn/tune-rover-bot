import os
import logging
import sqlite3
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackContext,
)
from datetime import datetime

DB_FILE = "database.db"

ALBUM_TITLE, ALBUM_ARTIST, ALBUM_LABEL, ALBUM_YEAR, ALBUM_COVER = range(5)

USER_ROLE = {"USER": 0, "ADMIN": 1}

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
            created_at TIMESTAMP
        );
        """
    )

    conn.commit()
    conn.close()


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
        (title, artist, label, release_year, cover_path, current_time),
    )

    conn.commit()
    conn.close()


def get_random_album():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM albums ORDER BY RANDOM() LIMIT 1")
    random_album = cursor.fetchone()

    conn.close()

    return random_album


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


def get_user_role(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Получаем роль пользователя
    cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
    role = cursor.fetchone()

    conn.close()

    return role[0] if role else 0


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    button = [[KeyboardButton("Удиви меня")]]
    add_user(user.id, user.username)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I'm a bot, please talk to me!",
        reply_markup=ReplyKeyboardMarkup(button, resize_keyboard=True),
    )


async def random_album(update: Update, context: ContextTypes.DEFAULT_TYPE):
    album = get_random_album()

    if album:
        id, title, artist, label, release_year, cover_path, created_at = album
        cover_path = os.path.join(os.getcwd(), "covers", cover_path)
        await update.message.reply_photo(
            open(cover_path, "rb"),
            caption=f"Случайный альбом: {title} - {artist}, год выпуска: {release_year}, добавлен: {created_at}",
        )
    else:
        await update.message.reply_text("Database doesn't has any album.")


async def add_album_start(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    user_role = get_user_role(user_id)
    if user_role == USER_ROLE["ADMIN"]:
        await update.message.reply_text(
            "Давайте добавим новый альбом. Введите название альбома:"
        )
        return ALBUM_TITLE
    else:
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return ConversationHandler.END


async def add_album_title(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    user_data["title"] = update.message.text

    await update.message.reply_text(
        f"Отлично! Теперь введите исполнителя альбома {user_data['title']}"
    )
    return ALBUM_ARTIST


async def add_album_artist(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    user_data["artist"] = update.message.text

    await update.message.reply_text(
        f'Хорошо! Теперь введите название лейбла, выпустившего альбом {user_data["title"]} от {user_data["artist"]}:'
    )
    return ALBUM_LABEL


async def add_album_label(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    user_data["label"] = update.message.text

    await update.message.reply_text(
        f'Хорошо! Теперь введите год выпуска альбома {user_data["title"]} от {user_data["artist"]}:'
    )
    return ALBUM_YEAR


async def add_album_year(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data

    try:
        user_data["year"] = int(update.message.text)
    except ValueError:
        update.message.reply_text("Введите корректный год в числовом формате.")
        return ALBUM_YEAR

    await update.message.reply_text(
        f'Отлично! Теперь отправьте обложку альбома {user_data["title"]} от {user_data["artist"]} (ответьте на это сообщение изображением).'
    )
    return ALBUM_COVER


async def add_album_cover(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data

    # Проверяем, пришло ли изображение
    if update.message.photo:
        # Получаем информацию о фотографии с максимальным разрешением
        photo_file = await update.message.photo[-1].get_file()

        # Получаем путь для сохранения файла
        cover_path = f'cover_{user_data["title"].replace(" ", "_")}_{user_data["artist"].replace(" ", "_")}_{user_data["year"]}.jpg'
        cover_path_full = os.path.join(os.getcwd(), "covers", cover_path)

        # Скачиваем файл и сохраняем его
        await photo_file.download_to_drive(cover_path_full)
        logger.info("Photo of %s: %s", user_data["title"], cover_path_full)

        # Добавляем альбом в базу данных
        add_album(
            user_data["title"],
            user_data["artist"],
            user_data["label"],
            user_data["year"],
            cover_path,
        )

        # Очищаем данные пользователя
        user_data.clear()

        await update.message.reply_text("Альбом успешно добавлен в базу данных!")
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Ответьте на это сообщение изображением (обложкой альбома)."
        )
        return ALBUM_COVER


async def add_album_cancel(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    user_data.clear()

    await update.message.reply_text("Добавление альбома отменено.")
    return ConversationHandler.END


async def surprise_me(update: Update, context: CallbackContext) -> None:
    album = get_random_album()

    await update.message.delete()

    if album:
        id, title, artist, label, release_year, cover_path, created_at = album
        cover_path = os.path.join(os.getcwd(), "covers", cover_path)
        await update.message.reply_photo(
            open(cover_path, "rb"),
            caption=f"Случайный альбом: {title} - {artist}, год выпуска: {release_year}, добавлен: {created_at}",
        )
    else:
        await update.message.reply_text("Database doesn't has any album.")


def main():
    create_table()

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)

    random_album_handler = CommandHandler("random", random_album)
    application.add_handler(random_album_handler)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_album_start)],
        states={
            ALBUM_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_album_title)
            ],
            ALBUM_ARTIST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_album_artist)
            ],
            ALBUM_LABEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_album_label)
            ],
            ALBUM_YEAR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_album_year)
            ],
            ALBUM_COVER: [
                MessageHandler(filters.PHOTO & ~filters.COMMAND, add_album_cover)
            ],
        },
        fallbacks=[CommandHandler("cancel", add_album_cancel)],
    )
    application.add_handler(conv_handler)

    application.add_handler(MessageHandler(filters.Text(["Удиви меня"]), surprise_me))

    application.run_polling()


if __name__ == "__main__":
    main()
