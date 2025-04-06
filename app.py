import streamlit as st
import os
import sqlite3

# Set page config; must be the first Streamlit command
st.set_page_config(
    page_title="Personal Finance Manager",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"  # Start with sidebar collapsed
)

# Load custom CSS
def load_css():
    css_file = os.path.join(os.path.dirname(__file__), ".streamlit/style.css")
    if os.path.exists(css_file):
        with open(css_file) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Apply custom styling
load_css()

# --- SQLite Database Initialization ---
def initialize_db():
    # Create (or open) the SQLite database file
    conn = sqlite3.connect("database.db", check_same_thread=False)
    cursor = conn.cursor()

    # Create tables with foreign keys and proper relationships
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS funds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        type TEXT CHECK(type IN ('income', 'expense')) NOT NULL,
        date TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS finpet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        pet_name TEXT NOT NULL,
        balance REAL DEFAULT 0,
        last_fed TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # Enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    return conn

# Global database connection (SQLite)
db_conn = initialize_db()

# --- Import Modules for Authentication and Utility Functions ---
from auth import login, register, is_authenticated, logout
import utils

# --- Initialize Session State Variables ---
required_session_vars = {
    "logged_in": False,
    "username": None,
    "theme_mode": "light",
    "zen_mode": False,
    "show_registration": False,
    "current_page": "Home"
}

for key, value in required_session_vars.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Store the database connection in session state
st.session_state.db_conn = db_conn

# --- Authentication Screens ---
def show_login_page():
    st.title("🔐 Login to Your Finance Dashboard")
    
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if username and password:
                if login(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success(f"Welcome back, {username}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password. Please try again.")
            else:
                st.warning("Please enter both username and password.")
    
    st.markdown("---")
    st.markdown("Don't have an account?")
    if st.button("Register"):
        st.session_state.show_registration = True
        st.rerun()

def show_registration_page():
    st.title("📝 Create Your Account")
    
    with st.form("registration_form"):
        username = st.text_input("Username", key="reg_username")
        password = st.text_input("Password", type="password", key="reg_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")
        submit_button = st.form_submit_button("Register")
        
        if submit_button:
            if username and password and confirm_password:
                if password != confirm_password:
                    st.error("Passwords do not match. Please try again.")
                else:
                    if register(username, password):
                        st.success("Registration successful! Please login.")
                        st.session_state.show_registration = False
                        st.rerun()
                    else:
                        st.error("Username already exists. Please choose another one.")
            else:
                st.warning("Please fill in all fields.")
    
    st.markdown("---")
    st.markdown("Already have an account?")
    if st.button("Login"):
        st.session_state.show_registration = False
        st.rerun()

# --- Main App Flow ---
if not st.session_state.logged_in:
    if st.session_state.show_registration:
        show_registration_page()
    else:
        show_login_page()
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
