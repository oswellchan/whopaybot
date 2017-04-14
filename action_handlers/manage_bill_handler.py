from action_handlers.action_handler import ActionHandler, Action
from telegram.ext import Filters
from telegram.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.inlinekeyboardbutton import InlineKeyboardButton
from telegram.error import BadRequest
import constants as const
import utils
import datetime
import logging
import counter

MODULE_ACTION_TYPE = const.TYPE_MANAGE_BILL

ACTION_GET_MANAGE_BILL = 0
ACTION_GET_MANAGE_BILL_KB = 1
ACTION_SHARE_BILL = 2
ACTION_CALCULATE_SPLIT = 3
ACTION_REFRESH_BILL = 4
ACTION_SEND_DEBTS_BILL_ADMIN = 5
ACTION_GET_CONFIRM_PAYMENTS_KB = 6
ACTION_CONFIRM_BILL_PAYMENT = 7
ACTION_SEND_DEBTS_BILL = 8
ACTION_SEND_BILL = 9
ACTION_SHARE_BILL_ITEM = 10
ACTION_SHARE_ALL_ITEMS = 11
ACTION_GET_SHARE_ITEMS_KB = 12
ACTION_GET_PAY_ITEMS_KB = 13
ACTION_PAY_DEBT = 14
ACTION_GET_INSPECT_BILL_KB = 15

REQUEST_CALC_SPLIT_CONFIRMATION = "You are about to calculate the splitting of the bill. Once this is done, no new person can be added to the bill anymore. Do you wish to continue? Reply 'yes' or 'no'."
ERROR_INVALID_CONFIRMATION = "Sorry, I could not understand the message. Reply 'yes' to continue or 'no' to cancel."
YES_WITH_QUOTES = "'yes'"
YES = 'yes'
NO_WITH_QUOTES = "'no'"
NO = 'no'


class BillManagementHandler(ActionHandler):
    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE)

    def execute(self, bot, update, trans, action_id,
                subaction_id=0, data=None):
        action = None
        if action_id == ACTION_SEND_BILL:
            action = SendBill()
        if action_id == ACTION_GET_MANAGE_BILL:
            action = SendCompleteBill()
        if action_id == ACTION_REFRESH_BILL:
            action = RefreshBill()
        if action_id == ACTION_CALCULATE_SPLIT:
            action = CalculateBillSplit()
        if action_id == ACTION_GET_CONFIRM_PAYMENTS_KB:
            action = DisplayConfirmPaymentsKB()
        if action_id == ACTION_CONFIRM_BILL_PAYMENT:
            action = ConfirmPayment()
        if action_id == ACTION_SHARE_BILL_ITEM:
            action = ShareBillItem()
        if action_id == ACTION_SHARE_ALL_ITEMS:
            action = ShareAllItems()
        if action_id == ACTION_GET_MANAGE_BILL_KB:
            action = DisplayManageBillKB()
        if action_id == ACTION_GET_SHARE_ITEMS_KB:
            action = DisplayShareItemsKB()
        if action_id == ACTION_PAY_DEBT:
            action = PayDebt()

        action.execute(bot, update, trans, subaction_id, data)


class SendBill(Action):
    ACTION_SEND_BILL = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_SEND_BILL)

    def execute(self, bot, update, trans, subaction_id=0, data=None):
        bill_id = data.get(const.JSON_BILL_ID)
        msg = update.message
        __, __, __, is_closed = trans.get_bill_gen_info(bill_id)
        if is_closed is None:
            text, pm, kb = SendCompleteBill.get_appropriate_response(
                bill_id, msg.from_user.id, trans
            )
            bot.sendMessage(
                text=text,
                chat_id=msg.chat_id,
                parse_mode=pm,
                reply_markup=kb
            )
        else:
            return SendDebtsBill().execute(bot, update, trans, 0, data)


