from telegram.ext import Filters
from telegram.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.inlinekeyboardbutton import InlineKeyboardButton
from telegram.parsemode import ParseMode

from action_handlers.action_handler import ActionHandler, Action
from action_handlers import manage_bill_handler
import constants as const
import utils
import logging

MODULE_ACTION_TYPE = const.TYPE_CREATE_BILL

ACTION_NEW_BILL = 0
ACTION_GET_MODIFY_ITEMS_KB = 1
ACTION_GET_MODIFY_TAXES_KB = 2
ACTION_CREATE_BILL_DONE = 3
ACTION_ADD_ITEMS = 4
ACTION_GET_EDIT_ITEM_KB = 5
ACTION_GET_DELETE_ITEM_KB = 6
ACTION_ADD_TAX = 7
ACTION_GET_EDIT_TAX_KB = 8
ACTION_GET_DELETE_TAX_KB = 9
ACTION_GET_NEW_BILL_KB = 10
ACTION_GET_EDIT_SPECIFIC_ITEM_KB = 11
ACTION_EDIT_SPECIFIC_ITEM_NAME = 14
ACTION_EDIT_SPECIFIC_ITEM_PRICE = 15
ACTION_DELETE_SPECIFIC_ITEM = 16
ACTION_GET_EDIT_SPECIFIC_TAX_KB = 17
ACTION_EDIT_SPECIFIC_TAX_NAME = 18
ACTION_EDIT_SPECIFIC_TAX_AMT = 19
ACTION_DELETE_SPECIFIC_TAX = 20

REQUEST_BILL_NAME = "Send me a name for the new bill you want to create."
REQUEST_ITEM_NAME = "Okay. Send me the name of the item."
REQUEST_ITEM_NAME_2 = "Got it. Send me the name of the next item you want to add. When you are done adding items, just let me know by sending /done."
REQUEST_ITEM_PRICE = "Great! Now send me the price of the item. Leave out the currency and provide only the value (e.g. 8.00 or 8)."
REQUEST_EDIT_ITEM_NAME = "Okay. Send me the new name of the item."
REQUEST_EDIT_ITEM_PRICE = "Okay. Send me the new price of the item. Leave out the currency and provide only the value (e.g. 8.00 or 8)."
REQUEST_TAX_NAME = "Can do. Send me the name of the tax."
REQUEST_TAX_NAME_2 = "Got it. Send me the name of the next tax you want to add. When you are done adding taxes, just let me know by sending /done."
REQUEST_TAX_AMT = "Great! Now send me the tax amount in whole numbers. Leave out the percentage sign (e.g. 7 or 7.00)."
REQUEST_EDIT_TAX_NAME = "Okay. Send me the new name of the tax."
REQUEST_EDIT_TAX_AMT = "Can do. Send me the new tax amount in whole numbers. Leave out the percentage sign (e.g. 7 or 7.00)."

ERROR_INVALID_BILL_NAME = "Sorry, the bill name provided is invalid. Name of the bill can only be 250 characters long. Please try again."
ERROR_SOMETHING_WENT_WRONG = "Sorry, an error has occurred. Please try again in a few moments."
ERROR_INVALID_ITEM_NAME = "Sorry, the item name provided is invalid. Name of the item can only be 250 characters long. Please try again."
ERROR_INVALID_TAX_NAME = "Sorry, the tax name provided is invalid. Name of the item can only be 250 characters long. Please try again."
ERROR_INVALID_FLOAT_VALUE = "Sorry, the {} provided is invalid. Value provided should be strictly digits only or with an optional decimal point (e.g. 8.00 or 8)."


