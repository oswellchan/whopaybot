import psycopg2
import uuid
import json
import utils


UNIQUE_VIOLATION = '23505'


class Database:
    def __init__(self, host, db, port, user, pw):
        self.host = host
        self.db = db
        self.port = port
        self.user = user
        self.pw = pw

    def get_connection(self):
        return Connection(
            self.host,
            self.db,
            self.port,
            self.user,
            self.pw
        )


class Connection:
    def __init__(self, host, db, port, user, pw):
        conn = psycopg2.connect(
            "host='{}' dbname='{}' user='{}' password='{}' port='{}'".format(
                host, db, user, pw, port
            )
        )
        conn.autocommit = True
        self.cursor = conn.cursor()


class Transaction:
    def __init__(self, connection):
        self.cursor = connection.cursor

    def __enter__(self):
        self.cursor.execute("BEGIN;")
        self.is_error = False
        return self

    def __exit__(self, type, value, traceback):
        if self.is_error:
            self.cursor.execute("ROLLBACK;")
            return

        self.cursor.execute("COMMIT;")

    def add_user(self, user_id, first_name, last_name, username):
        try:
            self.cursor.execute("""\
                INSERT INTO users (id, first_name, last_name, username)
                    VALUES(%s, %s, %s, %s)
                ON CONFLICT(id) DO UPDATE SET
                    id=EXCLUDED.id, first_name=EXCLUDED.first_name,
                    last_name=EXCLUDED.last_name, username=EXCLUDED.username;
            """, (user_id, first_name, last_name, username)
            )
        except Exception as e:
            self.is_error = True
            raise e

    def add_session(self, chat_id, user_id, action_type,
                    action_id, subaction_id, data=None):
        if data is not None:
            data = json.dumps(data)

        try:
            self.cursor.execute("""\
                INSERT INTO sessions (chat_id, user_id, action_type,
                    action_id, subaction_id, data, updated_at)
                    VALUES(%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT(chat_id, user_id) DO UPDATE SET
                    chat_id=EXCLUDED.chat_id,
                    user_id=EXCLUDED.user_id,
                    action_type=EXCLUDED.action_type,
                    action_id=EXCLUDED.action_id,
                    subaction_id=EXCLUDED.subaction_id,
                    data=EXCLUDED.data,
                    updated_at=EXCLUDED.updated_at;
            """, (chat_id, user_id, action_type, action_id, subaction_id, data)
            )
        except Exception as e:
            self.is_error = True
            raise e

    def get_session(self, chat_id, user_id):
        """\
        Get pending action. Also serves as lock against concurrent access.
        """
        try:
            self.cursor.execute("""\
                SELECT s.action_type, s.action_id, s.subaction_id,
                    s.data FROM sessions s
                WHERE s.chat_id = %s
                    AND s.user_id = %s
                FOR UPDATE;
            """, (chat_id, user_id)
            )

            rows = self.cursor.fetchall()

            if len(rows) > 1:
                raise Exception('More than 1 action.')

            data = rows[0][3]
            if data is not None:
                data = json.loads(data)
            else:
                data = {}

            return rows[0][0], rows[0][1], rows[0][2], data
        except Exception as e:
            self.is_error = True
            raise e

    def reset_session(self, chat_id, user_id, data=None):
        try:
            self.cursor.execute("""\
                UPDATE sessions
                SET action_type = NULL, action_id = NULL,
                    subaction_id = NULL, data = %s
                WHERE chat_id = %s
                    AND user_id = %s
            """, (data, chat_id, user_id)
            )
        except Exception as e:
            self.is_error = True
            raise e

    def add_bill(self, title, owner_id):
        try:
            count = 0
            while count < 10:
                bill_id = self.generate_id(16)
                self.cursor.execute("""\
                    INSERT INTO bills (id, title, owner_id)
                        VALUES (%s, %s, %s)
                    ON CONFLICT(id) DO NOTHING;
                """, (bill_id, title, owner_id)
                )
                if self.cursor.rowcount > 0:
                    return bill_id

                count += 1

            if count >= 10:
                raise Exception("Collision of bills id")
        except Exception as ex:
            self.is_error = True
            raise ex

    def set_bill_done(self, bill_id, user_id):
        try:
            self.cursor.execute("""\
                UPDATE bills SET completed_at = NOW()
                WHERE id = %s
                    AND owner_id = %s
                RETURNING id;
            """, (bill_id, user_id)
            )

            if self.cursor.rowcount < 1:
                raise Exception('Add item failed')
        except Exception as e:
            self.is_error = True
            raise e

    def add_item(self, bill_id, item_name, price):
        try:
            self.cursor.execute("""\
                INSERT INTO items (bill_id, name, price)
                    VALUES (%s, %s, %s)
                RETURNING id;
            """, (bill_id, item_name, price)
            )

            if self.cursor.rowcount < 1:
                raise Exception('Add item failed')
        except Exception as e:
            self.is_error = True
            raise e

    def get_bill_details(self, bill_id, user_id):
        bill = {
            'title': '',
            'items': [],
            'taxes': []
        }

        try:
            bill['title'] = self.get_bill_name(bill_id, user_id)
            bill['items'] = self.get_bill_items(bill_id)
            bill['taxes'] = self.get_bill_taxes(bill_id)

            return bill
        except Exception as e:
            self.is_error = True
            raise e

    def get_bill_name(self, bill_id, user_id):
        try:
            self.cursor.execute("""\
                SELECT b.title FROM bills b
                WHERE b.id = %s
                    AND b.owner_id = %s
                """, (bill_id, user_id)
            )

            if self.cursor.rowcount != 1:
                raise Exception('More than 1 bill found')

            return self.cursor.fetchone()[0]
        except Exception as e:
            self.is_error = True
            raise e

    def get_bill_items(self, bill_id):
        try:
            self.cursor.execute("""\
                SELECT i.id, i.name, i.price
                    FROM items i
                WHERE i.bill_id = %s
                ORDER BY i.created_at
            """, (bill_id,)
            )
            return self.cursor.fetchall()
        except Exception as e:
            utils.print_error()
            self.is_error = True
            raise e

    def get_item(self, item_id):
        try:
            self.cursor.execute("""\
                SELECT i.name, i.price
                    FROM items i
                WHERE i.id = %s
            """, (item_id,)
            )
            return self.cursor.fetchone()
        except Exception as e:
            utils.print_error()
            self.is_error = True
            raise e

    def edit_item_name(self, bill_id, item_id, user_id, name):
        try:
            self.cursor.execute("""\
                UPDATE items SET name = %s
                WHERE id = %s
                AND EXISTS(
                    SELECT * FROM items i
                    INNER JOIN bills b on b.id = i.bill_id
                    WHERE i.id = %s
                    AND b.id = %s
                    AND b.completed_at IS NULL
                    AND b.owner_id = %s
                )
                RETURNING id
            """, (name, item_id, item_id, bill_id, user_id)
            )

            count = self.cursor.rowcount
            if count != 1:
                raise Exception("Updated rows not expected. '{}'".format(count))
        except Exception as e:
            self.is_error = True
            raise e

    def edit_item_price(self, bill_id, item_id, user_id, price):
        try:
            self.cursor.execute("""\
                UPDATE items SET price = %s
                WHERE id = %s
                AND EXISTS(
                    SELECT * FROM items i
                    INNER JOIN bills b on b.id = i.bill_id
                    WHERE i.id = %s
                    AND b.id = %s
                    AND b.completed_at IS NULL
                    AND b.owner_id = %s
                )
                RETURNING id
            """, (price, item_id, item_id, bill_id, user_id)
            )

            count = self.cursor.rowcount
            if count != 1:
                raise Exception("Updated rows not expected. '{}'".format(count))
        except Exception as e:
            self.is_error = True
            raise e

    def delete_item(self, bill_id, item_id, user_id):
        try:
            self.cursor.execute("""\
                DELETE FROM items
                WHERE id = %s
                AND EXISTS(
                    SELECT * FROM items i
                    INNER JOIN bills b on b.id = i.bill_id
                    WHERE i.id = %s
                    AND b.id = %s
                    AND b.completed_at IS NULL
                    AND b.owner_id = %s
                )
                RETURNING id
            """, (item_id, item_id, bill_id, user_id)
            )

            count = self.cursor.rowcount
            if count != 1:
                raise Exception("Deleted rows not expected. '{}'".format(count))
        except Exception as e:
            self.is_error = True
            raise e

    def get_bill_taxes(self, bill_id):
        try:
            self.cursor.execute("""\
                SELECT bt.id, bt.title, bt.amount
                    FROM bill_taxes bt
                WHERE bt.bill_id = %s
                ORDER BY bt.created_at
            """, (bill_id,)
            )

            return self.cursor.fetchall()
        except Exception as e:
            self.is_error = True
            raise e

    def add_tax(self, bill_id, tax_name, amt):
        try:
            self.cursor.execute("""\
                INSERT INTO bill_taxes (bill_id, title, amount)
                    VALUES (%s, %s, %s)
                RETURNING id;
            """, (bill_id, tax_name, amt)
            )

            if self.cursor.rowcount < 1:
                raise Exception('Add tax failed')
        except Exception as e:
            self.is_error = True
            raise e

    def get_tax(self, tax_id):
        try:
            self.cursor.execute("""\
                SELECT bt.title, bt.amount
                    FROM bill_taxes bt
                WHERE bt.id = %s
            """, (tax_id,)
            )
            return self.cursor.fetchone()
        except Exception as e:
            utils.print_error()
            self.is_error = True
            raise e

    def edit_tax_name(self, bill_id, tax_id, user_id, name):
        try:
            self.cursor.execute("""\
                UPDATE bill_taxes bt SET title = %s
                WHERE id = %s
                AND EXISTS(
                    SELECT * FROM bill_taxes bt
                    INNER JOIN bills b on b.id = bt.bill_id
                    WHERE bt.id = %s
                    AND b.id = %s
                    AND b.completed_at IS NULL
                    AND b.owner_id = %s
                )
                RETURNING id
            """, (name, tax_id, tax_id, bill_id, user_id)
            )

            count = self.cursor.rowcount
            if count != 1:
                raise Exception("Updated rows not expected. '{}'".format(count))
        except Exception as e:
            self.is_error = True
            raise e

    def edit_tax_amt(self, bill_id, tax_id, user_id, amt):
        try:
            self.cursor.execute("""\
                UPDATE bill_taxes SET amount = %s
                WHERE id = %s
                AND EXISTS(
                    SELECT * FROM bill_taxes bt
                    INNER JOIN bills b on b.id = bt.bill_id
                    WHERE bt.id = %s
                    AND b.id = %s
                    AND b.completed_at IS NULL
                    AND b.owner_id = %s
                )
                RETURNING id
            """, (amt, tax_id, tax_id, bill_id, user_id)
            )

            count = self.cursor.rowcount
            if count != 1:
                raise Exception("Updated rows not expected. '{}'".format(count))
        except Exception as e:
            self.is_error = True
            raise e

    def delete_tax(self, bill_id, tax_id, user_id):
        try:
            self.cursor.execute("""\
                DELETE FROM bill_taxes
                WHERE id = %s
                AND EXISTS(
                    SELECT * FROM bill_taxes bt
                    INNER JOIN bills b on b.id = bt.bill_id
                    WHERE bt.id = %s
                    AND b.id = %s
                    AND b.completed_at IS NULL
                    AND b.owner_id = %s
                )
                RETURNING id
            """, (tax_id, tax_id, bill_id, user_id)
            )

            count = self.cursor.rowcount
            if count != 1:
                raise Exception("Deleted rows not expected. '{}'".format(count))
        except Exception as e:
            self.is_error = True
            raise e

    def get_sharers(self, bill_id):
        try:
            self.cursor.execute("""\
                SELECT bs.item_id, u.id, u.username,
                    u.first_name, u.last_name
                FROM bill_shares bs
                INNER JOIN users u ON u.id = bs.user_id
                WHERE bs.bill_id = %s
                ORDER BY bs.created_at
            """, (bill_id,)
            )

            return self.cursor.fetchall()
        except Exception as e:
            self.is_error = True
            raise e

    @staticmethod
    def generate_id(length):
        guid = str(uuid.uuid1())
        return guid.replace('-', '')[:length]
