import json
import logging  # Вывод отчетов о работе Бота (Ошибки, добавление и удаление книг м тд ..)
from datetime import datetime  # Дата и время для уведомлений и логов
from pathlib import Path  # для того чтобы найти папку data с данными для программы
import random

from telegram import Update, \
    ReplyKeyboardMarkup  # Подключаем Update - Ловит все действия пользователей в чатах. Второе для создания кнопок
from telegram.ext import (
    Application,  # Основной класс для работы бота. Запускает бота.
    CommandHandler,  # Ловит команды по типу /start
    ContextTypes,  # Для определения типа сообщения текст/команда/фото/видео/ответ
    MessageHandler,  # Если не команда текст
    filters,
)

from config import BOT_TOKEN

# Настройка логирования (вывод отчета в консоль)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)  # Запуск логирования

# Пути к данным
DATA_DIR = Path("data")
BOOKS_FILE = DATA_DIR / "books.json"
PROGRESS_FILE = DATA_DIR / "user_progress.json"

DATA_DIR.mkdir(exist_ok=True)  # Если такой паки нет => создать ее


def load_books():
    if BOOKS_FILE.exists():  # Если файл books.json есть то открываем и считываем
        with open(BOOKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(data):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# Загрузка данных для бота
books = load_books()
user_progress = load_progress()

# Клавиатура
MAIN_KEYBOARD = [
    ["📖 Получить отрывок", "📚 Рекомендовать книгу"],
    ["✅ Отметить прочитанное", "📖 Мои прочитанные"],
    ["📘 Обзоры книг", "⏰ Напоминание о чтении"]
]

# Создаешь кнопки используя класс ReplyKeyboardMarkup
reply_markup = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True, one_time_keyboard=False)


# /start
async def start(update: Update,
                context: ContextTypes.DEFAULT_TYPE):  # context помогает нам хранить информацию о боте и пользователе + помогает Pycharm Давать подсказет
    await update.message.reply_text(  # Отправка сообщения пользователю
        "📚 Добро пожаловать в бота для чтения!\nВыберите действие:",
        reply_markup=reply_markup  # Прикрепляем кнопки к сообщению
    )


