from action_handlers.action_handler import ActionHandler, Action
from telegram.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.inlinekeyboardbutton import InlineKeyboardButton
from telegram.ext import Filters
from telegram.parsemode import ParseMode
from telegram.error import BadRequest
import constants as const
import utils
import datetime
import logging
import counter
import math
import random

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
ACTION_GET_FORCE_CONFIRM_PAYMENTS_KB = 16
ACTION_FORCE_CONFIRM_PAYMENT = 17
ACTION_ADD_SOMEONE = 18

REQUEST_CALC_SPLIT_CONFIRMATION = "You are about to calculate the splitting of the bill. Once this is done, no new person can be added to the bill anymore. Do you wish to continue? Reply /yes or /no."
ERROR_INVALID_CONTACT = "Sorry, invalid Contact or name sent. Name can only be 250 characters long. Please try again."
REQUEST_PAY_CONFIRMATION = "You are about to confirm <b>{}'s</b> payment of {}{:.2f}. This action is irreversible. Do you wish to continue? Reply /yes or /no."
REQUEST_FORCE_PAY_CONFIRMATION = "You are about to forcibly confirm <b>{}'s</b> payment of {}{:.2f}. This person has not indicated payment yet. This action is irreversible. Do you wish to continue? Reply /yes or /no."
REQUEST_CONTACT = "Please send me the <b>Contact</b> or name of the person. However, this person might <b>not</b> be able to indicate payment for this bill later on. You will have to force confirm his/her payment. To stop this, reply /no."
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
        if action_id == ACTION_FORCE_CONFIRM_PAYMENT:
            action = ForceConfirmPayment()
        if action_id == ACTION_GET_FORCE_CONFIRM_PAYMENTS_KB:
            action = DisplayForceConfirmPaymentsKB()
        if action_id == ACTION_ADD_SOMEONE:
            action = AddSomeone()

        action.execute(bot, update, trans, subaction_id, data)

    def execute_yes(self, bot, update, trans, action_id,
                    subaction_id=0, data=None):
        action = None
        if action_id == ACTION_CONFIRM_BILL_PAYMENT:
            action = ConfirmPayment()
        if action_id == ACTION_CALCULATE_SPLIT:
            action = CalculateBillSplit()
        if action_id == ACTION_FORCE_CONFIRM_PAYMENT:
            action = ForceConfirmPayment()

        action.yes(bot, update, trans, subaction_id, data)

    def execute_no(self, bot, update, trans, action_id,
                   subaction_id=0, data=None):
        action = None
        if action_id == ACTION_CONFIRM_BILL_PAYMENT:
            action = ConfirmPayment()
        if action_id == ACTION_CALCULATE_SPLIT:
            action = CalculateBillSplit()
        if action_id == ACTION_FORCE_CONFIRM_PAYMENT:
            action = ForceConfirmPayment()
        if action_id == ACTION_ADD_SOMEONE:
            action = AddSomeone()

        action.no(bot, update, trans, subaction_id, data)


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
            kb = DisplayManageBillKB.get_manage_bill_keyboard(
                bill_id, trans
            )
        else:
            kb = DisplayShareItemsKB.get_share_items_keyboard(
                bill_id, trans, user_id
            )
        return text, pm, kb

    def send_bill_response(self, bot, cbq, bill_id, trans):
        try:
            chat_id = cbq.message.chat_id
            text, pm, kb = self.get_appropriate_response(
                bill_id, cbq.from_user.id, trans
            )
            trans.reset_session(chat_id, cbq.from_user.id)
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
            text="📮 Share Bill for Collaboration",
            switch_inline_query=bill_name
        )
        refresh_btn = InlineKeyboardButton(
            text="🔄 Refresh Bill",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_REFRESH_BILL,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        share_items = InlineKeyboardButton(
            text="🙋 Add yourself to Item(s)",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_SHARE_ITEMS_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        share_else_items = InlineKeyboardButton(
            text="💁 Add someone to Item(s)",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_ADD_SOMEONE,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        calc_bill_btn = InlineKeyboardButton(
            text="⚖ Calculate Split",
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
             [share_else_items],
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
    def get_appropriate_keyboard(bill_id, user_id, trans, proxy_uid=None):
        if proxy_uid is None:
            proxy_uid = user_id
        __, owner_id, __, closed_at = trans.get_bill_gen_info(bill_id)
        if owner_id == proxy_uid:
            return DisplayShareItemsKB.get_share_items_admin_keyboard(
                bill_id, trans, user_id
            )
        else:
            return DisplayShareItemsKB.get_share_items_keyboard(
                bill_id, trans, user_id
            )

    @staticmethod
    def get_share_items_keyboard(bill_id, trans, user_id):
        keyboard = []
        items = trans.get_bill_items(bill_id)
        refresh_btn = InlineKeyboardButton(
            text='🔄 Refresh',
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_REFRESH_BILL,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        keyboard.append([refresh_btn])
        for item_id, item_name, __ in items:
            if trans.has_bill_share(bill_id, item_id, user_id):
                text = "👋 Unshare " + item_name
            else:
                text = '☝️ Share ' + item_name
            item_btn = InlineKeyboardButton(
                text=text,
                callback_data=utils.get_action_callback_data(
                    MODULE_ACTION_TYPE,
                    ACTION_SHARE_BILL_ITEM,
                    {const.JSON_ITEM_ID: item_id,
                     const.JSON_USER_ID: user_id}
                )
            )
            keyboard.append([item_btn])

        text = "🙅 Unshare all items"
        for item_id, item_name, __ in items:
            if not trans.has_bill_share(bill_id, item_id, user_id):
                text = '🙌 Share all items'
                break

        share_all_btn = InlineKeyboardButton(
            text=text,
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_SHARE_ALL_ITEMS,
                {const.JSON_BILL_ID: bill_id,
                 const.JSON_USER_ID: user_id}
            )
        )
        keyboard.append([share_all_btn])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_share_items_admin_keyboard(bill_id, trans, user_id):
        keyboard = []
        items = trans.get_bill_items(bill_id)
        for item_id, item_name, __ in items:
            if trans.has_bill_share(bill_id, item_id, user_id):
                text = "👋 Unshare " + item_name
            else:
                text = '☝️ Share ' + item_name
            item_btn = InlineKeyboardButton(
                text=text,
                callback_data=utils.get_action_callback_data(
                    MODULE_ACTION_TYPE,
                    ACTION_SHARE_BILL_ITEM,
                    {const.JSON_ITEM_ID: item_id,
                     const.JSON_USER_ID: user_id}
                )
            )
            keyboard.append([item_btn])

        text = "🙅 Unshare all items"
        for item_id, item_name, __ in items:
            if not trans.has_bill_share(bill_id, item_id, user_id):
                text = '🙌 Share all items'
                break

        share_all_btn = InlineKeyboardButton(
            text=text,
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_SHARE_ALL_ITEMS,
                {const.JSON_BILL_ID: bill_id,
                 const.JSON_USER_ID: user_id}
            )
        )
        keyboard.append([share_all_btn])
        back_btn = InlineKeyboardButton(
            text='🔙 Back',
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
                bill_id, user_id, trans
            )
        else:
            return DisplayPayItemsKB.get_pay_items_keyboard(
                bill_id, user_id, trans
            )

    @staticmethod
    def get_pay_items_keyboard(self, bill_id, user_id, trans):
        keyboard = []
        keyboard.extend(DisplayPayItemsKB.get_payment_buttons(
            bill_id, user_id, trans
        ))
        refresh_btn = InlineKeyboardButton(
            text='🔄 Refresh',
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_REFRESH_BILL,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        keyboard.append([refresh_btn])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_pay_items_admin_keyboard(bill_id, user_id, trans):
        keyboard = []
        keyboard.extend(DisplayPayItemsKB.get_payment_buttons(
            bill_id, user_id, trans
        ))
        back_btn = InlineKeyboardButton(
            text='🔙 Back',
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_MANAGE_BILL_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        keyboard.append([back_btn])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_payment_buttons(bill_id, user_id, trans, debts=None):
        kb = []
        if debts is None:
            debts, __ = utils.calculate_remaining_debt(
                bill_id, trans
            )
        for debt in debts:
            text = '💸 Pay '
            for debtor in debt['debtors']:
                if (debtor['debtor'][0] == user_id and
                        debtor['status'] == '(Pending)'):
                    text = '💰 Unpay '
                    break

            credtr = debt['creditor']
            refresh_btn = InlineKeyboardButton(
                text="🔄 Refresh Bill",
                callback_data=utils.get_action_callback_data(
                    MODULE_ACTION_TYPE,
                    ACTION_REFRESH_BILL,
                    {const.JSON_BILL_ID: bill_id}
                )
            )
            pay_btn = InlineKeyboardButton(
                text=text + utils.format_name(
                    credtr[3], credtr[1], credtr[2]
                ),
                callback_data=utils.get_action_callback_data(
                    MODULE_ACTION_TYPE,
                    ACTION_PAY_DEBT,
                    {const.JSON_BILL_ID: bill_id,
                     const.JSON_CREDITOR_ID: credtr[0]}
                )
            )
            kb.append([refresh_btn])
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
            item_id = data.get(const.JSON_ITEM_ID)
            bill_id = trans.get_bill_id_of_item(item_id)

            __, __, __, is_closed = trans.get_bill_gen_info(bill_id)
            if is_closed is not None:
                debts, unique_users = utils.calculate_remaining_debt(
                    bill_id, trans
                )
                text, pm = utils.format_debts_bill_text(
                    bill_id, debts, unique_users, trans
                )
                btns = DisplayPayItemsKB.get_payment_buttons(
                    bill_id, cbq.from_user.id, trans, debts=debts
                )
                kb = InlineKeyboardMarkup(btns)
                cbq.answer()
                return cbq.edit_message_text(
                    text=text,
                    parse_mode=pm,
                    reply_markup=kb
                )

            user_id = data.get(const.JSON_USER_ID)
            if user_id is None:
                raise Exception('Missing user_id')
            self.share_bill_item(bot, cbq, bill_id, item_id, user_id, trans)
            print("7. Sent: " + str(datetime.datetime.now().time()))
            counter.Counter.remove_count()

    @staticmethod
    def share_bill_item(bot, cbq, bill_id, item_id, user_id, trans):
        print("4. Toggle share: " + str(datetime.datetime.now().time()))
        trans.toggle_bill_share(bill_id, item_id, user_id)
        print("5. Toggled: " + str(datetime.datetime.now().time()))
        text, pm = utils.get_complete_bill_text(bill_id, trans)
        kb = DisplayShareItemsKB.get_appropriate_keyboard(
            bill_id, user_id, trans, proxy_uid=cbq.from_user.id
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
                    bill_id, cbq.from_user.id, trans, debts=debts
                )
                kb = InlineKeyboardMarkup(btns)
                cbq.answer()
                return cbq.edit_message_text(
                    text=text,
                    parse_mode=pm,
                    reply_markup=kb
                )

            user_id = data.get(const.JSON_USER_ID)
            if user_id is None:
                raise Exception('Missing user_id')
            self.share_all_items(bot, cbq, bill_id, user_id, trans)
            print("7. Sent: " + str(datetime.datetime.now().time()))
            counter.Counter.remove_count()

    def share_all_items(self, bot, cbq, bill_id, user_id, trans):
        print("4. Toggle share: " + str(datetime.datetime.now().time()))
        trans.toggle_all_bill_shares(bill_id, user_id)
        print("5. Toggled: " + str(datetime.datetime.now().time()))
        text, pm = utils.get_complete_bill_text(bill_id, trans)
        kb = DisplayShareItemsKB.get_appropriate_keyboard(
            bill_id, user_id, trans, proxy_uid=cbq.from_user.id
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

    def yes(self, bot, update, trans, subaction_id, data=None):
        return self.split_bill(bot, update, trans, data)

    def no(self, bot, update, trans, subaction_id, data=None):
        msg = update.message
        bill_id = data.get(const.JSON_BILL_ID)
        return self.send_manage_bill(
            bot, bill_id, msg.chat_id, msg.from_user.id, trans
        )

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

    def send_manage_bill(self, bot, bill_id, chat_id, user_id, trans):
        text, pm = utils.get_complete_bill_text(bill_id, trans)
        keyboard = DisplayManageBillKB.get_manage_bill_keyboard(bill_id, trans)
        trans.reset_session(chat_id, user_id)
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

                num_sharers = len(item_sharers)
                # convert to cents
                item_amount = math.floor(price * tax_amt * 100)
                debt = item_amount // num_sharers
                remainder = item_amount % num_sharers

                # get random users to get remainder
                selected = random.sample(range(num_sharers), remainder)
                for i, sharer in enumerate(item_sharers):
                    amt_to_pay = debt
                    if i in selected:
                        amt_to_pay += 1
                    if debtors.get(sharer) is None:
                        debtors[sharer] = amt_to_pay / 100
                    else:
                        debtors[sharer] += amt_to_pay / 100

            trans.add_debtors(bill_id, bill['owner_id'], debtors)
            trans.close_bill(bill_id)
            for debtor_id, amt in debtors.items():
                auto_confirm = debtor_id == bill['owner_id']
                is_deleted = debtor_id != bill['owner_id']
                trans.add_payment_by_bill(
                    const.PAY_TYPE_NORMAL,
                    bill_id,
                    bill['owner_id'],
                    debtor_id,
                    auto_confirm=auto_confirm,
                    is_deleted=is_deleted
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
                text='✅ {}  {}{:.2f}'.format(
                    utils.format_name(payment[5], payment[3], payment[4]),
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
            text="🔙 Back",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_REFRESH_BILL,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        kb.append([back_btn])
        return InlineKeyboardMarkup(kb)


class DisplayForceConfirmPaymentsKB(Action):
    ACTION_DISPLAY_PAYMENTS_KB = 0

    def __init__(self):
        super().__init__(
            MODULE_ACTION_TYPE,
            ACTION_GET_FORCE_CONFIRM_PAYMENTS_KB
        )

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_DISPLAY_PAYMENTS_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            creditor_id = cbq.from_user.id
            return cbq.edit_message_reply_markup(
                reply_markup=self.get_force_confirm_payments_keyboard(
                    bill_id, creditor_id, trans
                )
            )

    @staticmethod
    def get_force_confirm_payments_keyboard(bill_id, creditor_id, trans):
        unpaid = trans.get_unpaid_payments(bill_id, creditor_id)

        kb = []
        for payment in unpaid:
            btn = InlineKeyboardButton(
                text='✅ {}  {}{:.2f}'.format(
                    utils.format_name(payment[5], payment[3], payment[4]),
                    const.EMOJI_MONEY_BAG,
                    payment[1],
                ),
                callback_data=utils.get_action_callback_data(
                    MODULE_ACTION_TYPE,
                    ACTION_FORCE_CONFIRM_PAYMENT,
                    {const.JSON_BILL_ID: bill_id,
                     const.JSON_PAYMENT_ID: payment[0]}
                )
            )
            kb.append([btn])

        back_btn = InlineKeyboardButton(
            text="🔙 Back",
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
        kb = DisplayPayItemsKB.get_payment_buttons(
            bill_id, user_id, trans, debts=debts
        )
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
            text="📮 Share Bill",
            switch_inline_query=bill_name
        )
        refresh_btn = InlineKeyboardButton(
            text="🔄 Refresh Bill",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_REFRESH_BILL,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        confirm_btn = InlineKeyboardButton(
            text="🤑 Confirm Payments",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_CONFIRM_PAYMENTS_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        f_confirm_btn = InlineKeyboardButton(
            text="😵 Force Confirm Payments",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_GET_FORCE_CONFIRM_PAYMENTS_KB,
                {const.JSON_BILL_ID: bill_id}
            )
        )
        kb = InlineKeyboardMarkup(
            [[share_btn],
             [refresh_btn],
             [confirm_btn],
             [f_confirm_btn]]
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
    ACTION_REQUEST_CONFIRMATION = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_CONFIRM_BILL_PAYMENT)

    def execute(self, bot, update, trans, subaction_id=0, data=None):
        if subaction_id == self.ACTION_REQUEST_CONFIRMATION:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            payment_id = data.get(const.JSON_PAYMENT_ID)
            return self.send_confirmation(bot, cbq, bill_id, payment_id, trans)

    def send_confirmation(self, bot, cbq, bill_id, payment_id, trans):
        self.set_session(
            cbq.message.chat_id,
            cbq.from_user,
            self.action_type,
            self.action_id,
            0,
            trans,
            data={const.JSON_BILL_ID: bill_id,
                  const.JSON_PAYMENT_ID: payment_id}
        )
        amt, fname, lname, uname = trans.get_payment(payment_id)
        cbq.answer()
        bot.sendMessage(
            chat_id=cbq.message.chat_id,
            text=REQUEST_PAY_CONFIRMATION.format(
                utils.escape_html(
                    utils.format_name(uname, fname, lname)
                ),
                const.EMOJI_MONEY_BAG,
                amt
            ),
            parse_mode=ParseMode.HTML
        )

    def yes(self, bot, update, trans, subaction_id, data=None):
        bill_id = data.get(const.JSON_BILL_ID)
        payment_id = data.get(const.JSON_PAYMENT_ID)
        self.confirm_payment(
            bot, bill_id, payment_id, update.message, trans
        )

    def no(self, bot, update, trans, subaction_id, data=None):
        return SendDebtsBill().execute(bot, update, trans, 0, data)

    def confirm_payment(self, bot, bill_id, payment_id, msg, trans):
        trans.confirm_payment(payment_id)
        text, pm = utils.get_debts_bill_text(bill_id, trans)
        kb = DisplayConfirmPaymentsKB.get_confirm_payments_keyboard(
            bill_id, msg.from_user.id, trans
        )
        trans.reset_session(msg.chat_id, msg.from_user.id)
        bot.sendMessage(
            chat_id=msg.chat_id,
            text=text,
            parse_mode=pm,
            reply_markup=kb
        )


class ForceConfirmPayment(Action):
    ACTION_REQUEST_CONFIRMATION = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_FORCE_CONFIRM_PAYMENT)

    def execute(self, bot, update, trans, subaction_id=0, data=None):
        if subaction_id == self.ACTION_REQUEST_CONFIRMATION:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            payment_id = data.get(const.JSON_PAYMENT_ID)
            return self.send_confirmation(bot, cbq, bill_id, payment_id, trans)

    def send_confirmation(self, bot, cbq, bill_id, payment_id, trans):
        self.set_session(
            cbq.message.chat_id,
            cbq.from_user,
            self.action_type,
            self.action_id,
            0,
            trans,
            data={const.JSON_BILL_ID: bill_id,
                  const.JSON_PAYMENT_ID: payment_id}
        )
        amt, fname, lname, uname = trans.get_payment(payment_id)
        cbq.answer()
        bot.sendMessage(
            chat_id=cbq.message.chat_id,
            text=REQUEST_FORCE_PAY_CONFIRMATION.format(
                utils.escape_html(
                    utils.format_name(uname, fname, lname)
                ),
                const.EMOJI_MONEY_BAG,
                amt
            ),
            parse_mode=ParseMode.HTML
        )

    def yes(self, bot, update, trans, subaction_id, data=None):
        bill_id = data.get(const.JSON_BILL_ID)
        payment_id = data.get(const.JSON_PAYMENT_ID)
        self.force_confirm_payment(
            bot, bill_id, payment_id, update.message, trans
        )

    def no(self, bot, update, trans, subaction_id, data=None):
        return SendDebtsBill().execute(bot, update, trans, 0, data)

    def force_confirm_payment(self, bot, bill_id, payment_id, msg, trans):
        trans.force_confirm_payment(payment_id)
        text, pm = utils.get_debts_bill_text(bill_id, trans)
        kb = DisplayForceConfirmPaymentsKB.get_force_confirm_payments_keyboard(
            bill_id, msg.from_user.id, trans
        )
        trans.reset_session(msg.chat_id, msg.from_user.id)
        bot.sendMessage(
            chat_id=msg.chat_id,
            text=text,
            parse_mode=pm,
            reply_markup=kb
        )


class AddSomeone(Action):
    ACTION_REQUEST_CONTACT = 0
    ACTION_DISPLAY_ITEMS = 1

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_ADD_SOMEONE)

    def execute(self, bot, update, trans, subaction_id=0, data=None):
        has_rights, chat_id, text = evaluate_rights(update, trans, data)
        if not has_rights:
            if chat_id is not None:
                if update.callback_query is not None:
                    update.callback_query.answer()
                return bot.sendMessage(
                    chat_id=chat_id,
                    text=text
                )

        bill_id = data.get(const.JSON_BILL_ID)
        if subaction_id == self.ACTION_REQUEST_CONTACT:
            cbq = update.callback_query
            return self.request_contact(bot, cbq, bill_id, trans)
        if subaction_id == self.ACTION_DISPLAY_ITEMS:
            return self.send_items_list(bot, update.message, bill_id, trans)

    def no(self, bot, update, trans, subaction_id, data=None):
        return SendBill().execute(bot, update, trans, subaction_id, data)

    def request_contact(self, bot, cbq, bill_id, trans):
        self.set_session(
            cbq.message.chat_id,
            cbq.from_user,
            self.action_type,
            self.action_id,
            self.ACTION_DISPLAY_ITEMS,
            trans,
            data={const.JSON_BILL_ID: bill_id}
        )
        cbq.answer()
        bot.sendMessage(
            chat_id=cbq.message.chat_id,
            text=REQUEST_CONTACT,
            parse_mode=ParseMode.HTML
        )

    def send_items_list(self, bot, msg, bill_id, trans):
        try:
            is_valid = False
            user_id = 0
            fname = None
            lname = None
            if Filters.contact.filter(msg):
                is_valid = True
                contact = msg.contact
                if contact is None:
                    raise Exception(ERROR_INVALID_CONTACT)
                user_id = contact.user_id
                fname = contact.first_name
                lname = contact.last_name

            if Filters.text.filter(msg):
                is_valid = True
                text = msg.text
                if (text is None or len(text) < 1 or len(text) > 250):
                    Exception(ERROR_INVALID_CONTACT)
                fname = text

            if not is_valid:
                raise Exception(ERROR_INVALID_CONTACT)

            user_id = trans.add_user(
                user_id,
                fname,
                lname,
                None,
                is_ignore_id=(user_id == 0)
            )

            text, pm = utils.get_complete_bill_text(bill_id, trans)
            kb = DisplayShareItemsKB.get_appropriate_keyboard(
                bill_id, user_id, trans, proxy_uid=msg.from_user.id
            )
            bot.sendMessage(
                chat_id=msg.chat_id,
                text=text,
                parse_mode=pm,
                reply_markup=kb
            )
            trans.reset_session(msg.chat_id, msg.from_user.id)
        except Exception as e:
            return bot.sendMessage(
                chat_id=msg.chat_id,
                text=str(e)
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
