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

### Scripts
There are a few scripts written to simplify development.
1. `sh scripts/setup.sh` - To be run only on clean environment. Sets up dev environment
2. `sh scripts/build.sh` - Rebuild the containers. Useful when you make changes to the environment or db schema
3. `sh scripts/restart.sh` - Run this whenever you make a code change and see the changes in dev
4. `sh scripts/logs.sh` - Run this to look at the dev logs in real time
5. `sh scripts/nuke.sh` - Removes all relevant containers and images. Used to reset to a clean environment

### DB Schema Changes
If there are changes to the DB schema, add them to `migrations/` with the file name format of `XXX_change_description` where `XXX` is one more than the largest number in the `migrations` directory so far.

## Contributing
[Useful guide to good commit messages](https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html)
> Capitalized, short (50 chars or less) summary
> ...
> Write your commit message in the imperative: "Fix bug" and not "Fixed bug"
or "Fixes bug."  This convention matches up with commit messages generated
by commands like git merge and git revert.
