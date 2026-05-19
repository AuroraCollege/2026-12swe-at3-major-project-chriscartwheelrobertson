"""
test.py — populate database.db with example test data.

Run with:  python test.py
Re-running drops and recreates all tables so the data is always fresh.

Users created:
  alice  /  password: alice123
  bob    /  password: bob123

Notes:
  Alice has 5 notes with varying ages and activity levels.
  Bob   has 2 notes with minimal activity.
"""

from werkzeug.security import generate_password_hash
from database import get_database, init_database
import os

# ── Fresh start ───────────────────────────────────────────────
if os.path.exists("database.db"):
    os.remove("database.db")
    print("Removed existing database.db")

init_database()
print("Schema created")

conn = get_database()

# ── Users ─────────────────────────────────────────────────────
users = [
    ("alice", generate_password_hash("alice123")),
    ("bob",   generate_password_hash("bob123")),
]

conn.executemany(
    "INSERT INTO user (username, password_hash) VALUES (?, ?)",
    users
)
conn.commit()
print("Inserted 2 users")

alice_id = conn.execute("SELECT id FROM user WHERE username = 'alice'").fetchone()["id"]
bob_id   = conn.execute("SELECT id FROM user WHERE username = 'bob'").fetchone()["id"]

# ── Notes ─────────────────────────────────────────────────────
# (user_id, title, content, created_at, updated_at)
notes = [
    # Alice — hot note, edited recently
    (alice_id,
     "Python decorators",
     "A decorator is a function that wraps another function. "
     "Use @functools.wraps to preserve the wrapped function's metadata.",
     "2026-05-01 09:00:00",
     "2026-05-18 14:30:00"),

    # Alice — warm note, edited a week ago
    (alice_id,
     "Flask routing",
     "Routes are defined with @app.route. "
     "Use <int:id> for typed URL parameters. "
     "Methods default to GET only unless specified.",
     "2026-04-10 11:00:00",
     "2026-05-11 10:00:00"),

    # Alice — aging note, edited 3 weeks ago
    (alice_id,
     "SQL joins explained",
     "INNER JOIN returns rows with matches in both tables. "
     "LEFT JOIN keeps all rows from the left table. "
     "Use ON to specify the join condition.",
     "2026-03-20 08:00:00",
     "2026-04-28 16:00:00"),

    # Alice — stale note, edited 6 weeks ago
    (alice_id,
     "HTTP status codes",
     "200 OK. 201 Created. 301 Moved Permanently. "
     "400 Bad Request. 401 Unauthorised. 403 Forbidden. "
     "404 Not Found. 500 Internal Server Error.",
     "2026-02-14 12:00:00",
     "2026-04-07 09:00:00"),

    # Alice — dormant note, edited 4 months ago
    (alice_id,
     "Git branching strategy",
     "Main branch is always deployable. "
     "Feature branches merge via pull request. "
     "Use rebase to keep history clean.",
     "2026-01-05 10:00:00",
     "2026-01-20 11:00:00"),

    # Bob — fresh note
    (bob_id,
     "Study timetable",
     "Monday: algorithms. Tuesday: databases. "
     "Wednesday: networks. Thursday: revision.",
     "2026-05-15 08:00:00",
     "2026-05-17 09:00:00"),

    # Bob — aging note
    (bob_id,
     "Essay outline",
     "Introduction: define the problem. "
     "Body: three supporting arguments. "
     "Conclusion: restate thesis.",
     "2026-04-01 14:00:00",
     "2026-04-25 15:00:00"),
]

conn.executemany(
    """INSERT INTO note (user_id, title, content, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?)""",
    notes
)
conn.commit()
print(f"Inserted {len(notes)} notes")

# Map titles to IDs for activity insertion
def note_id(title):
    return conn.execute(
        "SELECT id FROM note WHERE title = ?", (title,)
    ).fetchone()["id"]

# ── Activity ──────────────────────────────────────────────────
# (note_id, event_type, created_at)
# Hot note — many recent edits and views
python_id   = note_id("Python decorators")
flask_id    = note_id("Flask routing")
sql_id      = note_id("SQL joins explained")
http_id     = note_id("HTTP status codes")
git_id      = note_id("Git branching strategy")
timetable_id = note_id("Study timetable")

activities = [
    # Python decorators — hot (created + many views and edits this week)
    (python_id, "edit", "2026-05-01 09:00:00"),
    (python_id, "view", "2026-05-10 10:00:00"),
    (python_id, "view", "2026-05-12 11:00:00"),
    (python_id, "edit", "2026-05-14 14:00:00"),
    (python_id, "view", "2026-05-15 09:00:00"),
    (python_id, "view", "2026-05-16 10:30:00"),
    (python_id, "edit", "2026-05-18 14:30:00"),
    (python_id, "view", "2026-05-18 15:00:00"),

    # Flask routing — warm (a few edits last week)
    (flask_id,  "edit", "2026-04-10 11:00:00"),
    (flask_id,  "view", "2026-05-05 09:00:00"),
    (flask_id,  "edit", "2026-05-11 10:00:00"),
    (flask_id,  "view", "2026-05-13 14:00:00"),

    # SQL joins — aging (last activity 3 weeks ago)
    (sql_id,    "edit", "2026-03-20 08:00:00"),
    (sql_id,    "view", "2026-04-01 09:00:00"),
    (sql_id,    "edit", "2026-04-28 16:00:00"),

    # HTTP status codes — stale (last activity 6 weeks ago)
    (http_id,   "edit", "2026-02-14 12:00:00"),
    (http_id,   "view", "2026-03-01 10:00:00"),
    (http_id,   "edit", "2026-04-07 09:00:00"),

    # Git branching — dormant (last activity 4 months ago)
    (git_id,    "edit", "2026-01-05 10:00:00"),
    (git_id,    "view", "2026-01-10 11:00:00"),
    (git_id,    "edit", "2026-01-20 11:00:00"),

    # Bob's timetable — fresh
    (timetable_id, "edit", "2026-05-15 08:00:00"),
    (timetable_id, "view", "2026-05-16 09:00:00"),
    (timetable_id, "edit", "2026-05-17 09:00:00"),
]

conn.executemany(
    "INSERT INTO activity (note_id, event_type, created_at) VALUES (?, ?, ?)",
    activities
)
conn.commit()
print(f"Inserted {len(activities)} activity events")

conn.close()

# ── Summary ───────────────────────────────────────────────────
print("\nSeed complete. Test credentials:")
print("  alice / alice123  (5 notes: hot → dormant)")
print("  bob   / bob123    (2 notes: fresh, aging)")