class SendCompleteBill(Action):
    ACTION_MANAGE_BILL = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_MANAGE_BILL)

    def execute(self, bot, update, trans, subaction_id=0, data=None):
        if subaction_id == self.ACTION_MANAGE_BILL:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            __, owner_id, __, is_closed = trans.get_bill_gen_info(bill_id)
            if is_closed is not None:
                return

            self.send_bill_response(bot, cbq, bill_id, trans)

    @staticmethod
    def get_appropriate_response(bill_id, user_id, trans):
        text, pm = utils.get_complete_bill_text(bill_id, trans)
        kb = None
        __, owner_id, __, is_closed = trans.get_bill_gen_info(bill_id)
        if user_id == owner_id:
            kb = DisplayManageBillKB.get_manage_bill_keyboard(bill_id, trans)
        else:
            kb = DisplayShareItemsKB.get_share_items_keyboard(bill_id, trans)
        return text, pm, kb

    def send_bill_response(self, bot, cbq, bill_id, trans):
        try:
            chat_id = cbq.message.chat_id
            text, pm, kb = self.get_appropriate_response(
                bill_id, cbq.from_user.id, trans
            )
            trans.reset_session(cbq.from_user.id, chat_id)
            cbq.answer()
            cbq.edit_message_text(
                text=text,
                parse_mode=pm,
                reply_markup=kb
            )
        except BadRequest as e:
            print(e)
        except Exception as e:
            logging.exception('SendCompleteBill')


