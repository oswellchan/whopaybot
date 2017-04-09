from telegram.parsemode import ParseMode
import os
import sys
import json
import constants as const
import math


def print_error():
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno)


def get_action_callback_data(action_type, action_id, data):
    data[const.JSON_ACTION_TYPE] = action_type
    data[const.JSON_ACTION_ID] = action_id
    return json.dumps(data)


def format_complete_bill_text(bill, bill_id, trans):
    try:
        if bill.get('title') is None or len(bill.get('title')) == 0:
            raise Exception('Bill does not exist')

        title_text = '<b>{}</b>'.format(escape_html(bill['title']))

        sharers = trans.get_sharers(bill_id)
        num_sharers = count_unique_users(sharers)
        title_text += ('   ' + const.EMOJI_PERSON + str(num_sharers))

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
                for i_id, __, username, first_name, last_name in sharers:
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


def get_complete_bill_text(bill_id, trans):
    try:
        bill = trans.get_bill_details(bill_id)
        return format_complete_bill_text(bill, bill_id, trans)
    except Exception as e:
        print(e)


def format_debts_bill_text(bill_id, debts, unique_users, trans):
    try:
        title, __, __, __ = trans.get_bill_gen_info(bill_id)
        title_text = '<b>{}</b>'.format(escape_html(title))
        title_text += ('   ' + const.EMOJI_PERSON + str(unique_users))

        debts_text = []
        if len(debts) < 1:
            debts_text.append('<i>No debts</i>')
        else:
            for debt in debts:
                __, fname, lname, uname = debt['creditor']
                h = '<i>Pay to:</i>\n{}  {}{:.2f}\n\n<i>Amount to pay:</i>'.format(
                    format_name(uname, fname, lname),
                    const.EMOJI_MONEY_BAG,
                    debt['total_amt']
                )
                debts_text.append(h)
                if len(debt['debtors']) < 1:
                    debts_text.append('No debts')
                for i, debtor in enumerate(debt['debtors']):
                    __, fname, lname, uname = debtor['debtor']
                    debt_row = '{}. {}\n{}{:.4f}/{:.4f} {}'.format(
                        str(i + 1),
                        format_name(uname, fname, lname),
                        const.EMOJI_MONEY_BAG,
                        debtor['amt'],
                        debtor['orig_amt'],
                        debtor['status']
                    )
                debts_text.append(debt_row)
        text = title_text + '\n' + '\n'.join(debts_text)
        return text, ParseMode.HTML
    except Exception as e:
        print(e)


def get_debts_bill_text(bill_id, trans):
    try:
        debts, unique_users = calculate_remaining_debt(bill_id, trans)
        return format_debts_bill_text(bill_id, debts, unique_users, trans)
    except Exception as e:
        print(e)


def calculate_remaining_debt(bill_id, trans):
    unique_users = set()
    results = []
    debts = trans.get_debts(bill_id)
    if len(debts) < 1:
        return []

    result = None
    debtor = None
    is_pending = False
    for i, debt in enumerate(debts):
        unique_users.add(debt[2])
        creditor = (debt[6], debt[7], debt[8], debt[9])
        if result is None:
            result = {
                'total_amt': 0,
                'creditor': creditor,
                'debtors': []
            }
        if result['creditor'] != creditor:
            results.append(result)
            result = {
                'total_amt': 0,
                'creditor': creditor,
                'debtors': []
            }

        debt_id = debt[0]
        if debtor is None:
            debtor = {
                'debtor': (debt[2], debt[3], debt[4], debt[5]),
                'debt_id': debt_id,
                'orig_amt': debt[1],
                'amt': debt[1],
                'status': '',
            }
            result['total_amt'] += debt[1]

        if debtor['debt_id'] != debt_id:
            if is_pending:
                debtor['status'] = '(Pending)'
            elif math.isclose(debtor['amt'], 0):
                debtor['amt'] = 0
                debtor['status'] = '(Paid)'
            results['debtors'].append(debtor)

            # Reset debtor info with new info
            is_pending = False
            debtor = {
                'debtor': (debt[2], debt[3], debt[4], debt[5]),
                'debt_id': debt_id,
                'orig_amt': debt[1],
                'amt': debt[1],
                'status': '',
            }
            result['total_amt'] += debt[1]

        pay_amt = debt[10]
        created_at = debt[11]
        confirmed_at = debt[12]
        if confirmed_at is not None:
            debtor['amt'] -= pay_amt
        else:
            is_pending = is_pending or (created_at is not None)

        if i >= len(debts) - 1:
            if is_pending:
                debtor['status'] = '(Pending)'
            elif math.isclose(debtor['amt'], 0):
                debtor['amt'] = 0
                debtor['status'] = '(Paid)'
            result['debtors'].append(debtor)
            results.append(result)

    return results, len(unique_users)


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


def format_time(time):
    return time.strftime('%d %b %Y %-I:%M%p')


def escape_html(s):
    arr = s.split('&')
    escaped = []

    for sgmt in arr:
        a = sgmt.replace('<', '&lt;')
        a = a.replace('>', '&gt;')
        escaped.append(a)

    return '&amp;'.join(escaped)
