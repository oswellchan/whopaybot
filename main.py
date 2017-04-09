from settings import EnvSettings
from database import Database
from telegrambot import TelegramBot


if __name__ == '__main__':
    print('hello world')
    print('next')
    settings = EnvSettings()
    db = Database(
        settings.DB_HOST,
        settings.DB_NAME,
        settings.DB_PORT,
        settings.DB_USER,
        settings.DB_PASS
    )
    print(settings.TOKEN)
    print(settings.APP_NAME)
    print(settings.PORT)
    print(settings.IS_PROD)
    bot = TelegramBot(settings.TOKEN,
                      settings.APP_NAME,
                      settings.PORT,
                      db,
                      settings.IS_PROD)
