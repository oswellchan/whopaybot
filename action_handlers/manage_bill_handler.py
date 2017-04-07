from action_handlers.action_handler import ActionHandler, Action
from telegram.ext import Filters
from telegram.parsemode import ParseMode
from telegram.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.inlinekeyboardbutton import InlineKeyboardButton
import constants as const
import utils

MODULE_ACTION_TYPE = const.TYPE_MANAGE_BILL

ACTION_GET_MANAGE_BILL = 0
ACTION_GET_MANAGE_BILL_KB = 1
ACTION_SHARE_BILL = 2
ACTION_CALCULATE_SPLIT = 3
ACTION_REFRESH_BILL = 4
ACTION_SEND_DEBTS_BILL_ADMIN = 5
ACTION_CONFIRM_BILL_PAYMENT = 6

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
        if action_id == ACTION_GET_MANAGE_BILL:
            action = SendCompleteBill()
        if action_id == ACTION_REFRESH_BILL:
            action = RefreshBill()
        if action_id == ACTION_CALCULATE_SPLIT:
            action = CalculateBillSplit()
        action.execute(bot, update, trans, subaction_id, data)


class SendCompleteBill(Action):
    ACTION_MANAGE_BILL = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_MANAGE_BILL)

    def execute(self, bot, update, trans, subaction_id=0, data=None):
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
        if subaction_id == self.ACTION_MANAGE_BILL:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return self.send_bill_response(bot, cbq, bill_id, trans)

    def send_bill_response(self, bot, cbq, bill_id, trans):
        chat_id = cbq.message.chat_id
        text, pm = utils.get_complete_bill_text(bill_id, trans)
        keyboard = DisplayManageBillKB.get_manage_bill_keyboard(bill_id, trans)
        trans.reset_session(cbq.from_user.id, chat_id)
        cbq.answer()
        cbq.edit_message_text(
            text=text,
            parse_mode=pm,
            reply_markup=keyboard
        )


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
             [calc_bill_btn]]
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
        bill_id = data.get(const.JSON_BILL_ID)
        txt, pm, kb = SendDebtsBillAdmin.get_debts_bill_msg(bill_id, trans)
        update.callback_query.answer()
        update.callback_query.edit_message_text(
            text=txt,
            parse_mode=pm,
            reply_markup=kb
        )


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
            print(e)

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
            print(e)


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
                ACTION_CONFIRM_BILL_PAYMENT,
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
