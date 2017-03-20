import psycopg2
import uuid
import json


UNIQUE_VIOLATION = '23505'


class Database:
    def __init__(self, host, db, port, user, pw):
        self.host = host
        self.db = db
        self.port = port
        self.user = user
        self.pw = pw

    def get_connection(self):
        return self.Connection(
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

    def add_session(self, chat_id, user_id, action, data=None):
        if data is not None:
            data = json.dumps(data)

        try:
            self.cursor.execute("""\
                INSERT INTO sessions (chat_id, user_id, action, data,
                    updated_at)
                    VALUES(%s, %s, %s, %s, NOW())
                ON CONFLICT(chat_id, user_id) DO UPDATE SET
                    chat_id=EXCLUDED.chat_id, user_id=EXCLUDED.user_id,
                    action=EXCLUDED.action, data=EXCLUDED.data,
                    updated_at=EXCLUDED.updated_at;
            """, (chat_id, user_id, action, data)
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
                SELECT s.action, s.data FROM sessions s
                WHERE s.chat_id = %s
                    AND s.user_id = %s
                FOR UPDATE;
            """, (chat_id, user_id)
            )

            rows = self.cursor.fetchall()

            if len(rows) > 1:
                raise Exception('More than 1 action.')

            data = rows[0][1]
            if data is not None:
                data = json.loads(data)
            else:
                data = {}

            return rows[0][0], data
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

    def add_item(self, bill_id, item_name, price):
        try:
            self.cursor.execute("""\
                INSERT INTO items (name, price)
                    VALUES (%s, %s)
                RETURNING id;
            """, (item_name, price)
            )

            if self.cursor.rowcount < 1:
                raise Exception('Add item failed')

            item = self.cursor.fetchone()
            item_id = item[0]
            self.cursor.execute("""\
                INSERT INTO bill_items (bill_id, item_id)
                    VALUES (%s, %s);
            """, (bill_id, item_id)
            )
        except Exception as e:
            self.is_error = True
            raise e

    def reset_session(self, chat_id, user_id, data=None):
        try:
            self.cursor.execute("""\
                UPDATE sessions
                    SET action = NULL, data = %s
                WHERE chat_id = %s
                    AND user_id = %s
            """, (data, chat_id, user_id)
            )
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
            self.cursor.execute("""\
                SELECT b.title, i.id, i.name, i.price
                    FROM bills b
                LEFT JOIN bill_items bi ON bi.bill_id = b.id
                LEFT JOIN items i ON i.id = bi.item_id
                WHERE b.id = %s
                    AND b.owner_id = %s
            """, (bill_id, user_id)
            )

            rows = self.cursor.fetchall()
            if self.cursor.rowcount == 1:
                bill['title'] = rows[0][0]
            else:
                for row in rows:
                    bill_name, item_id, item_name, item_price = row
                    bill['title'] = bill_name
                    bill['items'].append((item_id, item_name, item_price))

            self.cursor.execute("""\
                SELECT bt.title, bt.amount
                    FROM bill_taxes bt
                INNER JOIN bills b ON b.id = bt.bill_id
                WHERE b.id = %s
                    AND b.owner_id = %s
            """, (bill_id, user_id)
            )

            bill['taxes'] = self.cursor.fetchall()

        except Exception as e:
            self.is_error = True
            raise e

        return bill

    @staticmethod
    def generate_id(length):
        guid = str(uuid.uuid1())
        return guid.replace('-', '')[:length]
