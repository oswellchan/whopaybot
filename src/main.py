from settings import EnvSettings
from database import Database
from telegrambot import TelegramBot
import logging


if __name__ == '__main__':
    try:
      settings = EnvSettings()
      db = Database(
          settings.DB_HOST,
          settings.DB_NAME,
          settings.DB_PORT,
          settings.DB_USER,
          settings.DB_PASS
      )
      bot = TelegramBot(settings.TOKEN,
                        settings.APP_NAME,
                        settings.PORT,
                        db,
                        settings.IS_PROD)
    except Exception as e:
        logging.exception()

    logging_kwargs = {
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'level': logging.INFO
    }

    if not settings.IS_PROD:
        logging_kwargs['filename'] = '/logs/whopay.txt'

    logging.basicConfig(**logging_kwargs)
