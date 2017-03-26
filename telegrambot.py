from telegram.ext import Updater, Filters, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.ext.dispatcher import run_async
from database import Transaction
from action_handlers import bill_handler
import json
import constants as const


PRIVATE_CHAT = 'private'


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

        # Handle callback queries
        callback_handler = CallbackQueryHandler(self.handle_all_callback)
        dispatcher.add_handler(callback_handler)

        # Handle all replies
        message_handler = MessageHandler(Filters.all, self.handle_all_msg)
        dispatcher.add_handler(message_handler)

    @run_async
    def start(self, bot, update):
        # TODO: make command list screen
        bot.sendMessage(chat_id=update.message.chat_id, text="Start screen")

    @run_async
    def new_bill(self, bot, update):
        # only allow private message
        try:
            conn = self.db.get_connection()
            handler = self.action_handlers_map[const.TYPE_CREATE_BILL]
            with Transaction(conn) as trans:
                handler.execute(
                    bot,
                    update,
                    trans,
                    action_id=bill_handler.ACTION_NEW_BILL
                )
        except Exception as e:
            print(e)

    @run_async
    def handle_all_msg(self, bot, update):
        try:
            if update.message.chat.type != PRIVATE_CHAT:
                return
            conn = self.db.get_connection()
            msg = update.message
            with Transaction(conn) as trans:
                try:
                    act_type, act_id, subact_id, data = trans.get_session(
                        msg.chat_id,
                        msg.from_user.id,
                    )
                    handler = self.get_action_handler(act_type)
                    return handler.execute(
                        bot, update, trans, act_id, subact_id, data
                    )
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)

    @run_async
    def handle_all_callback(self, bot, update):
        try:
            cbq = update.callback_query
            data = cbq.data

            if data is None:
                return cbq.answer()

            conn = self.db.get_connection()
            with Transaction(conn) as trans:
                trans.get_session(  # create lock to prevent concurrent requests
                    cbq.message.chat_id,
                    cbq.from_user.id
                )
                payload = json.loads(data)
                action_type = payload.get(const.JSON_ACTION_TYPE)
                action_id = payload.get(const.JSON_ACTION_ID)

                if action_type is None:
                    return cbq.answer('nothing')
                handler = self.get_action_handler(action_type)
                return handler.execute(
                    bot, update, trans, action_id, 0, payload
                )
        except Exception as e:
            print(e)

    def get_action_handler(self, action_type):
        if action_type == bill_handler.MODULE_ACTION_TYPE:
            return bill_handler.BillCreationHandler()

        raise Exception("Action type '{}' unknown".format(action_type))


class BillError(Exception):
    pass