class BillCreationHandler(ActionHandler):
    """docstring for NewBillHandler"""

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE)

    def evaluate_rights(self, update, trans, data):
        if data is None:
            return True, None, None
        bill_id = data.get(const.JSON_BILL_ID)
        if bill_id is None:
            return True, None, None

        __, owner_id, is_complete, is_closed = trans.get_bill_gen_info(bill_id)
        chat_id = None
        if update.callback_query is not None:
            has_rights = update.callback_query.from_user.id == owner_id
            chat_id = update.callback_query.message.chat_id
            if not has_rights:
                return has_rights, chat_id, 'Sorry, you do not have permission for this action.'

        if chat_id is None and update.message is not None:
            has_rights = update.message.from_user.id == owner_id
            chat_id = update.message.chat_id
            if not has_rights:
                return has_rights, chat_id, 'Sorry, you do not have permission for this action.'

        if is_complete is not None:
            return False, chat_id, 'Sorry, bill is already finalized and cannot be edited.'
        if is_closed is not None:
            return False, chat_id, 'Sorry, bill is already calculated and closed.'

        return True, None, None

    def execute(self, bot, update, trans, action_id,
                subaction_id=0, data=None):
        has_rights, chat_id, text = self.evaluate_rights(update, trans, data)
        if not has_rights:
            if chat_id is not None:
                if update.callback_query is not None:
                    update.callback_query.answer()
                bot.sendMessage(
                    chat_id=chat_id,
                    text=text
                )
            return

        action = None
        if action_id == ACTION_NEW_BILL:
            action = CreateNewBill()
        if action_id == ACTION_GET_NEW_BILL_KB:
            action = DisplayNewBillKB()
        if action_id == ACTION_GET_MODIFY_ITEMS_KB:
            action = DisplayModifyItemsKB()
        if action_id == ACTION_GET_MODIFY_TAXES_KB:
            action = DisplayModifyTaxesKB()
        if action_id == ACTION_GET_EDIT_ITEM_KB:
            action = DisplayEditItemsKB()
        if action_id == ACTION_GET_EDIT_SPECIFIC_ITEM_KB:
            action = DisplayEditSpecificItemKB()
        if action_id == ACTION_GET_DELETE_ITEM_KB:
            action = DisplayDeleteItemsKB()
        if action_id == ACTION_GET_EDIT_TAX_KB:
            action = DisplayEditTaxesKB()
        if action_id == ACTION_GET_EDIT_SPECIFIC_TAX_KB:
            action = DisplayEditSpecificTaxKB()
        if action_id == ACTION_GET_DELETE_TAX_KB:
            action = DisplayDeleteTaxesKB()
        if action_id == ACTION_ADD_ITEMS:
            action = AddItems()
        if action_id == ACTION_EDIT_SPECIFIC_ITEM_NAME:
            action = EditItemName()
        if action_id == ACTION_EDIT_SPECIFIC_ITEM_PRICE:
            action = EditItemPrice()
        if action_id == ACTION_DELETE_SPECIFIC_ITEM:
            action = DeleteItem()
        if action_id == ACTION_ADD_TAX:
            action = AddTax()
        if action_id == ACTION_EDIT_SPECIFIC_TAX_NAME:
            action = EditTaxName()
        if action_id == ACTION_EDIT_SPECIFIC_TAX_AMT:
            action = EditTaxAmt()
        if action_id == ACTION_DELETE_SPECIFIC_TAX:
            action = DeleteTax()
        if action_id == ACTION_CREATE_BILL_DONE:
            action = CreateBillDone()

        if action is None:
            return

        action.execute(bot, update, trans, subaction_id, data)

    def execute_done(self, bot, update, trans, action_id,
                     subaction_id=0, data=None):
        action = None
        if action_id == ACTION_ADD_ITEMS:
            action = AddItems()
        if action_id == ACTION_ADD_TAX:
            action = AddTax()

        if action is None:
            return

        action.done(bot, update, trans, subaction_id, data)


class CreateNewBill(Action):
    ACTION_CREATE_NEW_BILL = 0
    ACTION_NEW_BILL_SET_NAME = 1

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_NEW_BILL)

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
            logging.exception('add_bill_name')
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=str(e)
            )
        except Exception as e:
            logging.exception('add_bill_name')
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_SOMETHING_WENT_WRONG
            )


class DisplayNewBillKB(Action):
    ACTION_DISPLAY_NEW_BILL_KB = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_NEW_BILL_KB)

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

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_MODIFY_ITEMS_KB)

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

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_MODIFY_TAXES_KB)

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
                ACTION_GET_EDIT_TAX_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        del_tax_btn = InlineKeyboardButton(
            text="Delete tax",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_DELETE_TAX_KB,
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

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_EDIT_ITEM_KB)

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

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_EDIT_SPECIFIC_ITEM_KB)

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

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_DELETE_ITEM_KB)

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


