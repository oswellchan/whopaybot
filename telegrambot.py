from telegram.ext import Updater, CommandHandler


class TelegramBot():
    def __init__(self, token, db):
        self.db = db
        self.updater = Updater(token=token)
        self.attach_handlers(self.updater.dispatcher)

    def attach_handlers(self, dispatcher):
        start_handler = CommandHandler('start', self.start)
        dispatcher.add_handler(start_handler)

    def start(self, bot, update):
        bot.sendMessage(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")

    def start_bot(self):
        self.updater.start_polling()
