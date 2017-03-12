from os import path, environ
from dotenv import load_dotenv


class EnvSettings:
    def __init__(self):
        dotenv_path = path.join(path.dirname(__file__), '.env')
        load_dotenv(dotenv_path)
        self.TOKEN = environ.get("TOKEN")
        self.DB_USER = environ.get("DB_USER")
        self.DB_NAME = environ.get("DB_NAME")
        self.DB_PORT = environ.get("DB_PORT")
        self.DB_HOST = environ.get("DB_HOST")
        self.DB_PASS = environ.get("DB_PASS")
