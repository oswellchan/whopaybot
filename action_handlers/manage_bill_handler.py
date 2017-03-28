from action_handlers.action_handler import ActionHandler, Action
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
        action.execute(bot, update, trans, subaction_id, data)


class SendCompleteBill(Action):
    ACTION_MANAGE_BILL = 0

    def __init__(self):
        super().__init__(MODULE_ACTION_TYPE, ACTION_GET_MANAGE_BILL)

    def execute(self, bot, update, trans, subaction_id, data=None):
        if subaction_id == self.ACTION_MANAGE_BILL:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return self.send_bill_response(bot, cbq, bill_id, trans)

    def send_bill_response(self, bot, cbq, bill_id, trans):
        chat_id = cbq.message.chat_id
        user_id = cbq.from_user.id
        text, pm = utils.get_complete_bill_text(bill_id, user_id, trans)
        keyboard = DisplayManageBillKB.get_manage_bill_keyboard(bill_id)
        trans.reset_session(cbq.from_user.id, chat_id)
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
        if subaction_id == self.ACTION_DISPLAY_NEW_BILL_KB:
            cbq = update.callback_query
            bill_id = data.get(const.JSON_BILL_ID)
            return cbq.edit_message_reply_markup(
                reply_markup=self.get_manage_bill_keyboard(bill_id)
            )

    @staticmethod
    def get_manage_bill_keyboard(bill_id):
        share_btn = InlineKeyboardButton(
            text="Share Bill",
            callback_data=utils.get_action_callback_data(
                MODULE_ACTION_TYPE,
                ACTION_SHARE_BILL,
                {const.JSON_BILL_ID: bill_id}
            )
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
            return SendCompleteBill().execute(bot, update, trans, subaction_id, data)
