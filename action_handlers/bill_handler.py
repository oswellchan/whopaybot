from telegram.ext import Filters
from telegram.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.inlinekeyboardbutton import InlineKeyboardButton
from telegram.parsemode import ParseMode

from action_handlers.action_handler import ActionHandler, Action
import constants as const
import utils

MODULE_ACTION_TYPE = const.TYPE_CREATE_BILL

ACTION_NEW_BILL = 0
ACTION_GET_MODIFY_ITEMS_KB = 1
ACTION_GET_MODIFY_TAXES_KB = 2
ACTION_CREATE_BILL_DONE = 3
ACTION_ADD_ITEMS = 4
ACTION_GET_EDIT_ITEM_KB = 5
ACTION_GET_DELETE_ITEM_KB = 6
ACTION_ADD_TAX = 7
ACTION_EDIT_TAX = 8
ACTION_DELETE_TAX = 9
ACTION_GET_NEW_BILL_KB = 10
ACTION_GET_EDIT_SPECIFIC_ITEM_KB = 11
ACTION_EDIT_SPECIFIC_ITEM_NAME = 14
ACTION_EDIT_SPECIFIC_ITEM_PRICE = 15
ACTION_DELETE_SPECIFIC_ITEM = 16

REQUEST_BILL_NAME = "Send me a name for the new bill you want to create."
REQUEST_ITEM_NAME = "Okay. Send me the name of the item."
REQUEST_ITEM_PRICE = "Great! Now send me the price of the item. Leave out the currency and provide only the value (e.g. 8.00 or 8)."
REQUEST_EDIT_ITEM_NAME = "Send me the new name of the item."
REQUEST_EDIT_ITEM_PRICE = "Send me the new price of the item. Leave out the currency and provide only the value (e.g. 8.00 or 8)."

ERROR_INVALID_BILL_NAME = "Sorry, the bill name provided is invalid. Name of the bill can only be 250 characters long. Please try again."
ERROR_SOMETHING_WENT_WRONG = "Sorry, an error has occurred. Please try again in a few moments."
ERROR_INVALID_ITEM_NAME = "Sorry, the item name provided is invalid. Name of the item can only be 250 characters long. Please try again."
ERROR_INVALID_FLOAT_VALUE = "Sorry, the {} provided is invalid. Value provided should be strictly digits only or with an optional decimal point (e.g. 8.00 or 8)."


class BillCreationHandler(ActionHandler):
    """docstring for NewBillHandler"""

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE)

    def execute(self, bot, update, trans, action_id,
                subaction_id=0, data=None):
        if action_id == ACTION_NEW_BILL:
            return CreateNewBill(
                MODULE_ACTION_TYPE,
                ACTION_NEW_BILL
            ).execute(bot, update, trans, subaction_id, data)
        if action_id == ACTION_GET_NEW_BILL_KB:
            return DisplayNewBillKB(
                MODULE_ACTION_TYPE,
                ACTION_GET_NEW_BILL_KB
            ).execute(bot, update, trans, subaction_id, data)
        if action_id == ACTION_GET_MODIFY_ITEMS_KB:
            return DisplayModifyItemsKB(
                MODULE_ACTION_TYPE,
                ACTION_GET_MODIFY_ITEMS_KB
            ).execute(bot, update, trans, subaction_id, data)
        if action_id == ACTION_GET_MODIFY_TAXES_KB:
            return DisplayModifyTaxesKB(
                MODULE_ACTION_TYPE,
                ACTION_GET_MODIFY_TAXES_KB
            ).execute(bot, update, trans, subaction_id, data)
        if action_id == ACTION_GET_EDIT_ITEM_KB:
            return DisplayEditItemsKB(
                MODULE_ACTION_TYPE,
                ACTION_GET_EDIT_SPECIFIC_ITEM_KB
            ).execute(bot, update, trans, subaction_id, data)
        if action_id == ACTION_GET_EDIT_SPECIFIC_ITEM_KB:
            return DisplayEditSpecificItemKB(
                MODULE_ACTION_TYPE,
                ACTION_GET_EDIT_SPECIFIC_ITEM_KB
            ).execute(bot, update, trans, subaction_id, data)
        if action_id == ACTION_ADD_ITEMS:
            return AddItems(
                MODULE_ACTION_TYPE,
                ACTION_ADD_ITEMS
            ).execute(bot, update, trans, subaction_id, data)
        if action_id == ACTION_EDIT_SPECIFIC_ITEM_NAME:
            return EditItemName(
                MODULE_ACTION_TYPE,
                ACTION_EDIT_SPECIFIC_ITEM_NAME
            ).execute(bot, update, trans, subaction_id, data)
        if action_id == ACTION_EDIT_SPECIFIC_ITEM_PRICE:
            return EditItemPrice(
                MODULE_ACTION_TYPE,
                ACTION_EDIT_SPECIFIC_ITEM_PRICE
            ).execute(bot, update, trans, subaction_id, data)
        if action_id == ACTION_GET_DELETE_ITEM_KB:
            return DisplayDeleteItemsKB(
                MODULE_ACTION_TYPE,
                ACTION_GET_DELETE_ITEM_KB
            ).execute(bot, update, trans, subaction_id, data)
        if action_id == ACTION_DELETE_SPECIFIC_ITEM:
            return DeleteItem(
                MODULE_ACTION_TYPE,
                ACTION_DELETE_SPECIFIC_ITEM
            ).execute(bot, update, trans, subaction_id, data)