class DisplayEditTaxesKB(Action):
    ACTION_DISPLAY_EDIT_TAXES_KB = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_EDIT_TAX_KB)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DISPLAY_EDIT_TAXES_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return cbq.edit_message_reply_markup(
                reply_markup=self.get_edit_taxes_keyboard(bill_id, trans)
            )

    @staticmethod
    def get_edit_taxes_keyboard(bill_id, trans):
        kb = get_tax_buttons(bill_id, ACTION_GET_EDIT_SPECIFIC_TAX_KB, trans)
        back_btn = InlineKeyboardButton(
            text="Back",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_MODIFY_TAXES_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        kb.append([back_btn])
        return InlineKeyboardMarkup(kb)


class DisplayEditSpecificTaxKB(Action):
    ACTION_DISPLAY_EDIT_SPECIFIC_TAX_KB = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_EDIT_SPECIFIC_TAX_KB)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DISPLAY_EDIT_SPECIFIC_TAX_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            tax_id = data.get(const.JSON_TAX_ID)
            return cbq.edit_message_reply_markup(
                reply_markup=self.get_edit_tax_keyboard(
                    bill_id,
                    tax_id,
                    trans
                )
            )

    @staticmethod
    def get_edit_tax_keyboard(bill_id, tax_id, trans):
        name, amt = trans.get_tax(tax_id)
        edit_name_btn = InlineKeyboardButton(
            text="Edit Name: '{}'".format(name),
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_EDIT_SPECIFIC_TAX_NAME,
                {const.JSON_BILL_ID: bill_id,
                 const.JSON_TAX_ID: tax_id}
            )
        )
        edit_amt_btn = InlineKeyboardButton(
            text="Edit Amount: '{:.2f}'".format(amt),
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_EDIT_SPECIFIC_TAX_AMT,
                {const.JSON_BILL_ID: bill_id,
                 const.JSON_TAX_ID: tax_id}
            )
        )
        back_btn = InlineKeyboardButton(
            text="Back",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_EDIT_TAX_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        return InlineKeyboardMarkup([
            [edit_name_btn],
            [edit_amt_btn],
            [back_btn]
        ])


class DisplayDeleteTaxesKB(Action):
    ACTION_DISPLAY_DELETE_TAXES_KB = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_DELETE_TAX_KB)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DISPLAY_DELETE_TAXES_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return cbq.edit_message_reply_markup(
                reply_markup=self.get_delete_taxes_keyboard(bill_id, trans)
            )

    @staticmethod
    def get_delete_taxes_keyboard(bill_id, trans):
        kb = get_tax_buttons(bill_id, ACTION_DELETE_SPECIFIC_TAX, trans)
        back_btn = InlineKeyboardButton(
            text="Back",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_MODIFY_TAXES_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        kb.append([back_btn])
        return InlineKeyboardMarkup(kb)


class AddItems(Action):
    ACTION_ASK_FOR_ITEMS = 0
    ACTION_PROCESS_ITEMS = 1
    ACTION_ADD_ITEM_PRICE = 2

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_ADD_ITEMS)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_ASK_FOR_ITEMS:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return self.ask_for_item(bot, cbq, bill_id, trans)

        if subaction_id == self.ACTION_PROCESS_ITEMS:
            return self.add_item(bot, update.message, trans, data)

        if subaction_id == self.ACTION_ADD_ITEM_PRICE:
            return self.add_item_price(bot, update.message, trans, data)

    def done(self, bot, update, trans, subaction_id, data=None):
        msg = update.message
        bill_id = data.get(const.JSON_BILL_ID)
        trans.reset_session(msg.from_user.id, msg.chat_id)
        return send_bill_response(
            bot,
            msg.chat_id,
            msg.from_user.id,
            bill_id,
            trans,
            keyboard=DisplayNewBillKB.get_new_bill_keyboard(
                bill_id
            )
        )

    def ask_for_item(self, bot, cbq, bill_id, trans):
        self.set_session(
            cbq.message.chat_id,
            cbq.from_user,
            self.action_type,
            self.action_id,
            self.ACTION_PROCESS_ITEMS,
            trans,
            data={const.JSON_BILL_ID: bill_id}
        )
        cbq.answer()
        bot.sendMessage(chat_id=cbq.message.chat_id, text=REQUEST_ITEM_NAME)

    def add_item(self, bot, msg, trans, data):
        try:
            if Filters.text.filter(msg):
                return self.add_item_name(bot, msg, trans, data)

            # if Filters.image.filter(msg):
            #     return self.add_items_img(bot, msg, trans, data)

            # all other message types invalid
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_ITEM_NAME
            )
        except BillError as e:
            logging.exception('add_item')
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=str(e)
            )
        except Exception as e:
            logging.exception('add_item')
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
        if not Filters.text.filter(msg):
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_FLOAT_VALUE.format('item price')
            )

        text = msg.text

        try:
            price = float(text)
            bill_id = data.get(const.JSON_BILL_ID)
            if bill_id is None:
                raise Exception('bill_id is None')
            item_name = data.get('item_name')
            if item_name is None:
                raise Exception('item_name is None')
            trans.add_item(bill_id, item_name, price)
            self.set_session(
                msg.chat_id,
                msg.from_user,
                self.action_type,
                self.action_id,
                self.ACTION_PROCESS_ITEMS,
                trans,
                data=data
            )
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=REQUEST_ITEM_NAME_2
            )
        except ValueError as e:
            logging.exception('add_item_price')
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_FLOAT_VALUE.format('item price')
            )
        except Exception as e:
            logging.exception('add_item_price')

    def add_items_img(self, msg, bot, trans, data):
        pass


