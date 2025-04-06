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
    
    # Check if username already exists
    if db.users.find_one({"username": username}):
        return False
    
    # Hash the password
    hashed_password = hash_password(password)
    
    # Store the new user
    user = {
        "username": username,
        "password": hashed_password,
        "zen_mode": 0,           # SQLite uses integers for booleans
        "wants_budget": 100.0    # Default weekly budget for wants
    }
    db.users.insert_one(user)
    
    # Initialize user's funds
    funds = {
        "username": username,
        "balance": 0
    }
    db.funds.insert_one(funds)
    
    # Get current time as string for SQLite
    current_time = datetime.now().isoformat()
    
    # Initialize FinPet
    finpet = {
        "username": username,
        "level": 1,
        "xp": 0,
        "next_level_xp": 100,
        "name": "Penny",
        "last_fed": current_time,
        "rewards": "[]"  # Store rewards as JSON-formatted string
    }
    db.finpet.insert_one(finpet)
    
    return True

def login(username, password):
    """Verify username and password."""
    db = get_db()
    
    user = db.users.find_one({"username": username})
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