class CreateNewBill(Action):
    ACTION_CREATE_NEW_BILL = 0
    ACTION_NEW_BILL_SET_NAME = 1

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_CREATE_NEW_BILL:
            return self.create_new_bill(bot, update, trans)

        if subaction_id == self.ACTION_NEW_BILL_SET_NAME:
            return self.add_bill_name(bot, update, trans)

    def create_new_bill(self, bot, update, trans):
        self.set_session(
            update.message.chat_id,
            update.message.from_user,
            self.action_type,
            self.action_id,
            self.ACTION_NEW_BILL_SET_NAME,
            trans
        )
        bot.sendMessage(
            chat_id=update.message.chat_id,
            text=REQUEST_BILL_NAME
        )

    def add_bill_name(self, bot, update, trans):
        msg = update.message
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
            return send_bill_response(
                bot,
                msg.chat_id,
                msg.from_user.id,
                bill_id,
                trans,
                keyboard=DisplayNewBillKB.get_new_bill_keyboard(bill_id)
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


class DisplayNewBillKB(Action):
    ACTION_DISPLAY_NEW_BILL_KB = 0

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DISPLAY_NEW_BILL_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return cbq.edit_message_reply_markup(
                reply_markup=self.get_new_bill_keyboard(bill_id)
            )

    @staticmethod
    def get_new_bill_keyboard(bill_id):
        modify_items_btn = InlineKeyboardButton(
            text="Add/Edit Items",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_MODIFY_ITEMS_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        modify_taxes_btn = InlineKeyboardButton(
            text="Add/Edit Taxes",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_MODIFY_TAXES_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        done_btn = InlineKeyboardButton(
            text="Done",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_CREATE_BILL_DONE,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        return InlineKeyboardMarkup(
            [[modify_items_btn],
             [modify_taxes_btn],
             [done_btn]]
        )


class DisplayModifyItemsKB(Action):
    ACTION_DISPLAY_MODIFY_ITEMS_KB = 0

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DISPLAY_MODIFY_ITEMS_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return cbq.edit_message_reply_markup(
                reply_markup=self.get_modify_items_keyboard(bill_id)
            )

    @staticmethod
    def get_modify_items_keyboard(bill_id):
        add_item_btn = InlineKeyboardButton(
            text="Add item(s)",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_ADD_ITEMS,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        edit_item_btn = InlineKeyboardButton(
            text="Edit item",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_EDIT_ITEM_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        del_item_btn = InlineKeyboardButton(
            text="Delete item",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_DELETE_ITEM_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        back_btn = InlineKeyboardButton(
            text="Back",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_NEW_BILL_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        return InlineKeyboardMarkup(
            [[add_item_btn],
             [edit_item_btn],
             [del_item_btn],
             [back_btn]]
        )


class DisplayModifyTaxesKB(Action):
    ACTION_DISPLAY_MODIFY_TAXES_KB = 0

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DISPLAY_MODIFY_TAXES_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return cbq.edit_message_reply_markup(
                reply_markup=self.get_modify_taxes_keyboard(bill_id)
            )

    @staticmethod
    def get_modify_taxes_keyboard(bill_id):
        add_tax_btn = InlineKeyboardButton(
            text="Add tax",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_ADD_TAX,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        edit_tax_btn = InlineKeyboardButton(
            text="Edit tax",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_EDIT_TAX,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        del_tax_btn = InlineKeyboardButton(
            text="Delete tax",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_DELETE_TAX,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        back_btn = InlineKeyboardButton(
            text="Back",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_NEW_BILL_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        return InlineKeyboardMarkup(
            [[add_tax_btn],
             [edit_tax_btn],
             [del_tax_btn],
             [back_btn]]
        )


class DisplayEditItemsKB(Action):
    ACTION_DISPLAY_EDIT_ITEMS_KB = 0

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DISPLAY_EDIT_ITEMS_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return cbq.edit_message_reply_markup(
                reply_markup=self.get_edit_items_keyboard(bill_id, trans)
            )

    @staticmethod
    def get_edit_items_keyboard(bill_id, trans):
        kb = get_item_buttons(bill_id, ACTION_GET_EDIT_SPECIFIC_ITEM_KB, trans)
        back_btn = InlineKeyboardButton(
            text="Back",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_MODIFY_ITEMS_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        kb.append([back_btn])
        return InlineKeyboardMarkup(kb)


class DisplayEditSpecificItemKB(Action):
    ACTION_DISPLAY_EDIT_SPECIFIC_ITEM_KB = 0

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DISPLAY_EDIT_SPECIFIC_ITEM_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            item_id = data.get(const.JSON_ITEM_ID)
            return cbq.edit_message_reply_markup(
                reply_markup=self.get_edit_item_keyboard(
                    bill_id,
                    item_id,
                    trans
                )
            )

    @staticmethod
    def get_edit_item_keyboard(bill_id, item_id, trans):
        name, price = trans.get_item(item_id)
        edit_name_btn = InlineKeyboardButton(
            text="Edit Name: '{}'".format(name),
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_EDIT_SPECIFIC_ITEM_NAME,
                {const.JSON_BILL_ID: bill_id,
                 const.JSON_ITEM_ID: item_id}
            )
        )
        edit_price_btn = InlineKeyboardButton(
            text="Edit Price: '{:.2f}'".format(price),
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_EDIT_SPECIFIC_ITEM_PRICE,
                {const.JSON_BILL_ID: bill_id,
                 const.JSON_ITEM_ID: item_id}
            )
        )
        back_btn = InlineKeyboardButton(
            text="Back",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_EDIT_ITEM_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        return InlineKeyboardMarkup([
            [edit_name_btn],
            [edit_price_btn],
            [back_btn]
        ])


class DisplayDeleteItemsKB(Action):
    ACTION_DISPLAY_DELETE_ITEMS_KB = 0

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DISPLAY_DELETE_ITEMS_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return cbq.edit_message_reply_markup(
                reply_markup=self.get_delete_items_keyboard(bill_id, trans)
            )

    @staticmethod
    def get_delete_items_keyboard(bill_id, trans):
        kb = get_item_buttons(bill_id, ACTION_DELETE_SPECIFIC_ITEM, trans)
        back_btn = InlineKeyboardButton(
            text="Back",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_MODIFY_ITEMS_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        kb.append([back_btn])
        return InlineKeyboardMarkup(kb)


class AddItems(Action):
    ACTION_ASK_FOR_ITEMS = 0
    ACTION_PROCESS_ITEMS = 1
    ACTION_ADD_ITEM_PRICE = 2

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_ASK_FOR_ITEMS:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return self.ask_for_item(bot, cbq, bill_id, trans)

        if subaction_id == self.ACTION_PROCESS_ITEMS:
            return self.add_item(bot, update.message, trans, data)

        if subaction_id == self.ACTION_ADD_ITEM_PRICE:
            return self.add_item_price(bot, update.message, trans, data)

    def ask_for_item(self, bot, cbq, bill_id, trans):
        self.set_session(
            cbq.message.chat_id,
            cbq.from_user,
            MODULE_ACTION_TYPE,
            ACTION_ADD_ITEMS,
            self.ACTION_PROCESS_ITEMS,
            trans,
            data={'bill_id': bill_id}
        )
        cbq.answer()
        bot.sendMessage(chat_id=cbq.message.chat_id, text=REQUEST_ITEM_NAME)

    def add_item(self, bot, msg, trans, data):
        try:
            if Filters.text.filter(msg):
                return self.add_item_name(bot, msg, trans, data)

            if Filters.image.filter(msg):
                return self.add_items_img(bot, msg, trans, data)

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

    def add_item_name(self, bot, msg, trans, data):
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
            self.action_type,
            self.action_id,
            self.ACTION_ADD_ITEM_PRICE,
            trans,
            data=data
        )
        return bot.sendMessage(
            chat_id=msg.chat_id,
            text=REQUEST_ITEM_PRICE
        )

    def add_item_price(self, bot, msg, trans, data):
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
            return send_bill_response(
                bot,
                msg.chat_id,
                msg.from_user.id,
                bill_id,
                trans,
                keyboard=DisplayModifyItemsKB.get_modify_items_keyboard(
                    bill_id
                )
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


class EditItemName(Action):
    ACTION_ASK_FOR_ITEM_NAME = 0
    ACTION_UPDATE_ITEM_NAME = 1

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_ASK_FOR_ITEM_NAME:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            item_id = data.get(const.JSON_ITEM_ID)
            return self.ask_for_edited_item_name(
                bot,
                cbq,
                bill_id,
                item_id,
                trans
            )

        if subaction_id == self.ACTION_UPDATE_ITEM_NAME:
            return self.edit_item_name(bot, update.message, trans, data)

    def ask_for_edited_item_name(self, bot, cbq, bill_id, item_id, trans):
        self.set_session(
            cbq.message.chat_id,
            cbq.from_user,
            self.action_type,
            self.action_id,
            self.ACTION_UPDATE_ITEM_NAME,
            trans,
            data={'bill_id': bill_id,
                  'item_id': item_id}
        )
        cbq.answer()
        bot.sendMessage(
            chat_id=cbq.message.chat_id,
            text=REQUEST_EDIT_ITEM_NAME
        )

    def edit_item_name(self, bot, msg, trans, data):
        text = msg.text
        if (text is None or len(text) < 1 or len(text) > 250):
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_ITEM_NAME
            )
        try:
            bill_id = data.get('bill_id')
            if bill_id is None:
                raise Exception('bill_id is None')
            item_id = data.get('item_id')
            if item_id is None:
                raise Exception('item_id is None')
            trans.edit_item_name(bill_id, item_id, msg.from_user.id, text)
            trans.reset_session(msg.from_user.id, msg.chat_id)
            return send_bill_response(
                bot,
                msg.chat_id,
                msg.from_user.id,
                bill_id,
                trans,
                keyboard=DisplayEditSpecificItemKB.get_edit_item_keyboard(
                    bill_id,
                    item_id,
                    trans
                )
            )
        except Exception as e:
            print(e)
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_SOMETHING_WENT_WRONG
            )


class EditItemPrice(Action):
    ACTION_ASK_FOR_ITEM_PRICE = 0
    ACTION_UPDATE_ITEM_PRICE = 1

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_ASK_FOR_ITEM_PRICE:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            item_id = data.get(const.JSON_ITEM_ID)
            return self.ask_for_edited_item_price(
                bot,
                cbq,
                bill_id,
                item_id,
                trans
            )

        if subaction_id == self.ACTION_UPDATE_ITEM_PRICE:
            return self.edit_item_price(bot, update.message, trans, data)

    def ask_for_edited_item_price(self, bot, cbq, bill_id, item_id, trans):
        self.set_session(
            cbq.message.chat_id,
            cbq.from_user,
            self.action_type,
            self.action_id,
            self.ACTION_UPDATE_ITEM_PRICE,
            trans,
            data={'bill_id': bill_id,
                  'item_id': item_id}
        )
        cbq.answer()
        bot.sendMessage(
            chat_id=cbq.message.chat_id,
            text=REQUEST_EDIT_ITEM_PRICE
        )

    def edit_item_price(self, bot, msg, trans, data):
        text = msg.text
        try:
            price = float(text)
            bill_id = data.get('bill_id')
            if bill_id is None:
                raise Exception('bill_id is None')
            item_id = data.get('item_id')
            if item_id is None:
                raise Exception('item_id is None')
            trans.edit_item_price(bill_id, item_id, msg.from_user.id, price)
            trans.reset_session(msg.from_user.id, msg.chat_id)
            return send_bill_response(
                bot,
                msg.chat_id,
                msg.from_user.id,
                bill_id,
                trans,
                keyboard=DisplayEditSpecificItemKB.get_edit_item_keyboard(
                    bill_id,
                    item_id,
                    trans
                )
            )
        except ValueError as e:
            print(e)
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_FLOAT_VALUE.format('item price')
            )
        except Exception as e:
            print(e)


class DeleteItem(Action):
    ACTION_DELETE_ITEM = 0

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DELETE_ITEM:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            item_id = data.get(const.JSON_ITEM_ID)
            return self.delete_item(
                bot,
                cbq,
                bill_id,
                item_id,
                trans
            )

    def delete_item(self, bot, cbq, bill_id, item_id, trans):
        trans.delete_item(bill_id, item_id, cbq.from_user.id)
        trans.reset_session(cbq.from_user.id, cbq.message.chat_id)
        return cbq.edit_message_text(
            text=get_bill_text(bill_id, cbq.from_user.id, trans),
            parse_mode=ParseMode.HTML,
            reply_markup=DisplayDeleteItemsKB.get_delete_items_keyboard(
                bill_id, trans
            )
        )


class BillError(Exception):
    pass


def send_bill_response(bot, chat_id, user_id,
                       bill_id, trans, keyboard):
    bot.sendMessage(
        chat_id=chat_id,
        text=get_bill_text(bill_id, user_id, trans),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


def get_bill_text(bill_id, user_id, trans):
    try:
        bill = trans.get_bill_details(bill_id, user_id)
        if bill.get('title') is None or len(bill.get('title')) == 0:
            raise Exception('Bill does not exist')

        title_text = '<b>{}</b>'.format(utils.escape_html(bill['title']))

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
                                  const.EMOJI_MONEY_BAG +
                                  '{:.2f}'.format(price))

        bill_taxes = bill.get('taxes')
        taxes_text = []
        if bill_taxes is not None:
            for title, tax in bill_taxes:
                total += (tax * total / 100)
                taxes_text.append(const.EMOJI_TAX + ' ' + title +
                                  ': ' + tax + '%')

        text = title_text + '\n\n' + '\n'.join(items_text)
        if len(taxes_text) > 0:
            text += '\n\n' + '\n'.join(taxes_text)

        text += '\n\n' + 'Total: ' + "{:.2f}".format(total)
        return text
    except Exception as e:
        print(e)


def get_item_buttons(bill_id, action, trans):
    keyboard = []
    items = trans.get_bill_items(bill_id)
    for item_id, item_name, __ in items:
        item_btn = InlineKeyboardButton(
            text=item_name,
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                action,
                {const.JSON_BILL_ID: bill_id,
                 const.JSON_ITEM_ID: item_id}
            )
        )
        keyboard.append([item_btn])

    return keyboard
