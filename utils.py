from telegram.parsemode import ParseMode
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


def get_complete_bill_text(bill_id, user_id, trans):
    try:
        bill = trans.get_bill_details(bill_id, user_id)
        if bill.get('title') is None or len(bill.get('title')) == 0:
            raise Exception('Bill does not exist')

        title_text = '<b>{}</b>'.format(escape_html(bill['title']))

        sharers = trans.get_sharers(bill_id)
        num_sharers = count_unique_users(sharers)
        title_text += ('   ' + const.EMOJI_PERSON + str(num_sharers))

        items_text = []
        total = 0
        if len(sharers) < 1:
            items_text.append('<i>Currently no items</i>')
        else:
            item_index = 0
            user_index = 0
            prev_id = -1
            for i_id, i_name, i_price, __, u_username, \
                    u_first_name, u_last_name in sharers:
                if i_id != prev_id:
                    item_index += 1
                    user_index = 0
                    total += i_price

                    items_text.append('<i>{}. {}  {}{:.2f}</i>'.format(
                        str(item_index), i_name, const.EMOJI_MONEY_BAG, i_price
                    ))

                user_index += 1
                items_text.append('  {}) {}'.format(
                    user_index, format_name(
                        u_username,
                        u_first_name,
                        u_last_name
                    )
                ))

        bill_items = bill.get('items')
        items_text = []
        total = 0
        if bill_items is None or len(bill_items) < 1:
            items_text.append('<i>Currently no items</i>')
        else:
            for i, item in enumerate(bill_items):
                item_id, title, price = item
                total += price

                items_text.append('<i>{}. {}  {}{:.2f}</i>'.format(
                    str(i + 1), title, const.EMOJI_MONEY_BAG, price
                ))

                user_index = 0
                for i_id, username, first_name, last_name in sharers:
                    if i_id == item_id:
                        user_index += 1
                        items_text.append('  {}) {}'.format(
                            user_index,
                            format_name(
                                username,
                                first_name,
                                last_name
                            )
                        ))

        bill_taxes = bill.get('taxes')
        taxes_text = []
        if bill_taxes is not None:
            for __, title, tax in bill_taxes:
                total += (tax * total / 100)
                taxes_text.append(const.EMOJI_TAX + ' ' + title +
                                  ': ' + '{:.2f}'.format(tax) + '%')

        text = title_text + '\n\n' + '\n'.join(items_text)
        if len(taxes_text) > 0:
            text += '\n\n' + '\n'.join(taxes_text)

        text += '\n\n' + 'Total: ' + "{:.2f}".format(total)
        return text, ParseMode.HTML
    except Exception as e:
        print(e)


def count_unique_users(sharers):
    unique = set()
    for sharer in sharers:
        unique.add(sharer[1])
    return len(unique)


def format_name(username, first_name, last_name):
    if first_name is not None and last_name is not None:
        return first_name + ' ' + last_name
    if last_name is None and first_name is not None:
        return first_name
    if username is not None:
        return username

    return last_name


def escape_html(s):
    arr = s.split('&')
    escaped = []

    for sgmt in arr:
        a = sgmt.replace('<', '&lt;')
        a = a.replace('>', '&gt;')
        escaped.append(a)

    return '&amp;'.join(escaped)
