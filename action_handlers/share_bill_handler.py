from action_handlers.action_handler import ActionHandler, Action
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.inlinekeyboardbutton import InlineKeyboardButton
import constants as const
import utils

MODULE_ACTION_TYPE = const.TYPE_SHARE_BILL

ACTION_FIND_BILL_SHARES = 0
ACTION_SHARE_BILL_ITEM = 1
ACTION_SHARE_ALL_ITEMS = 2


class BillShareHandler(ActionHandler):
    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE)

    def execute(self, bot, update, trans, action_id,
                subaction_id=0, data=None):
        action = None
        if action_id == ACTION_FIND_BILL_SHARES:
            action = FindBillShares()
        if action_id == ACTION_SHARE_BILL_ITEM:
            action = ShareBillItem()
        if action_id == ACTION_SHARE_ALL_ITEMS:
            action = ShareAllItems()
        action.execute(bot, update, trans, subaction_id, data)


class FindBillShares(Action):
    ACTION_FIND_BILL = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_FIND_BILL_SHARES)

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
        for bill_id in bill_ids:
            details = trans.get_bill_details(bill_id)
            msg = utils.format_complete_bill_text(details, bill_id, trans)
            if msg is None:
                continue
            kb = get_share_keyboard(bill_id, ACTION_SHARE_BILL_ITEM, trans)
            results.append(
                InlineQueryResultArticle(
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
            )
        iq.answer(results)


class ShareBillItem(Action):
    ACTION_SHARE_ITEM = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_SHARE_BILL_ITEM)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_SHARE_ITEM:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            item_id = data.get(const.JSON_ITEM_ID)
            return self.share_bill_item(bot, cbq, bill_id, item_id, trans)

    def share_bill_item(self, bot, cbq, bill_id, item_id, trans):
        trans.toggle_bill_share(bill_id, item_id, cbq.from_user.id)
        text, pm = utils.get_complete_bill_text(bill_id, trans)
        kb = get_share_keyboard(bill_id, ACTION_SHARE_BILL_ITEM, trans)
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
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return self.share_all_items(bot, cbq, bill_id, trans)

    def share_all_items(self, bot, cbq, bill_id, trans):
        trans.toggle_all_bill_shares(bill_id, cbq.from_user.id)
        text, pm = utils.get_complete_bill_text(bill_id, trans)
        kb = get_share_keyboard(bill_id, ACTION_SHARE_BILL_ITEM, trans)
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


def has_rights(update, trans, data):
    if data is None:
        return True
    bill_id = data.get('bill_id')
    if bill_id is None:
        bill_id = data.get(const.JSON_BILL_ID)
    if bill_id is None:
        return True, None, None

    __, __, __, is_closed = trans.get_bill_gen_info(bill_id)

    if is_closed is not None:
        return False

    return True
