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

        self.TOKEN = environ.get("TOKEN")
        self.PORT = int(environ.get('PORT', '5000'))
        self.APP_NAME = environ.get("APP_NAME")
        self.IS_PROD = int(environ.get("IS_PROD"))

        if self.IS_PROD:
            url = urlparse.urlparse(environ['DATABASE_URL'])
            self.DB_NAME = url.path[1:]
            self.DB_USER = url.username
            self.DB_PASS = url.password
            self.DB_HOST = url.hostname
            self.DB_PORT = url.port
        else:
            self.DB_USER = environ.get("DB_USER")
            self.DB_NAME = environ.get("DB_NAME")
            self.DB_PORT = environ.get("DB_PORT")
            self.DB_HOST = environ.get("DB_HOST")
            self.DB_PASS = environ.get("DB_PASS")
