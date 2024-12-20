from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import * # Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

# Функция для старта бота
def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Кнопка 1", callback_data='button1')],
        [InlineKeyboardButton("Кнопка 2", callback_data='button2')],
        [InlineKeyboardButton("Кнопка 3", callback_data='button3')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Выберите одну из трех кнопок:', reply_markup=reply_markup)

# Функция для обработки нажатий кнопок
def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    # Сохраняем выбранную кнопку
    context.user_data['selected_button'] = query.data
    query.edit_message_text(text=f"Вы выбрали {query.data}. Пожалуйста, введите ваш API ключ:")

# Функция для обработки текстовых сообщений (ввод API ключа)
def handle_message(update: Update, context: CallbackContext) -> None:
    api_key = update.message.text
    selected_button = context.user_data.get('selected_button')

    if selected_button:
        # Здесь можно добавить основную логику, связанную с API ключом и выбранной кнопкой
        update.message.reply_text(f"Вы ввели API ключ: {api_key}. Выбранная кнопка: {selected_button}.")
        # Очистим данные пользователя после обработки
        context.user_data.clear()
    else:
        update.message.reply_text("Пожалуйста, сначала выберите кнопку.")

def main() -> None:
    # Вставьте свой токен бота
    updater = Updater("7283067661:AAFbhuZ8nkukgoRd6wFDxyTS3rP-yK9tiYQ")

    # Получаем диспетчер для регистрации обработчиков
    dispatcher = updater.dispatcher

    # Регистрация обработчиков команд и сообщений
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Запуск бота
    updater.start_polling()

    # Ожидание завершения работы
    updater.idle()

if __name__ == '__main__':
    main()
