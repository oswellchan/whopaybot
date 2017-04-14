from action_handlers.action_handler import ActionHandler, Action
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.inlinekeyboardbutton import InlineKeyboardButton
import constants as const
import utils

MODULE_ACTION_TYPE = const.TYPE_SHARE_BILL

ACTION_FIND_BILLS = 0
ACTION_REFRESH_SHARE_BILL = 1


class BillShareHandler(ActionHandler):
    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE)

    def execute(self, bot, update, trans, action_id,
                subaction_id=0, data=None):
        action = None
        if action_id == ACTION_FIND_BILLS:
            action = FindBills()
        if action_id == ACTION_REFRESH_SHARE_BILL:
            action = RefreshShareBill()
        action.execute(bot, update, trans, subaction_id, data)


class FindBills(Action):
    ACTION_FIND_BILL = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_FIND_BILLS)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_FIND_BILL:
            iq = update.inline_query
            return self.find_bills(bot, iq, trans)

    def find_bills(self, bot, iq, trans):
        query = iq.query
        if not query:
            return
        bill_ids = trans.get_bill_details_by_name(query, iq.from_user.id)
        results = []
        for bill_id, closed_at in bill_ids:
            result = None
            if closed_at is None:
                result = self.get_sharing_bill_result(bill_id, trans)
            else:
                result = self.get_debt_bill_result(bill_id, trans)

            if result is not None:
                results.append(result)

        iq.answer(results)

    @staticmethod
    def get_sharing_bill_result(bill_id, trans):
        details = trans.get_bill_details(bill_id)
        msg = utils.format_complete_bill_text(details, bill_id, trans)
        if msg is None:
            return
        kb = get_redirect_share_keyboard(bill_id)
        return InlineQueryResultArticle(
            id=bill_id,
            title=details.get('title'),
            input_message_content=InputTextMessageContent(
                msg[0],
                parse_mode=msg[1]
            ),
            reply_markup=kb,
            description='{}\nItems: {}'.format(
                utils.format_time(details.get('time')),
                str(len(details.get('items')))
            )
        )

    @staticmethod
    def get_debt_bill_result(bill_id, trans):
        details = trans.get_bill_details(bill_id)
        debts, unique_users = utils.calculate_remaining_debt(bill_id, trans)
        text, pm = utils.format_debts_bill_text(
            bill_id, debts, unique_users, trans
        )
        kb = get_redirect_pay_keyboard(bill_id)
        return InlineQueryResultArticle(
            id=bill_id,
            title=details.get('title'),
            input_message_content=InputTextMessageContent(
                text,
                parse_mode=pm
            ),
            reply_markup=kb,
            description='{}\nItems: {}'.format(
                utils.format_time(details.get('time')),
                str(len(details.get('items')))
            )
        )


class RefreshShareBill(Action):
    ACTION_REFRESH_SHARE_BILL = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_REFRESH_SHARE_BILL)

    def execute(self, bot, update, trans, subaction_id, data=None):
        cbq = update.callback_query
        bill_id = data.get(const.JSON_BILL_ID)
        if subaction_id == self.ACTION_REFRESH_SHARE_BILL:
            __, __, __, is_closed = trans.get_bill_gen_info(bill_id)

            if is_closed is None:
                self.refresh_share_bill(bill_id, cbq, trans)
            else:
                self.refresh_debt_bill(bill_id, cbq, trans)

    def refresh_share_bill(self, bill_id, cbq, trans):
        details = trans.get_bill_details(bill_id)
        text, pm = utils.format_complete_bill_text(details, bill_id, trans)
        kb = get_redirect_share_keyboard(bill_id)
        cbq.answer()
        cbq.edit_message_text(
            text=text,
            parse_mode=pm,
            reply_markup=kb
        )

    def refresh_debt_bill(self, bill_id, cbq, trans):
        debts, unique_users = utils.calculate_remaining_debt(bill_id, trans)
        text, pm = utils.format_debts_bill_text(
            bill_id, debts, unique_users, trans
        )
        kb = get_redirect_pay_keyboard(bill_id)
        cbq.answer()
        cbq.edit_message_text(
            text=text,
            parse_mode=pm,
            reply_markup=kb
        )


class PayDebt(Action):
    ACTION_PAY_DEBT = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_PAY_DEBT)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_PAY_DEBT:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            creditor_id = data.get(const.JSON_CREDITOR_ID)
            return self.pay_debt(bot, cbq, bill_id, creditor_id, trans)

    def pay_debt(self, bot, cbq, bill_id, creditor_id, trans):
        trans.add_payment_by_bill(
            const.PAY_TYPE_NORMAL,
            bill_id,
            creditor_id,
            cbq.from_user.id
        )
        debts, unique_users = utils.calculate_remaining_debt(
            bill_id, trans
        )
        text, pm = utils.format_debts_bill_text(
            bill_id, debts, unique_users, trans
        )
        kb = get_payment_keyboard(bill_id, debts)
        cbq.answer()
        cbq.edit_message_text(
            text=text,
            parse_mode=pm,
            reply_markup=kb
        )


def get_redirect_share_keyboard(bill_id):
    refresh_btn = InlineKeyboardButton(
        text='Refresh',
        callback_data=utils.get_action_callback_data(
            MODULE_ACTION_TYPE,
            ACTION_REFRESH_SHARE_BILL,
            {const.JSON_BILL_ID: bill_id}
        )
    )
    inspect_btn = InlineKeyboardButton(
        text='Share items',
        url='https://telegram.me/WhoPayBot?start=' + bill_id
    )

    return InlineKeyboardMarkup([
        [refresh_btn],
        [inspect_btn]
    ])


def get_redirect_pay_keyboard(bill_id):
    refresh_btn = InlineKeyboardButton(
        text='Refresh',
        callback_data=utils.get_action_callback_data(
            MODULE_ACTION_TYPE,
            ACTION_REFRESH_SHARE_BILL,
            {const.JSON_BILL_ID: bill_id}
        )
    )
    inspect_btn = InlineKeyboardButton(
        text='Pay Debts',
        url='https://telegram.me/WhoPayBot?start=' + bill_id
    )

    return InlineKeyboardMarkup([
        [refresh_btn],
        [inspect_btn]
    ])


def is_closed(bill_id, trans):
    __, __, __, is_closed = trans.get_bill_gen_info(bill_id)

    if is_closed is not None:
        return False

    return True
