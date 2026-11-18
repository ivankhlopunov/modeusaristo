import sqlite3


def connect():
    connection = sqlite3.connect("interviews.db")
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_tables():
    connection = connect()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interview_id TEXT,
            role TEXT,
            content TEXT,
            stale INTEGER DEFAULT 0,
            FOREIGN KEY (interview_id) REFERENCES interviews(id)
        )
    """)

    connection.commit()
    connection.close()


def create_interview(interview_id):
    connection = connect()

    connection.execute(
        "INSERT INTO interviews (id) VALUES (?)",
        (interview_id,)
    )

    connection.commit()
    connection.close()


def save_message(interview_id, role, content, stale=False):
    connection = connect()

    cursor = connection.execute(
        """
        INSERT INTO messages (interview_id, role, content, stale)
        VALUES (?, ?, ?, ?)
        """,
        (interview_id, role, content, int(stale))
    )

    message_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return message_id


def load_messages(interview_id):
    connection = connect()

    messages = connection.execute(
        """
        SELECT id, role, content, stale
        FROM messages
        WHERE interview_id = ?
        ORDER BY id
        """,
        (interview_id,)
    ).fetchall()

    connection.close()

    result = []

    for message_id, role, content, stale in messages:
        result.append({
            "id": message_id,
            "role": role,
            "content": content,
            "stale": bool(stale)
        })

    return result


def get_latest_interview():
    connection = connect()

    interview = connection.execute(
        "SELECT id FROM interviews ORDER BY created_at DESC LIMIT 1"
    ).fetchone()

    connection.close()

    if interview:
        return interview[0]

    return None


def update_message(message_id, content):
    connection = connect()

    connection.execute(
        "UPDATE messages SET content = ? WHERE id = ?",
        (content, message_id)
    )

    connection.commit()
    connection.close()


def mark_following_stale(interview_id, message_id):
    connection = connect()

    connection.execute(
        """
        UPDATE messages
        SET stale = 1
        WHERE interview_id = ? AND id > ?
        """,
        (interview_id, message_id)
    )

    connection.commit()
    connection.close()