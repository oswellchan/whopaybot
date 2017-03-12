from telegram.ext import Updater, Filters, CommandHandler, MessageHandler
from database import Transaction
import traceback


ACTION_NEWBILL_SET_NAME = 0
TEXT_REQUEST_BILL_NAME = "Send me a name for the new you want to create."


class TelegramBot:
    def __init__(self, token, db):
        self.db = db
        self.updater = Updater(token=token)
        self.attach_handlers(self.updater.dispatcher)

    def start_bot(self):
        self.updater.start_polling()

    def attach_handlers(self, dispatcher):
        start_handler = CommandHandler('start', self.start)
        dispatcher.add_handler(start_handler)
        newbill_handler = CommandHandler('newbill', self.new_bill)
        dispatcher.add_handler(newbill_handler)
        message_handler = MessageHandler(Filters.all, self.handle_all)
        dispatcher.add_handler(message_handler)

    def start(self, bot, update):
        # TODO: make command list screen
        bot.sendMessage(chat_id=update.message.chat_id, text="Start screen")
        pass

    def new_bill(self, bot, update):
        # only allow private message
        try:
            conn = self.db.get_connection()
            with Transaction(conn) as trans:
                self.set_session(
                    update.message,
                    ACTION_NEWBILL_SET_NAME,
                    trans
                )
            bot.sendMessage(
                chat_id=update.message.chat_id,
                text=TEXT_REQUEST_BILL_NAME
            )
        except Exception as e:
            traceback.print_trace()

    def handle_all(self, bot, update):
        try:
            if update.message.chat.type != 'private':
                return

            conn = self.db.get_connection()
            msg = update.message
            with Transaction(conn) as trans:
                try:
                    pending_action = trans.get_pending_action(
                        msg.from_user.id,
                        msg.chat_id
                    )
                    if pending_action == ACTION_NEWBILL_SET_NAME:
                        return self.add_bill_name(msg)
                except Exception as e:
                    print(e)
                    traceback.print_trace()
        except:
            traceback.print_trace()

    def set_session(self, message, action_type, trans):
        user = message.from_user
        trans.add_user(
            user.id,
            user.first_name,
            user.last_name,
            user.username
        )
        trans.add_session(message.chat_id, user.id, action_type)

    def add_bill_name(self, message):
        print(Filters.text.filter(message))
        print(Filters.audio.filter(message))
        print(Filters.sticker.filter(message))
        print(Filters.photo.filter(message))
