# Wrapper file for accessing the database
import sqlite3
 
DATABASE_PATH = "database.db"
 
def get_database():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row # Access columns by name
    return conn
 
def init_database():
    with get_database() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS user (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TEXT DEFAULT (datetime('now'))
            );
 
            CREATE TABLE IF NOT EXISTS note (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES user(id),
                title       TEXT NOT NULL,
                content     TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now'))
            );
                           
            CREATE TABLE IF NOT EXISTS activity (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id     INTEGER NOT NULL REFERENCES note(id),
                event_type  TEXT NOT NULL CHECK(event_type IN ('view', 'edit')),
                created_at  TEXT DEFAULT (datetime('now'))
            );
        """)
 
if __name__ == "__main__":
    init_database()
    print("Database initialised")
 