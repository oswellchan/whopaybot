class ActionHandler:
    def __init__(self, action_type):
        self.action_type = action_type

    def execute(self, bot, update, trans, action_id,
                subaction_id=0, data=None):
        pass

    def execute_done(self, bot, update, trans, action_id,
                     subaction_id=0, data=None):
        pass

    def execute_yes(self, bot, update, trans, action_id,
                    subaction_id=0, data=None):
        pass

    def execute_no(self, bot, update, trans, action_id,
                   subaction_id=0, data=None):
        pass


class Action:
    def __init__(self, action_type, action_id):
        self.action_type = action_type
        self.action_id = action_id

    def execute(self, bot, update, trans, subaction_id, data=None):
        pass

    def done(self, bot, update, trans, subaction_id, data=None):
        pass

    def yes(self, bot, update, trans, subaction_id, data=None):
        pass

    def no(self, bot, update, trans, subaction_id, data=None):
        pass

    def set_session(self, chat_id, user, action_type,
                    action_id, subaction_id, trans, data=None):
        trans.add_user(
            user.id,
            user.first_name,
            user.last_name,
            user.username
        )
        trans.add_session(
            chat_id,
            user.id,
            action_type,
            action_id,
            subaction_id,
            data
        )
