from flask import Flask, render_template, request, redirect, url_for, abort, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_database, init_database
from functools import wraps
import math

app = Flask(__name__)

# Generate with secrets.token(32) and set as an environment variable
app.secret_key = 'dev-secret-change-in-production'

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def log_activity(conn, note_id, event_type):
    conn.execute(
        'INSERT INTO activity (note_id, event_type) VALUES (?, ?)',
        (note_id, event_type)
    )

def calculate_heat(conn, note_id):
    rows = conn.execute(
        '''SELECT event_type, (julianday('now') - julianday(created_at)) * 24 AS hours_ago FROM activity WHERE note_id = ?''',
        (note_id,)
    ).fetchall()
    HALF_LIFE = 168 # Hours in 7 days
    score = 0.0
    for row in rows:
        weight = 10 if row['event_type'] == 'edit' else 3
        score += weight * math.exp(-row['hours_ago'] / HALF_LIFE)
    return min(round(score, 1), 100.0)

def calculate_age(updated_at):
    rows = None
    conn = get_database()
    row = conn.execute(
        "SELECT CAST((julianday('now') - julianday(?)) AS INTEGER) AS days",
        (updated_at,)
    ).fetchone()
    conn.close()
    days = row['days']
    if days < 7:
        return  'fresh',    days
    if days < 30:
        return  'aging',    days
    if days < 90:
        return  'stale',    days
    return      'dormant',  days

@app.route('/')
def index():
    with get_database() as conn:
        notes = conn.execute(
            'SELECT * FROM note WHERE user_id = ? ORDER BY updated_at DESC',
            (session.get('user_id'),)
        ).fetchall()
        notes_with_meta = [
            {
                'note':   note,
                'heat':   calculate_heat(conn, note['id']),
                'age_status': calculate_age(note['updated_at'])[0],
                'age_days':   calculate_age(note['updated_at'])[1],
            }
            for note in notes
        ]
    return render_template('index.html', title='Obsidian clone', notes=notes_with_meta)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            return render_template('register.html', error='Both fields are required.')
        with get_database() as conn:
            existing = conn.execute(
                'SELECT id FROM user WHERE username = ?', (username,)
            ).fetchone()
            if existing:
                return render_template('register.html', error='Username already taken.')
            conn.execute(
                'INSERT INTO user (username, password_hash) VALUES (?, ?)',
                (username, generate_password_hash(password))
            )
        return redirect(url_for('index'))
    return render_template('register.html', error=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        with get_database() as conn:
            user = conn.execute(
                'SELECT * FROM user WHERE username = ?', (username,)
            ).fetchone()
        if user is None or not check_password_hash(user['password_hash'], password):
            return render_template('login.html', error='Invalid username or password.')
        session['user_id']  = user['id']
        session['username'] = user['username']
        return redirect(url_for('index'))
    return render_template('login.html', error=None)

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/notes/new', methods=['GET', 'POST'])
@login_required
def new_note():
    if request.method == 'POST':
        title   = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        if not title:
            return render_template('note_form.html', note=None, error='Title is required.')
        with get_database() as conn:
            cursor = conn.execute(
                'INSERT INTO note (user_id, title, content) VALUES (?, ?, ?)',
                (session['user_id'], title, content)
            )
            log_activity(conn, cursor.lastrowid, 'edit')
        return redirect(url_for('index'))
    return render_template('note_form.html', note=None, error=None)

@app.route('/notes/<int:note_id>')
@login_required
def view_note(note_id):
    with get_database() as conn:
        note = conn.execute(
            'SELECT * FROM note WHERE id = ? AND user_id = ?',
            (note_id, session['user_id'])
        ).fetchone()
        if note is None:
            abort(404)
        log_activity(conn, note_id, 'view')
        heat = calculate_heat(conn, note_id)
    age_status, age_days = calculate_age(note['updated_at'])
    return render_template('note.html', note=note, heat=heat,
                           age_status=age_status, age_days=age_days)

@app.route('/notes/<int:note_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_note(note_id):
    with get_database() as conn:
        note = conn.execute(
            'SELECT * FROM note WHERE id = ? AND user_id = ?',
            (note_id, session['user_id'])
        ).fetchone()
    if note is None:
        abort(404)
    if request.method == 'POST':
        title   = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        if not title:
            return render_template('note_form.html', note=note, error='Title is required.')
        with get_database() as conn:
            conn.execute(
                '''UPDATE note
                   SET title = ?, content = ?, updated_at = datetime('now')
                   WHERE id = ? AND user_id = ?''',
                (title, content, note_id, session['user_id'])
            )
            log_activity(conn, note_id, 'edit')
        return redirect(url_for('view_note', note_id=note_id))
    return render_template('note_form.html', note=note, error=None)

@app.route('/notes/<int:note_id>/delete', methods=['POST'])
@login_required
def delete_note(note_id):
    with get_database() as conn:
        note = conn.execute(
            'SELECT id FROM note WHERE id = ? AND user_id = ?',
            (note_id, session['user_id'])
        ).fetchone()
    if note is None:
        abort(404)
    with get_database() as conn:
        conn.execute(
            'DELETE FROM note WHERE id = ? AND user_id = ?',
            (note_id, session['user_id'])
        )
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_database()
    app.run(debug=True)