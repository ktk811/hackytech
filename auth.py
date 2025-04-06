import sqlite3
from hashlib import sha256

def get_db():
    return sqlite3.connect("database.db")

def hash_password(password):
    return sha256(password.encode()).hexdigest()

def register(username, password):
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def login(username, password):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    return result and result[0] == hash_password(password)

def logout():
    pass  # Handled in app.py
