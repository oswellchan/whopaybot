from action_handlers.action_handler import ActionHandler, Action
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.inlinekeyboardbutton import InlineKeyboardButton
import constants as const
import utils
import datetime
import counter

MODULE_ACTION_TYPE = const.TYPE_SHARE_BILL

ACTION_FIND_BILLS = 0
ACTION_SHARE_BILL_ITEM = 1
ACTION_SHARE_ALL_ITEMS = 2
ACTION_PAY_DEBT = 3
ACTION_INSPECT_BILL = 4


class BillShareHandler(ActionHandler):
    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE)

    def execute(self, bot, update, trans, action_id,
                subaction_id=0, data=None):
        action = None
        if action_id == ACTION_FIND_BILLS:
            action = FindBills()
        if action_id == ACTION_SHARE_BILL_ITEM:
            action = ShareBillItem()
        if action_id == ACTION_SHARE_ALL_ITEMS:
            action = ShareAllItems()
        if action_id == ACTION_PAY_DEBT:
            action = PayDebt()
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

    def get_sharing_bill_result(self, bill_id, trans):
        details = trans.get_bill_details(bill_id)
        msg = utils.format_complete_bill_text(details, bill_id, trans)
        if msg is None:
            return
        kb = get_share_keyboard(bill_id, ACTION_SHARE_BILL_ITEM, trans)
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

    def get_debt_bill_result(self, bill_id, trans):
        details = trans.get_bill_details(bill_id)
        debts, unique_users = utils.calculate_remaining_debt(bill_id, trans)
        text, pm = utils.format_debts_bill_text(
            bill_id, debts, unique_users, trans
        )
        kb = get_payment_keyboard(bill_id, debts)
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

            if not has_rights(trans, data):
                debts, unique_users = utils.calculate_remaining_debt(
                    bill_id, trans
                )
                text, pm = utils.format_debts_bill_text(
                    bill_id, debts, unique_users, trans
                )
                kb = get_payment_keyboard(bill_id, debts)
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
        kb = get_share_keyboard(bill_id, ACTION_SHARE_BILL_ITEM, trans)
        print("6. Prepared: " + str(datetime.datetime.now().time()))
        cbq.edit_message_text(
            text=text,
            parse_mode=pm,
            reply_markup=kb
        )


class ShareAllItems(Action):
    ACTION_SHARE_ALL = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_SHARE_BILL_ITEM)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_SHARE_ALL:
            print("3. Parsing: " + str(datetime.datetime.now().time()))
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)

            if not has_rights(trans, data):
                debts, unique_users = utils.calculate_remaining_debt(
                    bill_id, trans
                )
                text, pm = utils.format_debts_bill_text(
                    bill_id, debts, unique_users, trans
                )
                kb = get_payment_keyboard(bill_id, debts)
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
        kb = get_share_keyboard(bill_id, ACTION_SHARE_BILL_ITEM, trans)
        print("6. Prepared: " + str(datetime.datetime.now().time()))
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


def get_share_keyboard(bill_id, action, trans):
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


def get_payment_keyboard(bill_id, debts):
    kb = []
    for debt in debts:
        credtr = debt['creditor']
        pay_btn = InlineKeyboardButton(
            text='Pay ' + utils.format_name(credtr[3], credtr[1], credtr[2]),
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_PAY_DEBT,
                {const.JSON_BILL_ID: bill_id,
                 const.JSON_CREDITOR_ID: credtr[0]}
            )
        )
        kb.append([pay_btn])
    inspect_btn = InlineKeyboardButton(
        text='Inspect bill',
        url='https://telegram.me/WhoPayBot?start=' + bill_id
    )
    kb.append([inspect_btn])

    return InlineKeyboardMarkup(kb)


def has_rights(trans, data):
    if data is None:
        return True
    bill_id = data.get(const.JSON_BILL_ID)
    if bill_id is None:
        return True

    __, __, __, is_closed = trans.get_bill_gen_info(bill_id)

    if is_closed is not None:
        return False

    return True