class DisplayManageBillKB(Action):
    ACTION_DISPLAY_NEW_BILL_KB = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_MANAGE_BILL_KB)

    def execute(self, bot, update, trans, subaction_id, data=None):
        has_rights, chat_id, text = evaluate_rights(update, trans, data)
        if not has_rights:
            if chat_id is not None:
                if update.callback_query is not None:
                    update.callback_query.answer()
                bot.sendMessage(
                    chat_id=chat_id,
                    text=text
                )
            return
        if subaction_id == self.ACTION_DISPLAY_NEW_BILL_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return cbq.edit_message_reply_markup(
                reply_markup=self.get_manage_bill_keyboard(bill_id, trans)
            )

    @staticmethod
    def get_manage_bill_keyboard(bill_id, trans):
        bill_name, __, __, __ = trans.get_bill_gen_info(bill_id)
        share_btn = InlineKeyboardButton(
            text="Share Bill",
            switch_inline_query=bill_name
        )
        refresh_btn = InlineKeyboardButton(
            text="Refresh Bill",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_REFRESH_BILL,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        share_items = InlineKeyboardButton(
            text="Add yourself to Item(s)",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_SHARE_ITEMS_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        calc_bill_btn = InlineKeyboardButton(
            text="Calculate Split",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_CALCULATE_SPLIT,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        return InlineKeyboardMarkup(
            [[share_btn],
             [refresh_btn],
             [share_items],
             [calc_bill_btn]]
        )


class DisplayShareItemsKB(Action):
    ACTION_DISPLAY_SHARE_ITEMS_KB = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_SHARE_ITEMS_KB)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DISPLAY_SHARE_ITEMS_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            kb = self.get_appropriate_keyboard(
                bill_id, cbq.from_user.id, trans
            )
            return cbq.edit_message_reply_markup(reply_markup=kb)

    @staticmethod
    def get_appropriate_keyboard(bill_id, user_id, trans):
        __, owner_id, __, closed_at = trans.get_bill_gen_info(bill_id)
        if owner_id == user_id:
            return DisplayShareItemsKB.get_share_items_admin_keyboard(
                bill_id, trans
            )
        else:
            return DisplayShareItemsKB.get_share_items_keyboard(bill_id, trans)

    @staticmethod
    def get_share_items_keyboard(bill_id, trans):
        keyboard = []
        items = trans.get_bill_items(bill_id)
        refresh_btn = InlineKeyboardButton(
            text='Refresh',
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_REFRESH_BILL,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        keyboard.append([refresh_btn])
        for item_id, item_name, __ in items:
            item_btn = InlineKeyboardButton(
                text=item_name,
                callback_data=utils.get_action_callback_data(
                    MODULE_ACTION_TYPE,
                    ACTION_SHARE_BILL_ITEM,
                    {const.JSON_BILL_ID: bill_id,
                     const.JSON_ITEM_ID: item_id}
                )
            )
            keyboard.append([item_btn])
        share_all_btn = InlineKeyboardButton(
            text='Share all items',
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_SHARE_ALL_ITEMS,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        keyboard.append([share_all_btn])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_share_items_admin_keyboard(bill_id, trans):
        keyboard = []
        items = trans.get_bill_items(bill_id)
        for item_id, item_name, __ in items:
            item_btn = InlineKeyboardButton(
                text=item_name,
                callback_data=utils.get_action_callback_data(
                    MODULE_ACTION_TYPE,
                    ACTION_SHARE_BILL_ITEM,
                    {const.JSON_BILL_ID: bill_id,
                     const.JSON_ITEM_ID: item_id}
                )
            )
            keyboard.append([item_btn])
        share_all_btn = InlineKeyboardButton(
            text='Share all items',
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_SHARE_ALL_ITEMS,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        keyboard.append([share_all_btn])
        back_btn = InlineKeyboardButton(
            text='Back',
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_MANAGE_BILL_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        keyboard.append([back_btn])
        return InlineKeyboardMarkup(keyboard)


class DisplayPayItemsKB(Action):
    ACTION_DISPLAY_PAY_ITEMS_KB = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_PAY_ITEMS_KB)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DISPLAY_PAY_ITEMS_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            kb = self.get_appropriate_keyboard(
                bill_id, cbq.from_user.id, trans
            )
            return cbq.edit_message_reply_markup(reply_markup=kb)

    @staticmethod
    def get_appropriate_keyboard(bill_id, user_id, trans):
        __, owner_id, __, closed_at = trans.get_bill_gen_info(bill_id)
        if owner_id == user_id:
            return DisplayPayItemsKB.get_pay_items_admin_keyboard(
                bill_id, trans
            )
        else:
            return DisplayPayItemsKB.get_pay_items_keyboard(bill_id, trans)

    @staticmethod
    def get_pay_items_keyboard(self, bill_id, trans):
        keyboard = []
        keyboard.extend(DisplayPayItemsKB.get_payment_buttons(bill_id, trans))
        refresh_btn = InlineKeyboardButton(
            text='Refresh',
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_REFRESH_BILL,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        keyboard.append([refresh_btn])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_pay_items_admin_keyboard(bill_id, trans):
        keyboard = []
        keyboard.extend(DisplayPayItemsKB.get_payment_buttons(bill_id, trans))
        back_btn = InlineKeyboardButton(
            text='Back',
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_MANAGE_BILL_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        keyboard.append([back_btn])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_payment_buttons(bill_id, trans, debts=None):
        kb = []
        if debts is None:
            debts, __ = utils.calculate_remaining_debt(
                bill_id, trans
            )
        for debt in debts:
            credtr = debt['creditor']
            pay_btn = InlineKeyboardButton(
                text='Pay ' + utils.format_name(
                    credtr[3], credtr[1], credtr[2]
                ),
                callback_data=utils.get_action_callback_data(
                    MODULE_ACTION_TYPE,
                    ACTION_PAY_DEBT,
                    {const.JSON_BILL_ID: bill_id,
                     const.JSON_CREDITOR_ID: credtr[0]}
                )
            )
            kb.append([pay_btn])

        return kb


class ShareBillItem(Action):
    ACTION_SHARE_ITEM = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_SHARE_BILL_ITEM)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_SHARE_ITEM:
            print("3. Parsing: " + str(datetime.datetime.now().time()))
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            item_id = data.get(const.JSON_ITEM_ID)

            __, __, __, is_closed = trans.get_bill_gen_info(bill_id)
            if is_closed is not None:
                debts, unique_users = utils.calculate_remaining_debt(
                    bill_id, trans
                )
                text, pm = utils.format_debts_bill_text(
                    bill_id, debts, unique_users, trans
                )
                btns = DisplayPayItemsKB.get_payment_buttons(
                    bill_id, trans, debts=debts
                )
                kb = InlineKeyboardMarkup(btns)
                cbq.answer()
                return cbq.edit_message_text(
                    text=text,
                    parse_mode=pm,
                    reply_markup=kb
                )

            self.share_bill_item(bot, cbq, bill_id, item_id, trans)
            print("7. Sent: " + str(datetime.datetime.now().time()))
            counter.Counter.remove_count()

    def share_bill_item(self, bot, cbq, bill_id, item_id, trans):
        print("4. Toggle share: " + str(datetime.datetime.now().time()))
        trans.toggle_bill_share(bill_id, item_id, cbq.from_user.id)
        print("5. Toggled: " + str(datetime.datetime.now().time()))
        text, pm = utils.get_complete_bill_text(bill_id, trans)
        kb = DisplayShareItemsKB.get_appropriate_keyboard(
            bill_id, cbq.from_user.id, trans
        )
        print("6. Prepared: " + str(datetime.datetime.now().time()))
        cbq.edit_message_text(
            text=text,
            parse_mode=pm,
            reply_markup=kb
        )


class ShareAllItems(Action):
    ACTION_SHARE_ALL = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_SHARE_ALL_ITEMS)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_SHARE_ALL:
            print("3. Parsing: " + str(datetime.datetime.now().time()))
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)

            __, __, __, is_closed = trans.get_bill_gen_info(bill_id)
            if is_closed is not None:
                debts, unique_users = utils.calculate_remaining_debt(
                    bill_id, trans
                )
                text, pm = utils.format_debts_bill_text(
                    bill_id, debts, unique_users, trans
                )
                btns = DisplayPayItemsKB.get_payment_buttons(
                    bill_id, trans, debts=debts
                )
                kb = InlineKeyboardMarkup(btns)
                cbq.answer()
                return cbq.edit_message_text(
                    text=text,
                    parse_mode=pm,
                    reply_markup=kb
                )

            self.share_all_items(bot, cbq, bill_id, trans)
            print("7. Sent: " + str(datetime.datetime.now().time()))
            counter.Counter.remove_count()

    def share_all_items(self, bot, cbq, bill_id, trans):
        print("4. Toggle share: " + str(datetime.datetime.now().time()))
        trans.toggle_all_bill_shares(bill_id, cbq.from_user.id)
        print("5. Toggled: " + str(datetime.datetime.now().time()))
        text, pm = utils.get_complete_bill_text(bill_id, trans)
        kb = DisplayShareItemsKB.get_appropriate_keyboard(
            bill_id, cbq.from_user.id, trans
        )
        print("6. Prepared: " + str(datetime.datetime.now().time()))
        cbq.edit_message_text(
            text=text,
            parse_mode=pm,
            reply_markup=kb
        )


class RefreshBill(Action):
    ACTION_REFRESH_BILL = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_REFRESH_BILL)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_REFRESH_BILL:
            bill_id = data.get(const.JSON_BILL_ID)
            __, __, __, closed_at = trans.get_bill_gen_info(bill_id)
            if closed_at is None:
                return SendCompleteBill().execute(
                    bot, update, trans, data=data
                )
            else:
                return self.refresh_debts_bill(update, trans, data)

    def refresh_debts_bill(self, update, trans, data):
        try:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            txt, pm, kb = SendDebtsBill.get_debts_bill_msg(
                bill_id, cbq.from_user.id, trans
            )
            cbq.answer()
            cbq.edit_message_text(
                text=txt,
                parse_mode=pm,
                reply_markup=kb
            )
        except BadRequest as e:
            print(e)
        except Exception as e:
            logging.exception('RefreshBill')


class CalculateBillSplit(Action):
    ACTION_REQUEST_CONFIRMATION = 0
    ACTION_PROCESS_SPLIT_BILL = 1

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_CALCULATE_SPLIT)

    def execute(self, bot, update, trans, subaction_id, data=None):
        has_rights, chat_id, text = evaluate_rights(update, trans, data)
        if not has_rights:
            if chat_id is not None:
                if update.callback_query is not None:
                    update.callback_query.answer()
                bot.sendMessage(
                    chat_id=chat_id,
                    text=text
                )
            return
        if subaction_id == self.ACTION_REQUEST_CONFIRMATION:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return self.send_confirmation(bot, cbq, bill_id, trans)
        if subaction_id == self.ACTION_PROCESS_SPLIT_BILL:
            return self.process_split_bill(bot, update, trans, data)

    def send_confirmation(self, bot, cbq, bill_id, trans):
        self.set_session(
            cbq.message.chat_id,
            cbq.from_user,
            self.action_type,
            self.action_id,
            self.ACTION_PROCESS_SPLIT_BILL,
            trans,
            data={const.JSON_BILL_ID: bill_id}
        )
        cbq.answer()
        bot.sendMessage(
            chat_id=cbq.message.chat_id,
            text=REQUEST_CALC_SPLIT_CONFIRMATION
        )

    def process_split_bill(self, bot, update, trans, data):
        msg = update.message
        if not Filters.text.filter(msg):
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_CONFIRMATION
            )

        text = msg.text
        try:
            if (text.lower() == YES_WITH_QUOTES or
                    text.lower() == YES):
                return self.split_bill(bot, update, trans, data)
            if (text.lower() == NO_WITH_QUOTES or
                    text.lower() == NO):
                bill_id = data.get(const.JSON_BILL_ID)
                if bill_id is None:
                    raise Exception('bill_id not saved in session')
                return self.send_manage_bill(
                    bot, bill_id, msg.chat_id, msg.from_user.id, trans
                )

            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=ERROR_INVALID_CONFIRMATION
            )
        except Exception as e:
            logging.exception('process_split_bill')

    def send_manage_bill(self, bot, bill_id, chat_id, user_id, trans):
        text, pm = utils.get_complete_bill_text(bill_id, trans)
        keyboard = DisplayManageBillKB.get_manage_bill_keyboard(bill_id, trans)
        trans.reset_session(user_id, chat_id)
        bot.sendMessage(
            chat_id=chat_id,
            text=text,
            parse_mode=pm,
            reply_markup=keyboard
        )

    def split_bill(self, bot, update, trans, data):
        try:
            bill_id = data[const.JSON_BILL_ID]
            bill = trans.get_bill_details(bill_id)
            taxes = bill['taxes']
            tax_amt = 1
            for __, __, amt in taxes:
                tax_amt *= (1 + amt / 100)

            sharers = trans.get_sharers(bill_id)
            items = bill['items']
            debtors = {}
            for item in items:
                item_id, title, price = item
                item_sharers = []
                for i_id, u_id, __, __, __ in sharers:
                    if i_id == item_id:
                        item_sharers.append(u_id)
                if len(item_sharers) == 0:
                    continue
                debt = price * tax_amt / len(item_sharers)
                for sharer in item_sharers:
                    if debtors.get(sharer) is None:
                        debtors[sharer] = debt
                    else:
                        debtors[sharer] += debt

            trans.add_debtors(bill_id, bill['owner_id'], debtors)
            trans.close_bill(bill_id)
            trans.add_payment_by_bill(
                const.PAY_TYPE_NORMAL,
                bill_id,
                bill['owner_id'],
                bill['owner_id'],
                auto_confirm=True
            )
            return SendDebtsBillAdmin().execute(bot, update, trans, data=data)
        except Exception as e:
            logging.exception('split_bill')