class EditItemName(Action):
    ACTION_ASK_FOR_ITEM_NAME = 0
    ACTION_UPDATE_ITEM_NAME = 1

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_EDIT_SPECIFIC_ITEM_NAME)

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
            data={const.JSON_BILL_ID: bill_id,
                  const.JSON_ITEM_ID: item_id}
        )
        cbq.answer()
        bot.sendMessage(
            chat_id=cbq.message.chat_id,
            text=REQUEST_EDIT_ITEM_NAME
        )

    def edit_item_name(self, bot, msg, trans, data):
        if not Filters.text.filter(msg):
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_ITEM_NAME
            )

        text = msg.text
        if (text is None or len(text) < 1 or len(text) > 250):
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_ITEM_NAME
            )
        try:
            bill_id = data.get(const.JSON_BILL_ID)
            if bill_id is None:
                raise Exception('bill_id is None')
            item_id = data.get(const.JSON_ITEM_ID)
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
            logging.exception('edit_item_name')
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_SOMETHING_WENT_WRONG
            )


class EditItemPrice(Action):
    ACTION_ASK_FOR_ITEM_PRICE = 0
    ACTION_UPDATE_ITEM_PRICE = 1

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_EDIT_SPECIFIC_ITEM_PRICE)

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
            data={const.JSON_BILL_ID: bill_id,
                  const.JSON_ITEM_ID: item_id}
        )
        cbq.answer()
        bot.sendMessage(
            chat_id=cbq.message.chat_id,
            text=REQUEST_EDIT_ITEM_PRICE
        )

    def edit_item_price(self, bot, msg, trans, data):
        if not Filters.text.filter(msg):
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_FLOAT_VALUE.format('item price')
            )

        text = msg.text
        try:
            price = float(text)
            bill_id = data.get(const.JSON_BILL_ID)
            if bill_id is None:
                raise Exception('bill_id is None')
            item_id = data.get(const.JSON_ITEM_ID)
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
            logging.exception('edit_item_price')
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_FLOAT_VALUE.format('item price')
            )
        except Exception as e:
            logging.exception('edit_item_price')


class DeleteItem(Action):
    ACTION_DELETE_ITEM = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_DELETE_SPECIFIC_ITEM)

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


