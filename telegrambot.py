from telegram.ext import Updater, Filters, CommandHandler, MessageHandler
from database import Transaction
import traceback


PRIVATE_CHAT = 'private'
ACTION_NEWBILL_SET_NAME = 0
REQUEST_BILL_NAME = "Send me a name for the new bill you want to create."
ERROR_INVALID_BILL_NAME = "Sorry, the bill name provided is invalid. Name of the bill can only be 250 characters long."
ERROR_SOMETHING_WENT_WRONG = "Sorry, an error has occurred. Please try again in a few moments."


class TelegramBot:
    def __init__(self, token, db):
        self.db = db
        self.updater = Updater(token=token)
        self.init_handlers(self.updater.dispatcher)

    def start_bot(self):
        self.updater.start_polling()

    def init_handlers(self, dispatcher):
        # Command handlers
        start_handler = CommandHandler('start', self.start)
        dispatcher.add_handler(start_handler)
        newbill_handler = CommandHandler('newbill', self.new_bill)
        dispatcher.add_handler(newbill_handler)

        # Handle all replies
        message_handler = MessageHandler(Filters.all, self.handle_all)
        dispatcher.add_handler(message_handler)

    def start(self, bot, update):
        # TODO: make command list screen
        bot.sendMessage(chat_id=update.message.chat_id, text="Start screen")

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
                text=REQUEST_BILL_NAME
            )
        except Exception as e:
            traceback.print_trace()

    def handle_all(self, bot, update):
        try:
            if update.message.chat.type != PRIVATE_CHAT:
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
                        return self.add_bill_name(msg, bot, trans)
                except Exception as e:
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

    def add_bill_name(self, msg, bot, trans):
        try:
            if not Filters.text.filter(msg):
                return bot.sendMessage(
                    chat_id=msg.chat_id,
                    text=ERROR_INVALID_BILL_NAME
                )

            text = msg.text
            if (text is None or len(text) < 1 or len(text) > 250):
                return bot.sendMessage(
                    chat_id=msg.chat_id,
                    text=ERROR_INVALID_BILL_NAME
                )

            bill_id = trans.create_new_bill(text, msg.from_user.id)
            trans.reset_action(msg.from_user.id, msg.chat_id)
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=text,
                reply_markup=self.get_new_bill_keyboard(bill_id)
            )
        except Exception as e:
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_SOMETHING_WENT_WRONG
            )

    def get_new_bill_keyboard(self, bill_id):
        pass
