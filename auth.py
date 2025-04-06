import streamlit as st
from hashlib import sha256
from database import get_db
from datetime import datetime

def hash_password(password):
    """Hash a password for storing."""
    return sha256(password.encode()).hexdigest()

def register(username, password):
    """Register a new user."""
    db = get_db()
    cursor = db.cursor()
    
    # Check if username already exists
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if cursor.fetchone() is not None:
        return False
    
    # Hash the password
    hashed_password = hash_password(password)
    
    # Store the new user
    cursor.execute(
        "INSERT INTO users (username, password, zen_mode, wants_budget) VALUES (?, ?, ?, ?)",
        (username, hashed_password, 0, 100.0)
    )
    
    # Initialize user's funds
    cursor.execute(
        "INSERT INTO funds (username, balance) VALUES (?, ?)",
        (username, 0)
    )
    
    # Get current time as string for SQLite
    current_time = datetime.now().isoformat()
    
    # Initialize FinPet
    cursor.execute(
        "INSERT INTO finpet (username, level, xp, next_level_xp, name, last_fed) VALUES (?, ?, ?, ?, ?, ?)",
        (username, 1, 0, 100, "Penny", current_time)
    )
    
    db.commit()
    return True

def login(username, password):
    """Verify username and password."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if not user:
        return False
    
    # Check password
    hashed_password = hash_password(password)
    if user["password"] != hashed_password:
        return False
    
    # Update session state with zen mode status (convert SQLite integer to boolean)
    st.session_state.zen_mode = bool(user.get("zen_mode", 0))
    
    return True

def is_authenticated():
    """Check if user is authenticated in the current session."""
    return st.session_state.get("logged_in", False)

def logout():
    """Log out the current user."""
    st.session_state.logged_in = False
    st.session_state.username = None
