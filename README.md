# WhoPayBot

Telegram bot for bill splitting.

This is a Telegram bot made using the [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot/) framework that makes splitting a bill between a group of people easier.

## Requirements
1. Python 3.6+
2. PostgreSQL 9.6+

## Installing

1. Clone repo to a local directory
2. Install virtualenv:

        $ pip install virtualenv

3. Setup virtualenv

        $ virtualenv venv

    Or if you have multiple python installations

       $ virtualenv -p /usr/bin/python3.6 venv

4. Activate virtualenv

        $ source venv/bin/activate

5. Install dependencies

        $ pip install -r requirements.txt

6. Create PostgreSQL DB and run `schema.sql` to create the tables.
7. Create .env file with necessary params

        TOKEN=BOT_TOKEN

        # Set IS_PROD to 0 for local and 1 for production
        IS_PROD=0
        APP_NAME=APP_NAME

        # Local env settings
        DB_USER=DB_USERNAME
        DB_NAME=DB_NAME
        DB_HOST=DB_HOST
        DB_PASS=DB_PASSWORD
        DB_PORT=DB_PORT

## Usage

Run the project bot using

    $ python main.py
