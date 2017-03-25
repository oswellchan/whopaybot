import os
import sys
import json
import constants as const


def print_error():
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno)


def get_action_callback_data(action_type, action_id, data):
    data[const.JSON_ACTION_TYPE] = action_type
    data[const.JSON_ACTION_ID] = action_id
    return json.dumps(data)


def escape_html(s):
    arr = s.split('&')
    escaped = []

    for sgmt in arr:
        a = sgmt.replace('<', '&lt;')
        a = a.replace('>', '&gt;')
        escaped.append(a)

    return '&amp;'.join(escaped)
