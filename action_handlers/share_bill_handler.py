from action_handlers.action_handler import ActionHandler, Action
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.inlinekeyboardbutton import InlineKeyboardButton
import constants as const
import utils

MODULE_ACTION_TYPE = const.TYPE_SHARE_BILL

ACTION_FIND_BILL_SHARES = 0
ACTION_SHARE_BILL_ITEM = 1


class BillShareHandler(ActionHandler):
    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE)

    def execute(self, bot, update, trans, action_id,
                subaction_id=0, data=None):
        action = None
        if action_id == ACTION_FIND_BILL_SHARES:
            action = FindBillShares()
        action.execute(bot, update, trans, subaction_id, data)


class FindBillShares(Action):
    ACTION_FIND_BILL = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_FIND_BILL_SHARES)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_FIND_BILL:
            iq = update.inline_query
            return self.send_bill_response(bot, iq, trans)

    def send_bill_response(self, bot, iq, trans):
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
            keyboard = InlineKeyboardMarkup(get_item_buttons(bill_id, ACTION_SHARE_BILL_ITEM, trans))
            results.append(
                InlineQueryResultArticle(
                    id=bill_id,
                    title=details.get('title'),
                    input_message_content=InputTextMessageContent(
                        msg[0],
                        parse_mode=msg[1]
                    ),
                    reply_markup=keyboard,
                    description='{}\nItems: {}'.format(
                        utils.format_time(details.get('time')),
                        str(len(details.get('items')))
                    )
                )
            )
        iq.answer(results)


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