# Получить отрывок
async def handle_excerpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)  # Получаем Id Пользователя ТГ
    today = datetime.now().strftime("%Y-%m-%d")  # Время последнего обращения

    if not books:
        await update.message.reply_text("Библиотека пуста 😢", reply_markup=reply_markup)
        return

    book = random.choice(books)  # Рандомно выбираем книгу из списка
    if user_id not in user_progress:
        user_progress[user_id] = {"read_books": [], "last_excerpt_date": ""}
    user_progress[user_id]["last_excerpt_date"] = today  # Обновляем время последнего обращение
    save_progress(user_progress)  # Сохраняем нового пользователя в файл

    await update.message.reply_text(
        f"📖 *{book['title']}* — _{book['author']}_\n\n{book['excerpt']}",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


# Рекомендация
async def handle_recommend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    read_ids = user_progress.get(user_id, {}).get("read_books",
                                                  [])  # Получаем прочитанные книги, по id пользователя. Если ничего не ситает то задаем пустой словарь с пустыми книгами
    unread_books = [b for b in books if b["id"] not in read_ids]  # Получаем непрочитанные книги

    if not unread_books:
        await update.message.reply_text("Вы прочитали всё! 🎉", reply_markup=reply_markup)
        return

    book = random.choice(unread_books)
    await update.message.reply_text(
        f"📚 Рекомендуем:\n\n*{book['title']}* — _{book['author']}_\nЖанр: {book['genre']}",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


# Отметить прочитанное
async def handle_read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not books:
        await update.message.reply_text("Нет книг для отметки.", reply_markup=reply_markup)
        return

    book_list = "\n".join(
        [f"{b['id']}. {b['title']} — {b['author']}" for b in books])  # Генерируем список книг с номером(id)
    await update.message.reply_text(
        f"Введите ID книги, которую хотите отметить как прочитанную:\n\n{book_list}",
        reply_markup=reply_markup
    )
    context.user_data["awaiting_book_id"] = True  # Говорим боту, чтоб ожидаем ввод id книги, чтобы потом обработать


# Мои прочитанные книги
async def handle_my_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    read_ids = user_progress.get(user_id, {}).get("read_books", [])  # Получаем просчитанные книги (id)

    if not read_ids:
        await update.message.reply_text(
            "Вы ещё не прочитали ни одной книги. Начните с кнопки «Получить отрывок»!",
            reply_markup=reply_markup
        )
        return

    read_books = [book for book in books if
                  book["id"] in read_ids]  # Получаем инфу о прочитанных книгах(Название, автор)
    if not read_books:
        await update.message.reply_text("Ваши прочитанные книги не найдены в библиотеке.", reply_markup=reply_markup)
        return

    response = "📖 Ваши прочитанные книги:\n\n"
    for book in read_books:
        response += f"• *{book['title']}* — _{book['author']}_\n"

    await update.message.reply_text(response, parse_mode="Markdown", reply_markup=reply_markup)


# Обзоры
async def handle_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not books:
        await update.message.reply_text("Нет книг для обзора.", reply_markup=reply_markup)
        return
    response = "📘 Обзоры:\n\n"
    for book in books:
        response += f"*{book['title']}* — {book['review']}\n\n"
    await update.message.reply_text(response, parse_mode="Markdown", reply_markup=reply_markup)


# Напоминание
async def handle_remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.job_queue is None:  # Проверяем доступность уведомлений
        await update.message.reply_text(
            "⚠️ Напоминания недоступны.",
            reply_markup=reply_markup
        )
        return

    user_id = update.effective_user.id
    current_jobs = context.job_queue.get_jobs_by_name(str(user_id))
    for job in current_jobs:
        job.schedule_removal()

    context.job_queue.run_once(
        send_reminder,
        when=5,  # 1 час
        chat_id=user_id,
        name=str(user_id)
    )
    await update.message.reply_text("⏰ Напоминание установлено на 1 час.", reply_markup=reply_markup)


async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job  # Получаем задаение об отправке сообщения
    await context.bot.send_message(
        chat_id=job.chat_id,  # Говорим боту кому отправить напоминание
        text="📖 Не забудьте почитать сегодня! Нажмите «Получить отрывок» в меню.",
        reply_markup=reply_markup
    )


# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    # Прикрепляем к тексту сответствующиие команды
    if text == "📖 Получить отрывок":
        return await handle_excerpt(update, context)
    elif text == "📚 Рекомендовать книгу":
        return await handle_recommend(update, context)
    elif text == "✅ Отметить прочитанное":
        return await handle_read(update, context)
    elif text == "📖 Мои прочитанные":
        return await handle_my_books(update, context)
    elif text == "📘 Обзоры книг":
        return await handle_reviews(update, context)
    elif text == "⏰ Напоминание о чтении":
        return await handle_remind(update, context)

    # Обработка ввода ID книги
    if context.user_data.get("awaiting_book_id"):
        try:
            book_id = int(text)
            today = datetime.now().strftime("%Y-%m-%d")
            book = next((b for b in books if b["id"] == book_id),
                        None)  # Генератор берет книгу а если не найдет вернет None
            if not book:
                await update.message.reply_text("Книга с таким ID не найдена.", reply_markup=reply_markup)
                return

            user_id = str(update.effective_user.id)
            if user_id not in user_progress:
                user_progress[user_id] = {"read_books": [], "last_excerpt_date": f"{today}"}
            if book_id not in user_progress[user_id]["read_books"]:
                user_progress[user_id]["read_books"].append(book_id)
                save_progress(user_progress)
                await update.message.reply_text(f"✅ «{book['title']}» отмечена как прочитанная!",
                                                reply_markup=reply_markup)
            else:
                await update.message.reply_text("Эта книга уже в списке прочитанных.", reply_markup=reply_markup)
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите корректный ID (целое число).",
                                            reply_markup=reply_markup)
        finally:
            context.user_data[
                "awaiting_book_id"] = False  # Не зависимо от тог получлось ли отметить говорим что больше не ждем ввода от usera
        return

    # Неизвестный ввод
    await update.message.reply_text("Пожалуйста, используйте кнопки меню.", reply_markup=reply_markup)


# Основная функция
if __name__ == "__main__":
    application = Application.builder().token(BOT_TOKEN).build()  # Инициализируем Бота (Создаем)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен с кнопками и функцией 'Мои прочитанные'...")
    application.run_polling()  # Запускаем Бота