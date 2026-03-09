import sqlite3, hashlib, secrets, os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'omni.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS user_charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chart_type TEXT NOT NULL,
            chart_image TEXT NOT NULL,
            insight TEXT,
            dataset_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS user_datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            rows INTEGER,
            cols INTEGER,
            data_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    salt = secrets.token_hex(16)
    h = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{h}"

def verify_password(password, stored):
    try:
        salt, h = stored.split(':', 1)
        return hashlib.sha256((password + salt).encode()).hexdigest() == h
    except:
        return False

def create_user(username, email, password):
    try:
        conn = get_db()
        conn.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                     (username.strip(), email.strip().lower(), hash_password(password)))
        conn.commit()
        conn.close()
        return True, "Account created successfully"
    except sqlite3.IntegrityError as e:
        return False, "Username or email already exists"

def login_user(username_or_email, password):
    conn = get_db()
    user = conn.execute(
        'SELECT * FROM users WHERE username=? OR email=?',
        (username_or_email, username_or_email.lower())
    ).fetchone()
    conn.close()
    if not user:
        return None, "User not found"
    if not verify_password(password, user['password_hash']):
        return None, "Incorrect password"
    token = secrets.token_hex(32)
    conn = get_db()
    conn.execute('INSERT INTO sessions (token, user_id) VALUES (?, ?)', (token, user['id']))
    conn.commit()
    conn.close()
    return token, "Login successful"

def get_user_from_token(token):
    if not token:
        return None
    conn = get_db()
    row = conn.execute(
        'SELECT u.* FROM users u JOIN sessions s ON u.id=s.user_id WHERE s.token=?', (token,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def logout_user(token):
    conn = get_db()
    conn.execute('DELETE FROM sessions WHERE token=?', (token,))
    conn.commit()
    conn.close()

def save_chart(user_id, chart_type, image_b64, insight, dataset_name):
    conn = get_db()
    conn.execute(
        'INSERT INTO user_charts (user_id, chart_type, chart_image, insight, dataset_name) VALUES (?,?,?,?,?)',
        (user_id, chart_type, image_b64, insight, dataset_name)
    )
    conn.commit()
    conn.close()

def get_user_charts(user_id):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM user_charts WHERE user_id=? ORDER BY created_at DESC LIMIT 50', (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_chart(chart_id, user_id):
    conn = get_db()
    conn.execute('DELETE FROM user_charts WHERE id=? AND user_id=?', (chart_id, user_id))
    conn.commit()
    conn.close()

def save_dataset(user_id, filename, rows, cols, data_json):
    conn = get_db()
    conn.execute('DELETE FROM user_datasets WHERE user_id=?', (user_id,))
    conn.execute(
        'INSERT INTO user_datasets (user_id, filename, rows, cols, data_json) VALUES (?,?,?,?,?)',
        (user_id, filename, rows, cols, data_json)
    )
    conn.commit()
    conn.close()

def get_user_dataset(user_id):
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM user_datasets WHERE user_id=? ORDER BY created_at DESC LIMIT 1', (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