class AddTax(Action):
    ACTION_ASK_FOR_TAX = 0
    ACTION_ADD_TAX_NAME = 1
    ACTION_ADD_TAX_AMT = 2

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_ADD_TAX)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_ASK_FOR_TAX:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return self.ask_for_tax(bot, cbq, bill_id, trans)

        if subaction_id == self.ACTION_ADD_TAX_NAME:
            return self.add_tax_name(bot, update.message, trans, data)

        if subaction_id == self.ACTION_ADD_TAX_AMT:
            return self.add_tax_amt(bot, update.message, trans, data)

    def done(self, bot, update, trans, subaction_id, data=None):
        msg = update.message
        bill_id = data.get(const.JSON_BILL_ID)
        trans.reset_session(msg.from_user.id, msg.chat_id)
        return send_bill_response(
            bot,
            msg.chat_id,
            msg.from_user.id,
            bill_id,
            trans,
            keyboard=DisplayNewBillKB.get_new_bill_keyboard(
                bill_id
            )
        )

    def ask_for_tax(self, bot, cbq, bill_id, trans):
        self.set_session(
            cbq.message.chat_id,
            cbq.from_user,
            self.action_type,
            self.action_id,
            self.ACTION_ADD_TAX_NAME,
            trans,
            data={const.JSON_BILL_ID: bill_id}
        )
        cbq.answer()
        bot.sendMessage(chat_id=cbq.message.chat_id, text=REQUEST_TAX_NAME)

    def add_tax_name(self, bot, msg, trans, data):
        try:
            if not Filters.text.filter(msg):
                raise BillError(ERROR_INVALID_TAX_NAME)

            text = msg.text
            if (text is None or len(text) < 1 or len(text) > 250):
                return bot.sendMessage(
                    chat_id=msg.chat_id,
                    text=ERROR_INVALID_TAX_NAME
                )

            data['tax_name'] = text
            self.set_session(
                msg.chat_id,
                msg.from_user,
                self.action_type,
                self.action_id,
                self.ACTION_ADD_TAX_AMT,
                trans,
                data=data
            )
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=REQUEST_TAX_AMT
            )
        except BillError as e:
            logging.exception('add_tax_name')
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=str(e)
            )
        except Exception as e:
            logging.exception('add_tax_name')
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_SOMETHING_WENT_WRONG
            )

    def add_tax_amt(self, bot, msg, trans, data):
        try:
            if not Filters.text.filter(msg):
                raise BillError(ERROR_INVALID_TAX_NAME)

            text = msg.text
            amt = float(text)
            bill_id = data.get(const.JSON_BILL_ID)
            if bill_id is None:
                raise Exception('bill_id is None')
            tax_name = data.get('tax_name')
            if tax_name is None:
                raise Exception('tax_name is None')
            trans.add_tax(bill_id, tax_name, amt)
            self.set_session(
                msg.chat_id,
                msg.from_user,
                self.action_type,
                self.action_id,
                self.ACTION_ADD_TAX_NAME,
                trans,
                data=data
            )
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=REQUEST_TAX_NAME_2
            )
        except (ValueError, BillError) as e:
            logging.exception('add_tax_amt')
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_FLOAT_VALUE.format('tax amount')
            )
        except Exception as e:
            logging.exception('add_tax_amt')


class EditTaxName(Action):
    ACTION_ASK_FOR_TAX_NAME = 0
    ACTION_UPDATE_TAX_NAME = 1

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_EDIT_SPECIFIC_TAX_NAME)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_ASK_FOR_TAX_NAME:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            tax_id = data.get(const.JSON_TAX_ID)
            return self.ask_for_edited_tax_name(
                bot,
                cbq,
                bill_id,
                tax_id,
                trans
            )

        if subaction_id == self.ACTION_UPDATE_TAX_NAME:
            return self.edit_tax_name(bot, update.message, trans, data)

    def ask_for_edited_tax_name(self, bot, cbq, bill_id, tax_id, trans):
        self.set_session(
            cbq.message.chat_id,
            cbq.from_user,
            self.action_type,
            self.action_id,
            self.ACTION_UPDATE_TAX_NAME,
            trans,
            data={const.JSON_BILL_ID: bill_id,
                  const.JSON_TAX_ID: tax_id}
        )
        cbq.answer()
        bot.sendMessage(
            chat_id=cbq.message.chat_id,
            text=REQUEST_EDIT_TAX_NAME
        )

    def edit_tax_name(self, bot, msg, trans, data):
        if not Filters.text.filter(msg):
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_TAX_NAME
            )

        text = msg.text
        if (text is None or len(text) < 1 or len(text) > 250):
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_TAX_NAME
            )
        try:
            bill_id = data.get(const.JSON_BILL_ID)
            if bill_id is None:
                raise Exception('bill_id is None')
            tax_id = data.get(const.JSON_TAX_ID)
            if tax_id is None:
                raise Exception('tax_id is None')
            trans.edit_tax_name(bill_id, tax_id, msg.from_user.id, text)
            trans.reset_session(msg.from_user.id, msg.chat_id)
            return send_bill_response(
                bot,
                msg.chat_id,
                msg.from_user.id,
                bill_id,
                trans,
                keyboard=DisplayEditSpecificTaxKB.get_edit_tax_keyboard(
                    bill_id,
                    tax_id,
                    trans
                )
            )
        except Exception as e:
            logging.exception('edit_tax_name')
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_SOMETHING_WENT_WRONG
            )


