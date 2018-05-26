# WhoPayBot

Telegram bot for bill splitting.

This is a Telegram bot made using the [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot/) framework that makes splitting a bill between a group of people easier.

## Requirements
1. Docker

## Installing

1. Clone repo to a local directory
2. Get your bot token and app name from [@BotFather](https://telegram.me/botfather)
3. Create .env file in the root project directory with the following params: (Sample provided in .env.example)
```
TOKEN=BOT_TOKEN

# Set IS_PROD to 0 for local and 1 for production
IS_PROD=0
APP_NAME=APP_NAME

# Local env settings
DB_USER=DB_USERNAME
DB_PASS=DB_PASSWORD
```
4. Run `sh scripts/setup.sh`
5. Go to the bot on Telegram and run a few commands e.g. `/newbill`
6. Done

## Development

There are a few scripts written to simplify development.
1. `sh scripts/build.sh` - Rebuild the containers. Useful when you make changes to the environment
2. `sh scripts/restart.sh` - Run this whenever you make a code change and see the changes in dev
3. `sh scripts/logs.sh` - Run this to look at the dev logs in real time
