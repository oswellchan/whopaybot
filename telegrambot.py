from telegram.ext import Updater, Filters, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.inlinekeyboardbutton import InlineKeyboardButton
from telegram.parsemode import ParseMode
from database import Transaction
import json


PRIVATE_CHAT = 'private'
ACTION_NEWBILL_SET_NAME = 0
ACTION_ADD_ITEM = 1
ACTION_EDIT_ITEM = 2
ACTION_DELETE_ITEM = 3
ACTION_ADD_TAX = 4
ACTION_EDIT_TAX = 5
ACTION_DELETE_TAX = 6
ACTION_CREATE_BILL_DONE = 7
ACTION_GET_NEW_BILL_KEYBOARD = 8
ACTION_GET_MODIFY_ITEM_KEYBOARD = 9
ACTION_GET_MODIFY_TAX_KEYBOARD = 10
ACTION_ADD_ITEM_PRICE = 11
ACTION_ADD_NEW_TAX_AMT = 12

REQUEST_BILL_NAME = "Send me a name for the new bill you want to create."
REQUEST_ITEM_NAME = "Okay. Send me the name of the item."
REQUEST_ITEM_PRICE = "Great! Now send me the price of the item. Leave out the currency and provide only the value (e.g. 8.00 or 8)."
REQUEST_TAX_NAME = "Okay. Send me the name of the tax."
ERROR_INVALID_BILL_NAME = "Sorry, the bill name provided is invalid. Name of the bill can only be 250 characters long. Please try again."
ERROR_INVALID_ITEM_NAME = "Sorry, the item name provided is invalid. Name of the item can only be 250 characters long. Please try again."
ERROR_INVALID_TAX_NAME = "Sorry, the item tax provided is invalid. Name of the tax can only be 250 characters long. Please try again."
ERROR_INVALID_FLOAT_VALUE = "Sorry, the {} provided is invalid. Value provided should be strictly digits only or with an optional decimal point (e.g. 8.00 or 8)."
ERROR_SOMETHING_WENT_WRONG = "Sorry, an error has occurred. Please try again in a few moments."
JSON_ACTION_FIELD = 'a'
JSON_BILL_FIELD = 'b'
EMOJI_MONEY_BAG = '\U0001F4B0'
EMOJI_TAX = '\U0001F4B8'


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

    def start(self, bot, update):
        # TODO: make command list screen
        bot.sendMessage(chat_id=update.message.chat_id, text="Start screen")

    def new_bill(self, bot, update):
        # only allow private message
        try:
            conn = self.db.get_connection()
            with Transaction(conn) as trans:
                self.set_session(
                    update.message.chat_id,
                    update.message.from_user,
                    ACTION_NEWBILL_SET_NAME,
                    trans
                )
            bot.sendMessage(
                chat_id=update.message.chat_id,
                text=REQUEST_BILL_NAME
            )
        except Exception as e:
            print(e)

    def handle_all_msg(self, bot, update):
        try:
            if update.message.chat.type != PRIVATE_CHAT:
                return
            conn = self.db.get_connection()
            msg = update.message
            with Transaction(conn) as trans:
                try:
                    pending_action, data = trans.get_session(
                        msg.chat_id,
                        msg.from_user.id,
                    )
                    if pending_action == ACTION_NEWBILL_SET_NAME:
                        return self.add_bill_name(msg, bot, trans)
                    if pending_action == ACTION_ADD_ITEM:
                        return self.add_item(msg, bot, trans, data)
                    if pending_action == ACTION_ADD_ITEM_PRICE:
                        return self.add_item_price(msg, bot, trans, data)
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)

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
                action = payload.get(JSON_ACTION_FIELD)
                bill_id = payload.get(JSON_BILL_FIELD)

                if action is None:
                    return cbq.answer('nothing')
                if action == ACTION_GET_MODIFY_ITEM_KEYBOARD:
                    cbq.edit_message_reply_markup(
                        reply_markup=self.get_modify_items_keyboard(bill_id)
                    )
                if action == ACTION_GET_MODIFY_TAX_KEYBOARD:
                    cbq.edit_message_reply_markup(
                        reply_markup=self.get_modify_taxes_keyboard(bill_id)
                    )
                if action == ACTION_GET_NEW_BILL_KEYBOARD:
                    cbq.edit_message_reply_markup(
                        reply_markup=self.get_new_bill_keyboard(bill_id)
                    )
                if action == ACTION_ADD_ITEM:
                    self.ask_for_item(bot, cbq, bill_id, trans)
                if action == ACTION_EDIT_ITEM:
                    return cbq.answer('Edit')
                if action == ACTION_CREATE_BILL_DONE:
                    return cbq.answer('Done')
        except Exception as e:
            print(e)

    def set_session(self, chat_id, user, action_type, trans, data=None):
        trans.add_user(
            user.id,
            user.first_name,
            user.last_name,
            user.username
        )
        trans.add_session(chat_id, user.id, action_type, data)

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

            bill_id = trans.add_bill(text, msg.from_user.id)
            trans.reset_session(msg.from_user.id, msg.chat_id)
            return self.send_bill_response(
                bot,
                msg.chat_id,
                msg.from_user.id,
                bill_id,
                trans
            )
        except BillError as e:
            print(e)
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=str(e)
            )
        except Exception as e:
            print(e)
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_SOMETHING_WENT_WRONG
            )

    def get_bill_text(self, bill_id, user_id, trans):
        bill = trans.get_bill_details(bill_id, user_id)
        if bill.get('title') is None or len(bill.get('title')) == 0:
            raise BillError('Bill does not exist')

        title_text = '<b>{}</b>'.format(self.escape_html(bill['title']))

        bill_items = bill.get('items')
        items_text = []
        total = 0
        if bill_items is None or len(bill_items) < 1:
            items_text.append('<i>Currently no items</i>')
        else:
            for i, item in enumerate(bill_items):
                __, title, price = item
                total += price

                items_text.append(str(i + 1) + '. ' + title + '\n' +
                                  EMOJI_MONEY_BAG + "{:.2f}".format(price))

        bill_taxes = bill.get('taxes')
        taxes_text = []
        if bill_taxes is not None:
            for title, tax in bill_taxes:
                total += (tax * total / 100)
                taxes_text.append(EMOJI_TAX + ' ' + title + ': ' + tax + '%')

        text = title_text + '\n\n' + '\n'.join(items_text)
        if len(taxes_text) > 0:
            text += '\n\n' + '\n'.join(taxes_text)

        text += '\n\n' + 'Total: ' + "{:.2f}".format(total)
        return text

    def send_bill_response(self, bot, chat_id, user_id, bill_id, trans):
        bot.sendMessage(
            chat_id=chat_id,
            text=self.get_bill_text(bill_id, user_id, trans),
            parse_mode=ParseMode.HTML,
            reply_markup=self.get_new_bill_keyboard(bill_id)
        )

    def get_new_bill_keyboard(self, bill_id):
        modify_items_btn = InlineKeyboardButton(
            text="Add/Edit Items",
            callback_data=self.get_action_callback_data(
                ACTION_GET_MODIFY_ITEM_KEYBOARD,
                bill_id
            )
        )
        modify_taxes_btn = InlineKeyboardButton(
            text="Add/Edit Taxes",
            callback_data=self.get_action_callback_data(
                ACTION_GET_MODIFY_TAX_KEYBOARD,
                bill_id
            )
        )
        done_btn = InlineKeyboardButton(
            text="Done",
            callback_data=self.get_action_callback_data(
                ACTION_CREATE_BILL_DONE,
                bill_id
            )
        )
        return InlineKeyboardMarkup(
            [[modify_items_btn],
             [modify_taxes_btn],
             [done_btn]]
        )

    def get_modify_items_keyboard(self, bill_id):
        add_item_btn = InlineKeyboardButton(
            text="Add item(s)",
            callback_data=self.get_action_callback_data(
                ACTION_ADD_ITEM,
                bill_id
            )
        )
        edit_item_btn = InlineKeyboardButton(
            text="Edit item",
            callback_data=self.get_action_callback_data(
                ACTION_EDIT_ITEM,
                bill_id
            )
        )
        del_item_btn = InlineKeyboardButton(
            text="Delete item",
            callback_data=self.get_action_callback_data(
                ACTION_DELETE_ITEM,
                bill_id
            )
        )
        back_btn = InlineKeyboardButton(
            text="Back",
            callback_data=self.get_action_callback_data(
                ACTION_GET_NEW_BILL_KEYBOARD,
                bill_id
            )
        )
        return InlineKeyboardMarkup(
            [[add_item_btn],
             [edit_item_btn],
             [del_item_btn],
             [back_btn]]
        )

    def get_modify_taxes_keyboard(self, bill_id):
        add_tax_btn = InlineKeyboardButton(
            text="Add tax",
            callback_data=self.get_action_callback_data(
                ACTION_ADD_TAX,
                bill_id
            )
        )
        edit_tax_btn = InlineKeyboardButton(
            text="Edit tax",
            callback_data=self.get_action_callback_data(
                ACTION_EDIT_TAX,
                bill_id
            )
        )
        del_tax_btn = InlineKeyboardButton(
            text="Delete tax",
            callback_data=self.get_action_callback_data(
                ACTION_DELETE_TAX,
                bill_id
            )
        )
        back_btn = InlineKeyboardButton(
            text="Back",
            callback_data=self.get_action_callback_data(
                ACTION_GET_NEW_BILL_KEYBOARD,
                bill_id
            )
        )
        return InlineKeyboardMarkup(
            [[add_tax_btn],
             [edit_tax_btn],
             [del_tax_btn],
             [back_btn]]
        )

    def ask_for_item(self, bot, cbq, bill_id, trans):
        self.set_session(
            cbq.message.chat_id,
            cbq.from_user,
            ACTION_ADD_ITEM,
            trans,
            data={'bill_id': bill_id}
        )
        cbq.answer()
        bot.sendMessage(chat_id=cbq.message.chat_id, text=REQUEST_ITEM_NAME)

    def add_item(self, msg, bot, trans, data):
        try:
            if Filters.text.filter(msg):
                return self.add_item_name(msg, bot, trans, data)

            if Filters.image.filter(msg):
                return self.add_items_img(msg, bot, trans, data)

            # all other message types invalid
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_ITEM_NAME
            )
        except BillError as e:
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=str(e)
            )
        except Exception as e:
            print(e)
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_SOMETHING_WENT_WRONG
            )

    def add_item_name(self, msg, bot, trans, data):
        text = msg.text
        if (text is None or len(text) < 1 or len(text) > 250):
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_ITEM_NAME
            )

        data['item_name'] = text
        self.set_session(
            msg.chat_id,
            msg.from_user,
            ACTION_ADD_ITEM_PRICE,
            trans,
            data=data
        )
        return bot.sendMessage(
            chat_id=msg.chat_id,
            text=REQUEST_ITEM_PRICE
        )

    def add_item_price(self, msg, bot, trans, data):
        text = msg.text

        try:
            price = float(text)
            bill_id = data.get('bill_id')
            if bill_id is None:
                raise Exception('bill_id is None')
            item_name = data.get('item_name')
            if item_name is None:
                raise Exception('item_name is None')
            trans.add_item(bill_id, item_name, price)
            trans.reset_session(msg.from_user.id, msg.chat_id)
            return self.send_bill_response(
                bot,
                msg.chat_id,
                msg.from_user.id,
                bill_id,
                trans
            )
        except ValueError as e:
            print(e)
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_FLOAT_VALUE.format('item price')
            )
        except Exception as e:
            print(e)

    def add_items_img(self, msg, bot, trans, data):
        pass

    def ask_for_tax_name(self, bot, cbq, bill_id, trans):
        self.set_session(
            cbq.message.chat_id,
            cbq.from_user,
            ACTION_ADD_TAX,
            trans,
            data={'bill_id': bill_id}
        )
        bot.sendMessage(chat_id=cbq.message.chat_id, text=REQUEST_TAX_NAME)

    def get_action_callback_data(self, action, bill_id):
        data = {
            JSON_ACTION_FIELD: action,
            JSON_BILL_FIELD: bill_id
        }
        return json.dumps(data)

    @staticmethod
    def escape_html(s):
        arr = s.split('&')
        escaped = []

        for sgmt in arr:
            a = sgmt.replace('<', '&lt;')
            a = a.replace('>', '&gt;')
            escaped.append(a)

        return '&amp;'.join(escaped)


class BillError(Exception):
    pass