class EditTaxAmt(Action):
    ACTION_ASK_FOR_TAX_AMT = 0
    ACTION_UPDATE_TAX_AMT = 1

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_EDIT_SPECIFIC_TAX_AMT)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_ASK_FOR_TAX_AMT:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            tax_id = data.get(const.JSON_TAX_ID)
            return self.ask_for_edited_tax_amt(
                bot,
                cbq,
                bill_id,
                tax_id,
                trans
            )

        if subaction_id == self.ACTION_UPDATE_TAX_AMT:
            return self.edit_tax_amt(bot, update.message, trans, data)

    def ask_for_edited_tax_amt(self, bot, cbq, bill_id, tax_id, trans):
        self.set_session(
            cbq.message.chat_id,
            cbq.from_user,
            self.action_type,
            self.action_id,
            self.ACTION_UPDATE_TAX_AMT,
            trans,
            data={const.JSON_BILL_ID: bill_id,
                  const.JSON_TAX_ID: tax_id}
        )
        cbq.answer()
        bot.sendMessage(
            chat_id=cbq.message.chat_id,
            text=REQUEST_EDIT_TAX_AMT
        )

    def edit_tax_amt(self, bot, msg, trans, data):
        if not Filters.text.filter(msg):
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_FLOAT_VALUE.format('tax amount')
            )

        text = msg.text
        try:
            amt = float(text)
            bill_id = data.get(const.JSON_BILL_ID)
            if bill_id is None:
                raise Exception('bill_id is None')
            tax_id = data.get(const.JSON_TAX_ID)
            if tax_id is None:
                raise Exception('tax_id is None')
            trans.edit_tax_amt(bill_id, tax_id, msg.from_user.id, amt)
            trans.reset_session(msg.from_user.id, msg.chat_id)
            return send_bill_response(
                bot,
                msg.chat_id,
                msg.from_user.id,
                bill_id,
                trans,
                keyboard=DisplayEditSpecificTaxKB.get_edit_tax_keyboard(
                    bill_id,
                    tax_id,
                    trans
                )
            )
        except ValueError as e:
            logging.exception('edit_tax_amt')
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_FLOAT_VALUE.format('tax amount')
            )
        except Exception as e:
            logging.exception('edit_tax_amt')


class DeleteTax(Action):
    ACTION_DELETE_TAX = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_DELETE_SPECIFIC_TAX)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DELETE_TAX:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            tax_id = data.get(const.JSON_TAX_ID)
            return self.delete_tax(
                bot,
                cbq,
                bill_id,
                tax_id,
                trans
            )

    def delete_tax(self, bot, cbq, bill_id, tax_id, trans):
        trans.delete_tax(bill_id, tax_id, cbq.from_user.id)
        trans.reset_session(cbq.from_user.id, cbq.message.chat_id)
        return cbq.edit_message_text(
            text=get_bill_text(bill_id, cbq.from_user.id, trans),
            parse_mode=ParseMode.HTML,
            reply_markup=DisplayDeleteTaxesKB.get_delete_taxes_keyboard(
                bill_id, trans
            )
        )


class CreateBillDone(Action):
    ACTION_BILL_DONE = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_CREATE_BILL_DONE)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_BILL_DONE:
            return self.set_bill_done(bot, update, trans, data)

    def set_bill_done(self, bot, update, trans, data):
        bill_id = data.get(const.JSON_BILL_ID)
        cbq = update.callback_query
        trans.set_bill_done(bill_id, cbq.from_user.id)
        manage_bill_handler.BillManagementHandler().execute(
            bot,
            update,
            trans,
            manage_bill_handler.ACTION_GET_MANAGE_BILL,
            data=data
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
        bill = trans.get_bill_details(bill_id)
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

                items_text.append(str(i + 1) + '. ' + title + '  ' +
                                  const.EMOJI_MONEY_BAG +
                                  '{:.2f}'.format(price))

        bill_taxes = bill.get('taxes')
        taxes_text = []
        if bill_taxes is not None:
            for __, title, tax in bill_taxes:
                total += (tax * total / 100)
                taxes_text.append(const.EMOJI_TAX + ' ' + title +
                                  ': ' + '{:.2f}'.format(tax) + '%')

        text = title_text + '\n\n' + '\n'.join(items_text)
        if len(taxes_text) > 0:
            text += '\n\n' + '\n'.join(taxes_text)

        text += '\n\n' + 'Total: ' + "{:.2f}".format(total)
        return text
    except Exception as e:
        logging.exception('get_bill_text')


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


def get_tax_buttons(bill_id, action, trans):
    keyboard = []
    taxes = trans.get_bill_taxes(bill_id)
    for tax_id, tax_name, __ in taxes:
        tax_btn = InlineKeyboardButton(
            text=tax_name,
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                action,
                {const.JSON_BILL_ID: bill_id,
                 const.JSON_TAX_ID: tax_id}
            )
        )
        keyboard.append([tax_btn])

    return keyboard
