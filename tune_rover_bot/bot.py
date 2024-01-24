import os
import logging
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackContext,
)
import db


(
    ALBUM_TITLE,
    ALBUM_ARTIST,
    ALBUM_LABEL,
    ALBUM_YEAR,
    ALBUM_COVER,
    ALBUM_ITUNES,
    ALBUM_YMUSIC,
) = range(7)

USER_ROLE = {"USER": 0, "ADMIN": 1}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    exit("Specify TELEGRAM_BOT_TOKEN env variable")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    button = [[KeyboardButton("Удиви меня")]]
    db.add_user(user.id, user.username)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет! Я - твой проводник в мире музыки! Пристегнись - нас ждут удивительные открытия в мире музыки!",
        reply_markup=ReplyKeyboardMarkup(button, resize_keyboard=True),
    )


async def random_album(update: Update, context: ContextTypes.DEFAULT_TYPE):
    album = db.get_random_album()

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
    user_role = db.get_user_role(user_id)
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

    album = db.find_album(user_data["title"], user_data["artist"])
    if album:
        user_data.clear()
        await update.message.reply_text(
            "Похоже, этот альбом уже есть в базе!\nДобавление альбома отменено."
        )
        return ConversationHandler.END
    else:
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
        user_data["cover_path"] = cover_path
        await update.message.reply_text(
            'Обложка альбома успешно добавлена! Теперь укажите ссылку на альбом в iTunes (если есть), или введите "нет":'
        )
        return ALBUM_ITUNES
    else:
        await update.message.reply_text(
            "Пожалуйста, отправьте фотографию в формате JPEG или PNG."
        )
        return ALBUM_COVER


async def add_album_itunes(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    user_data["itunes_link"] = (
        update.message.text if update.message.text.lower() != "нет" else None
    )
    await update.message.reply_text(
        'Отлично! Теперь укажите ссылку на альбом в Яндекс.Музыке (если есть), или введите "нет":'
    )
    return ALBUM_YMUSIC


async def add_album_ymusic(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    user_data["ymusic_link"] = (
        update.message.text if update.message.text.lower() != "нет" else None
    )
    db.add_album(
        user_data["title"],
        user_data["artist"],
        user_data["label"],
        user_data["year"],
        user_data["cover_path"],
        user_data["itunes_link"],
        user_data["ymusic_link"],
    )
    await update.message.reply_text("Альбом успешно добавлен в базу данных!")
    context.user_data.clear()
    return ConversationHandler.END


async def add_album_cancel(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    user_data.clear()

    await update.message.reply_text("Добавление альбома отменено.")
    return ConversationHandler.END


async def surprise_me(update: Update, context: CallbackContext) -> None:
    album = db.get_random_album()

    await update.message.delete()

    if album:
        title, artist, label, release_year, cover_path, itunes, ymusic = album
        cover_path = os.path.join(os.getcwd(), "covers", cover_path)

        keyboard = [[]]

        if itunes:
            keyboard[0].append(
                InlineKeyboardButton(
                    "Apple Music",
                    url=itunes,
                )
            )

        if ymusic:
            keyboard[0].append(
                InlineKeyboardButton(
                    "Яндекс Музыка",
                    url=ymusic,
                )
            )

        if keyboard:
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            reply_markup = None

        await update.message.reply_photo(
            open(cover_path, "rb"),
            caption=f"{title} - {artist} ({label}, {release_year})",
            reply_markup=reply_markup,
        )
    else:
        await update.message.reply_text("Database doesn't has any album.")


def main():
    db.create_table()

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
            ALBUM_ITUNES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_album_itunes)
            ],
            ALBUM_YMUSIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_album_ymusic)
            ],
        },
        fallbacks=[CommandHandler("cancel", add_album_cancel)],
    )
    application.add_handler(conv_handler)

    application.add_handler(MessageHandler(filters.Text(["Удиви меня"]), surprise_me))

    application.run_polling()


if __name__ == "__main__":
    main()