class DisplayInspectBillKB(Action):
    ACTION_DISPLAY_INSPECT_BILL_KB = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_INSPECT_BILL_KB)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DISPLAY_INSPECT_BILL_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return cbq.edit_message_reply_markup(
                reply_markup=self.get_inspect_bill_keyboard(bill_id)
            )

    def get_inspect_bill_keyboard(bill_id):
        kb = []
        by_user_btn = InlineKeyboardButton(
            text="Inspect Bill by Person",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_REFRESH_BILL,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        by_item_btn = InlineKeyboardButton(
            text="Inspect Bill by Item",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_REFRESH_BILL,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        back_btn = InlineKeyboardButton(
            text="Inspect Bill by Item",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_REFRESH_BILL,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        kb = [
            [by_user_btn],
            [by_item_btn],
            [back_btn]
        ]
        return InlineKeyboardMarkup(kb)


class DisplayConfirmPaymentsKB(Action):
    ACTION_DISPLAY_PAYMENTS_KB = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_CONFIRM_PAYMENTS_KB)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DISPLAY_PAYMENTS_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            creditor_id = cbq.from_user.id
            return cbq.edit_message_reply_markup(
                reply_markup=self.get_confirm_payments_keyboard(
                    bill_id, creditor_id, trans
                )
            )

    @staticmethod
    def get_confirm_payments_keyboard(bill_id, creditor_id, trans):
        pending = trans.get_pending_payments(bill_id, creditor_id)

        kb = []
        for payment in pending:
            btn = InlineKeyboardButton(
                text='{}  {}{:.4f}'.format(
                    utils.format_name(payment[4], payment[2], payment[3]),
                    const.EMOJI_MONEY_BAG,
                    payment[1],
                ),
                callback_data=utils.get_action_callback_data(
                    MODULE_ACTION_TYPE,
                    ACTION_CONFIRM_BILL_PAYMENT,
                    {const.JSON_BILL_ID: bill_id,
                     const.JSON_PAYMENT_ID: payment[0]}
                )
            )
            kb.append([btn])

        back_btn = InlineKeyboardButton(
            text="Back",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_REFRESH_BILL,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        kb.append([back_btn])
        return InlineKeyboardMarkup(kb)


class SendDebtsBill(Action):
    ACTION_SEND_DEBTS_BILL = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_SEND_DEBTS_BILL)

    def execute(self, bot, update, trans, subaction_id=0, data=None):
        if subaction_id == self.ACTION_SEND_DEBTS_BILL:
            bill_id = data.get(const.JSON_BILL_ID)
            __, owner_id, __, is_closed = trans.get_bill_gen_info(bill_id)

            if not is_closed:
                return

            msg = update.message
            if msg.from_user.id == owner_id:
                return SendDebtsBillAdmin().execute(
                    bot, update, trans, subaction_id, data
                )

            return self.send_debts_bill(bot, bill_id, msg, trans)

    def send_debts_bill(self, bot, bill_id, msg, trans):
        text, pm, kb = self.get_debts_bill_msg(bill_id, msg.from_user.id, trans)
        trans.reset_session(msg.chat_id, msg.from_user.id)
        bot.sendMessage(
            chat_id=msg.chat_id,
            text=text,
            parse_mode=pm,
            reply_markup=kb
        )

    @staticmethod
    def get_debts_bill_msg(bill_id, user_id, trans):
        __, owner_id, __, __ = trans.get_bill_gen_info(bill_id)
        if user_id == owner_id:
            return SendDebtsBillAdmin.get_debts_bill_msg(bill_id, trans)
        debts, unique_users = utils.calculate_remaining_debt(bill_id, trans)
        text, pm = utils.format_debts_bill_text(
            bill_id, debts, unique_users, trans
        )
        kb = DisplayPayItemsKB.get_payment_buttons(bill_id, trans, debts=debts)
        return text, pm, InlineKeyboardMarkup(kb)


class SendDebtsBillAdmin(Action):
    ACTION_SEND_DEBTS_BILL = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_SEND_DEBTS_BILL_ADMIN)

    def execute(self, bot, update, trans, subaction_id=0, data=None):
        if subaction_id == self.ACTION_SEND_DEBTS_BILL:
            bill_id = data.get(const.JSON_BILL_ID)
            msg = update.message
            self.send_debts_bill(bot, bill_id, msg, trans)

    def send_debts_bill(self, bot, bill_id, msg, trans):
        text, pm, kb = self.get_debts_bill_msg(bill_id, trans)
        trans.reset_session(msg.chat_id, msg.from_user.id)
        bot.sendMessage(
            chat_id=msg.chat_id,
            text=text,
            parse_mode=pm,
            reply_markup=kb
        )

    @staticmethod
    def get_debts_bill_msg(bill_id, trans):
        bill_name, __, __, __ = trans.get_bill_gen_info(bill_id)
        share_btn = InlineKeyboardButton(
            text="Share Bill",
            switch_inline_query=bill_name
        )
        refresh_btn = InlineKeyboardButton(
            text="Refresh Bill",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_REFRESH_BILL,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        confirm_btn = InlineKeyboardButton(
            text="Confirm Payments",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_CONFIRM_PAYMENTS_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        kb = InlineKeyboardMarkup(
            [[share_btn],
             [refresh_btn],
             [confirm_btn]]
        )
        text, pm = utils.get_debts_bill_text(bill_id, trans)
        return text, pm, kb


class PayDebt(Action):
    ACTION_PAY_DEBT = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_PAY_DEBT)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_PAY_DEBT:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            creditor_id = data.get(const.JSON_CREDITOR_ID)
            self.pay_debt(bot, cbq, bill_id, creditor_id, trans)
            RefreshBill().execute(bot, update, trans, 0, data)

    def pay_debt(self, bot, cbq, bill_id, creditor_id, trans):
        trans.add_payment_by_bill(
            const.PAY_TYPE_NORMAL,
            bill_id,
            creditor_id,
            cbq.from_user.id
        )


class ConfirmPayment(Action):
    ACTION_CONFIRM_PAYMENT = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_CONFIRM_BILL_PAYMENT)

    def execute(self, bot, update, trans, subaction_id=0, data=None):
        if subaction_id == self.ACTION_CONFIRM_PAYMENT:
            bill_id = data.get(const.JSON_BILL_ID)
            payment_id = data.get(const.JSON_PAYMENT_ID)
            self.confirm_payment(
                bot, bill_id, payment_id, update.callback_query, trans
            )

    def confirm_payment(self, bot, bill_id, payment_id, cbq, trans):
        trans.confirm_payment(payment_id)
        text, pm = utils.get_debts_bill_text(bill_id, trans)
        kb = DisplayConfirmPaymentsKB.get_confirm_payments_keyboard(
            bill_id, cbq.from_user.id, trans
        )
        cbq.answer()
        cbq.edit_message_text(
            text=text,
            parse_mode=pm,
            reply_markup=kb
        )


def evaluate_rights(update, trans, data):
    if data is None:
        return True, None, None
    bill_id = data.get(const.JSON_BILL_ID)
    if bill_id is None:
        return True, None, None

    __, owner_id, __, is_closed = trans.get_bill_gen_info(bill_id)
    chat_id = None
    if update.callback_query is not None:
        has_rights = update.callback_query.from_user.id == owner_id
        chat_id = update.callback_query.message.chat_id
        if not has_rights:
            update.callback_query.answer()
            return has_rights, chat_id, 'Sorry, you do not have permission for this action.'

    if chat_id is None and update.message is not None:
        has_rights = update.message.from_user.id == owner_id
        chat_id = update.message.chat_id
        if not has_rights:
            return has_rights, chat_id, 'Sorry, you do not have permission for this action.'

    if is_closed is not None:
        return False, chat_id, 'Sorry, bill is already calculated and closed.'

    return True, None, None
