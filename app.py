import streamlit as st
import os
import sqlite3

# Set page config; must be the first Streamlit command
st.set_page_config(
    page_title="Personal Finance Manager",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load custom CSS
def load_css():
    css_file = os.path.join(os.path.dirname(__file__), ".streamlit/style.css")
    if os.path.exists(css_file):
        with open(css_file) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
load_css()

# --- SQLite Database Initialization ---
def initialize_db():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Create all tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        zen_mode INTEGER DEFAULT 0,
        wants_budget REAL DEFAULT 100.0
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        category TEXT,
        type TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS funds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        balance REAL DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        target_amount REAL NOT NULL,
        current_amount REAL DEFAULT 0,
        date_created TEXT,
        completed INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS finpet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        next_level_xp INTEGER DEFAULT 75,
        name TEXT DEFAULT 'Penny',
        last_fed TEXT,
        rewards TEXT DEFAULT '[]',
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    conn.commit()
    return conn

# Initialize database
db_conn = initialize_db()

# --- Session State Initialization ---
session_vars = {
    "logged_in": False,
    "username": None,
    "theme_mode": "light",
    "zen_mode": False,
    "show_registration": False,
    "current_page": "Home"
}

for key, value in session_vars.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- Authentication Functions ---
def hash_password(password):
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def register(username, password):
    try:
        cursor = db_conn.cursor()
        hashed_pw = hash_password(password)
        
        # Insert user
        cursor.execute("""
            INSERT INTO users (username, password)
            VALUES (?, ?)
        """, (username, hashed_pw))
        
        # Initialize funds
        cursor.execute("""
            INSERT INTO funds (user_id, balance)
            VALUES ((SELECT id FROM users WHERE username = ?), 0)
        """, (username,))
        
        # Initialize FinPet
        cursor.execute("""
            INSERT INTO finpet (user_id, name)
            VALUES ((SELECT id FROM users WHERE username = ?), 'Penny')
        """, (username,))
        
        db_conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def login(username, password):
    cursor = db_conn.cursor()
    hashed_pw = hash_password(password)
    
    cursor.execute("""
        SELECT id, zen_mode FROM users 
        WHERE username = ? AND password = ?
    """, (username, hashed_pw))
    
    user = cursor.fetchone()
    if user:
        st.session_state.zen_mode = bool(user[1])
        return True
    return False

def logout():
    st.session_state.clear()
    st.session_state.update(session_vars)

# --- Auth Pages ---
def show_login_page():
    st.title("🔐 Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if login(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid credentials")
    if st.button("Register"):
        st.session_state.show_registration = True
        st.rerun()

def show_registration_page():
    st.title("📝 Register")
    with st.form("register_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        if st.form_submit_button("Register"):
            if password == confirm:
                if register(username, password):
                    st.success("Registration successful! Please login")
                    st.session_state.show_registration = False
                    st.rerun()
                else:
                    st.error("Username exists")
            else:
                st.error("Passwords mismatch")

# --- Main App ---
if not st.session_state.logged_in:
    show_registration_page() if st.session_state.show_registration else show_login_page()
else:
    # Header with user info and navigation
    header_col1, header_col2 = st.columns([3, 1])
    
    with header_col1:
        st.title("💰 Personal Finance Manager")
    
    with header_col2:
        st.write(f"👤 {st.session_state.username}")
        if st.button("Logout", key="logout_top"):
            logout()
            st.session_state.clear()
            st.session_state.update(required_session_vars)
            st.rerun()

    # Horizontal navigation menu with functional buttons
    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
    
    with nav_col1:
        with st.container():
            st.markdown('<div class="horizontal-nav">', unsafe_allow_html=True)
            home = st.button("📊 Dashboard", key="nav_home", use_container_width=True)
            add_expense = st.button("➕ Add Expense", key="nav_add_expense", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if home:
                st.switch_page("app.py")
            if add_expense:
                st.switch_page("pages/02_Add_Expense.py")
    
    with nav_col2:
        with st.container():
            st.markdown('<div class="horizontal-nav">', unsafe_allow_html=True)
            funds_goals = st.button("💵 Funds & Goals", key="nav_funds_goals", use_container_width=True)
            expense_history = st.button("📜 History", key="nav_history", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if funds_goals:
                st.switch_page("pages/03_Funds_Goals.py")
            if expense_history:
                st.switch_page("pages/04_Expense_History.py")
    
    with nav_col3:
        with st.container():
            st.markdown('<div class="horizontal-nav">', unsafe_allow_html=True)
            finpet = st.button("🐾 FinPet", key="nav_finpet", use_container_width=True)
            weekly_wants = st.button("🛍️ Weekly Wants", key="nav_weekly", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if finpet:
                st.switch_page("pages/05_FinPet.py")
            if weekly_wants:
                st.switch_page("pages/06_Weekly_Wants.py")
    
    with nav_col4:
        with st.container():
            st.markdown('<div class="horizontal-nav">', unsafe_allow_html=True)
            ai_chatbot = st.button("🤖 AI Assistant", key="nav_chatbot", use_container_width=True)
            zen_mode = st.button("🧘 Zen Mode", key="nav_zen", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if ai_chatbot:
                st.switch_page("pages/07_AI_Chatbot.py")
            if zen_mode:
                st.switch_page("pages/08_Zen_Mode.py")
    
    # Settings and theme section
    with st.expander("⚙️ Settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            theme_mode = st.radio(
                "Theme",
                ["Light Mode", "Dark Mode"],
                index=0 if st.session_state.theme_mode == "light" else 1,
                horizontal=True
            )
            st.session_state.theme_mode = "light" if theme_mode == "Light Mode" else "dark"
        
        with col2:
            if st.session_state.zen_mode:
                st.success("🧘 Zen Mode is active")
            else:
                st.info("🧘 Zen Mode is inactive")
        
        if st.button("Logout", key="logout_button"):
            logout()
            st.session_state.clear()
            st.session_state.update(required_session_vars)
            st.rerun()
    
    # Divider after navigation
    st.markdown("<hr style='margin: 1rem 0; border-color: #E0E0E0;'>", unsafe_allow_html=True)
    
    # Welcome dashboard overview
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Welcome to your financial dashboard!")
        st.markdown("""
        This application helps you manage your personal finances, track expenses, 
        set savings goals, and make better financial decisions.
        
        Use the navigation menu above to:
        - View your financial summary
        - Add and categorize expenses
        - Manage funds and savings goals
        - Review expense history
        - Interact with your FinPet
        - Track weekly discretionary spending
        - Get AI-powered financial advice
        - Activate Zen Mode for mindful spending
        """)
    
    with col2:
        st.info("Click on any of the navigation links above to access different features.")
        st.metric(label="Current Balance", value=f"${utils.get_current_balance():.2f}")
        st.metric(
            label="This Week's Expenses", 
            value=f"${utils.get_weekly_expenses():.2f}",
            delta=f"{utils.get_expense_trend():.1f}%"
        )
        st.button("Go to Home Dashboard →", on_click=lambda: st.switch_page("pages/01_Home.py"))
