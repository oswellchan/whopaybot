from settings import EnvSettings
from database import Database
from telegrambot import TelegramBot


if __name__ == '__main__':
    settings = EnvSettings()
    db = Database(
        settings.DB_HOST,
        settings.DB_NAME,
        settings.DB_PORT,
        settings.DB_USER,
        settings.DB_PASS
    )
    bot = TelegramBot(settings.TOKEN, db)
    bot.start_bot()

    # updater = Updater(token=settings.TOKEN)
    # dispatcher = updater.dispatcher
    # start_handler = CommandHandler('start', start)
    # dispatcher.add_handler(start_handler)

    # updater.start_polling()
