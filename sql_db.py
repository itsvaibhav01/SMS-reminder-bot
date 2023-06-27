import sqlite3
import threading

class SQLiteManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self._local = threading.local()
        self._create_tables()

    def _create_tables(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users
                        (phone_number TEXT PRIMARY KEY, name TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS messages
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, phone_number TEXT, message TEXT, status TEXT, message_order INTEGER DEFAULT 0)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS models
                        (message_id INTEGER PRIMARY KEY, task TEXT, time TEXT, date TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS reminders
                        (phone_number TEXT, job TEXT, task TEXT, done INTEGER DEFAULT 0)''')
        conn.commit()
        cursor.close()

    def _get_connection(self):
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(self.db_file)
        return self._local.connection

    def execute(self, query, params=()):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor

    def add_user(self, phone_number, name):
        self.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (phone_number, name))

    def get_username(self, phone_number):
        cursor = self.execute("SELECT name FROM users WHERE phone_number=?", (phone_number,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None

    def add_message(self, phone_number, message, status):
        cursor = self.execute("INSERT INTO messages (phone_number, message, status) VALUES (?, ?, ?)",
                              (phone_number, message, status))
        message_id = cursor.lastrowid
        cursor.close()
        return message_id

    def get_last_received_message(self, phone_number):
        cursor = self.execute("SELECT message FROM messages WHERE phone_number=? AND status='received' ORDER BY id DESC LIMIT 1",
                              (phone_number,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None

    def check_username_sent(self, phone_number):
        cursor = self.execute("SELECT status FROM messages WHERE phone_number=? AND message='Hello! What is your name?'",
                              (phone_number,))
        result = cursor.fetchone()
        print('check_username_sent', result)
        return bool(result)

    def update_username_sent(self, phone_number):
        self.execute("UPDATE messages SET status='sent' WHERE phone_number=? AND message='What''s your name?'",
                     (phone_number,))

    def get_last_order(self, phone_number):
        cursor = self.execute("SELECT id, message_order FROM messages WHERE phone_number=? ORDER BY id DESC LIMIT 1 OFFSET 1",
                              (phone_number,))
        result = cursor.fetchone()
        if result:
            return result[0], result[1]
        return None, 0

    def set_order(self, phone_number, new_order):
        cursor = self.execute("SELECT id, message_order FROM messages WHERE phone_number=? ORDER BY id DESC LIMIT 1", (phone_number,))
        last_message = cursor.fetchone()
        if last_message is not None:
            message_id, last_order = last_message
            self.execute("UPDATE messages SET message_order=? WHERE id=?", (new_order, message_id))


    def update_model(self, message_id, task, time, date):
        self.execute("INSERT OR REPLACE INTO models VALUES (?, ?, ?, ?)",
                     (message_id, task, time, date))

    def get_task_and_date(self, message_id):
        cursor = self.execute("SELECT task, date FROM models WHERE message_id=?", (message_id,))
        result = cursor.fetchone()
        if result:
            return result[0], result[1]
        return None, None

    def add_reminder(self, phone_number, job_id, task):
        self.execute("INSERT OR REPLACE INTO reminders VALUES (?, ?, ?, 0)", (phone_number, job_id, task))

    def get_reminder_jobs(self, phone_number):
        cursor = self.execute("SELECT job FROM reminders WHERE done=0 AND phone_number=?", (phone_number,))
        job_ids = [row[0] for row in cursor.fetchall()]
        return job_ids

    def get_task_by_job_id(self, phone_number, job_id):
        cursor = self.execute("SELECT task FROM reminders WHERE phone_number=? AND job=?", (phone_number, job_id))
        task_rows = cursor.fetchall()
        tasks = [row[0] for row in task_rows]
        return tasks

    def set_reminder_done(self, job_id):
        print(job_id)
        self.execute("UPDATE reminders SET done=1 WHERE job=?", (job_id,))