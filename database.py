import psycopg2


class Database():
    def __init__(self, host, db, port, user, pw):
        conn = psycopg2.connect(
            "host='{}' dbname='{}' user='{}' password='{}' port='{}'".format(
                host, db, port, user, pw
            )
        )
        self.cursor = conn.cursor()
        try:
            self.cursor.execute("""SELECT * from bill""")
        except:
            print("I can't SELECT from bill")

        rows = self.cursor.fetchall()
        for row in rows:
            print("   ", row[1])
