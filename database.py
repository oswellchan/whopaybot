import psycopg2


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
                    VALUES({}, '{}', '{}', '{}')
                ON CONFLICT(id) DO UPDATE SET
                    id=EXCLUDED.id, first_name=EXCLUDED.first_name,
                    last_name=EXCLUDED.last_name, username=EXCLUDED.username;
            """.format(
                user_id,
                first_name,
                last_name,
                username
            ))
        except Exception as e:
            self.is_error = True
            raise e

    def add_session(self, chat_id, user_id, action):
        try:
            self.cursor.execute("""\
                INSERT INTO sessions (chat_id, user_id, action, updated_at)
                    VALUES({}, {}, {}, NOW())
                ON CONFLICT(chat_id) DO UPDATE SET
                    chat_id=EXCLUDED.chat_id, user_id=EXCLUDED.user_id,
                    action=EXCLUDED.action, updated_at=EXCLUDED.updated_at;
            """.format(chat_id, user_id, action)
            )
        except Exception as e:
            self.is_error = True
            raise e

    def get_pending_action(self, chat_id, user_id):
        try:
            self.cursor.execute("""\
                SELECT s.action FROM sessions s
                WHERE s.chat_id = {}
                    AND s.user_id = {}
                FOR UPDATE;
            """.format(chat_id, user_id)
            )

            rows = self.cursor.fetchall()
            if len(rows) > 1:
                raise Exception('More than 1 action.')

            return rows[0][0]
        except Exception as e:
            self.is_error = True
            raise e
