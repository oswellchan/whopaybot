from os import path, environ
from dotenv import load_dotenv
import urllib.parse as urlparse


class EnvSettings:
    def __init__(self):
        try:
            dotenv_path = path.join(path.dirname(__file__), '.env')
            load_dotenv(dotenv_path)
        except Exception as e:
            pass

        EnvSettings.TOKEN = environ.get("TOKEN")
        EnvSettings.PORT = int(environ.get('PORT', '5000'))
        EnvSettings.APP_NAME = environ.get("APP_NAME")
        EnvSettings.IS_PROD = int(environ.get("IS_PROD"))

        if EnvSettings.IS_PROD:
            url = urlparse.urlparse(environ['DATABASE_URL'])
            EnvSettings.DB_NAME = url.path[1:]
            EnvSettings.DB_USER = url.username
            EnvSettings.DB_PASS = url.password
            EnvSettings.DB_HOST = url.hostname
            EnvSettings.DB_PORT = url.port
        else:
            EnvSettings.DB_USER = environ.get("DB_USER")
            EnvSettings.DB_NAME = environ.get("DB_NAME")
            EnvSettings.DB_PORT = environ.get("DB_PORT")
            EnvSettings.DB_HOST = environ.get("DB_HOST")
            EnvSettings.DB_PASS = environ.get("DB_PASS")
