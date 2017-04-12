from telegram.ext import Updater, Filters
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler
from telegram.ext.dispatcher import run_async
from database import Transaction
from action_handlers import create_bill_handler, manage_bill_handler, share_bill_handler
import json
import constants as const
import logging
import datetime

PRIVATE_CHAT = 'private'


class TelegramBot:
    def __init__(self, token, app_name, port, db, is_prod):
        self.db = db
        self.updater = Updater(token=token)
        self.init_handlers(self.updater.dispatcher)

        if is_prod:
            self.updater.start_webhook(listen="0.0.0.0",
                                       port=port,
                                       url_path=token)
            self.updater.bot.setWebhook("https://{}.herokuapp.com/{}".format(
                app_name, token)
            )
            self.updater.idle()
        else:
            self.updater.start_polling()

    def init_handlers(self, dispatcher):
        # Command handlers
        start_handler = CommandHandler('start', self.start, pass_args=True)
        dispatcher.add_handler(start_handler)
        newbill_handler = CommandHandler('newbill', self.new_bill)
        dispatcher.add_handler(newbill_handler)
        done_handler = CommandHandler('done', self.done)
        dispatcher.add_handler(done_handler)

        # Handle callback queries
        callback_handler = CallbackQueryHandler(self.handle_all_callback)
        dispatcher.add_handler(callback_handler)

        # Handle inline queries
        inline_handler = InlineQueryHandler(self.handle_inline)
        dispatcher.add_handler(inline_handler)

        # Handle all replies
        message_handler = MessageHandler(Filters.all, self.handle_all_msg)
        dispatcher.add_handler(message_handler)

    @run_async
    def start(self, bot, update, args):
        # TODO: make command list screen
        if args is not None and len(args) == 1:
            # send the thing
            pass
        bot.sendMessage(chat_id=update.message.chat_id, text="Start screen")

    @run_async
    def new_bill(self, bot, update):
        # only allow private message
        try:
            conn = self.db.get_connection()
            handler = self.get_action_handler(const.TYPE_CREATE_BILL)
            with Transaction(conn) as trans:
                handler.execute(
                    bot,
                    update,
                    trans,
                    action_id=create_bill_handler.ACTION_NEW_BILL
                )
        except Exception as e:
            logging.exception('new_bill')

    @run_async
    def done(self, bot, update):
        try:
            conn = self.db.get_connection()
            with Transaction(conn) as trans:
                msg = update.message
                user = msg.from_user
                trans.add_user(
                    user.id,
                    user.first_name,
                    user.last_name,
                    user.username
                )
                act_type, act_id, subact_id, data = trans.get_session(
                    msg.chat_id,
                    msg.from_user.id,
                )
                handler = self.get_action_handler(act_type)
                return handler.execute_done(
                    bot, update, trans, act_id, subact_id, data
                )
        except Exception as e:
            logging.exception('done')

    @run_async
    def handle_all_msg(self, bot, update):
        try:
            if update.message.chat.type != PRIVATE_CHAT:
                return
            conn = self.db.get_connection()
            msg = update.message
            with Transaction(conn) as trans:
                try:
                    user = update.message.from_user
                    trans.add_user(
                        user.id,
                        user.first_name,
                        user.last_name,
                        user.username
                    )
                    act_type, act_id, subact_id, data = trans.get_session(
                        msg.chat_id,
                        msg.from_user.id,
                    )
                    handler = self.get_action_handler(act_type)
                    return handler.execute(
                        bot, update, trans, act_id, subact_id, data
                    )
                except Exception as e:
                    logging.exception('inner handle_all_msg')
        except Exception as e:
            logging.exception('handle_all_msg')

    @run_async
    def handle_all_callback(self, bot, update):
        print("1. Received: " + str(datetime.datetime.now().time()))
        try:
            cbq = update.callback_query
            data = cbq.data

            if data is None:
                return cbq.answer()

            conn = self.db.get_connection()
            with Transaction(conn) as trans:
                user = update.callback_query.from_user
                trans.add_user(
                    user.id,
                    user.first_name,
                    user.last_name,
                    user.username
                )
                payload = json.loads(data)
                action_type = payload.get(const.JSON_ACTION_TYPE)
                action_id = payload.get(const.JSON_ACTION_ID)

                if action_type is None:
                    return cbq.answer('nothing')
                handler = self.get_action_handler(action_type)
                print("2. Dispatched: " + str(datetime.datetime.now().time()))
                return handler.execute(
                    bot, update, trans, action_id, 0, payload
                )
        except Exception as e:
            logging.exception('handle_all_callback')

    @run_async
    def handle_inline(self, bot, update):
        try:
            conn = self.db.get_connection()
            handler = self.get_action_handler(const.TYPE_SHARE_BILL)
            with Transaction(conn) as trans:
                user = update.inline_query.from_user
                trans.add_user(
                    user.id,
                    user.first_name,
                    user.last_name,
                    user.username
                )
                handler.execute(
                    bot,
                    update,
                    trans,
                    action_id=share_bill_handler.ACTION_FIND_BILLS
                )
        except Exception as e:
            logging.exception('handle_inline')

    def get_action_handler(self, action_type):
        if action_type == create_bill_handler.MODULE_ACTION_TYPE:
            return create_bill_handler.BillCreationHandler()
        if action_type == manage_bill_handler.MODULE_ACTION_TYPE:
            return manage_bill_handler.BillManagementHandler()
        if action_type == share_bill_handler.MODULE_ACTION_TYPE:
            return share_bill_handler.BillShareHandler()

        raise Exception("Action type '{}' unknown".format(action_type))


class BillError(Exception):
    pass
