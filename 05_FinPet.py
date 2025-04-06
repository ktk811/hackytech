import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import utils
import sqlite3
import threading
import base64
import os
from pathlib import Path

# Thread-local storage for database connections
thread_local = threading.local()

# Set page config
st.set_page_config(page_title="FinPet", page_icon="🐾", layout="wide")

# Check if user is logged in
if not st.session_state.get("logged_in", False):
    st.warning("Please login to access this page.")
    st.switch_page("app.py")

# Title
st.title("🐾 FinPet - Your Financial Companion")

# Helper functions for direct database access
def get_db_connection():
    if not hasattr(thread_local, 'conn'):
        thread_local.conn = sqlite3.connect('finance_tracker.db', check_same_thread=False)
        # Enable foreign keys
        thread_local.conn.execute("PRAGMA foreign_keys = ON")
    return thread_local.conn

def get_finpet_data(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM finpet WHERE username = ?", (username,))
    finpet_data = cursor.fetchone()
    if finpet_data:
        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, finpet_data))
    return None

def get_finpet_rewards(username):
    """Get the rewards for a user's FinPet directly from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT rewards FROM finpet WHERE username = ?", (username,))
    rewards_data = cursor.fetchone()
    
    if rewards_data and rewards_data[0]:
        try:
            import json
            return json.loads(rewards_data[0])
        except Exception as e:
            st.error(f"Error parsing rewards: {e}")
            return []
    return []

def update_finpet_name(username, new_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE finpet SET name = ? WHERE username = ?", 
                  (new_name, username))
    conn.commit()
    return cursor.rowcount > 0

def get_user_goal_count(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM goals 
        WHERE username = ? AND current_amount >= target_amount
    """, (username,))
    count = cursor.fetchone()[0]
    return count

def get_user_expense_count(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM expenses WHERE username = ?", (username,))
    count = cursor.fetchone()[0]
    return count

def get_recent_expenses(username, limit=5):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, description, amount, category, type, date
        FROM expenses 
        WHERE username = ? 
        ORDER BY date DESC
        LIMIT ?
    """, (username, limit))
    
    results = cursor.fetchall()
    if results:
        columns = [description[0] for description in cursor.description]
        expenses = [dict(zip(columns, row)) for row in results]
        return expenses
    return []

# Helper function to load and display GIFs
def get_img_with_href(img_path, target_size=(250, 250)):
    with open(img_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        html = f"""
        <div style="display: flex; justify-content: center; align-items: center; height: 300px;">
            <img src="data:image/gif;base64,{b64}" alt="FinPet" width="{target_size[0]}" height="{target_size[1]}">
        </div>
        """
        return html

# Get user's FinPet data
finpet = utils.get_user_finpet(st.session_state.username)

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader(f"Meet {finpet['name']} - Level {finpet['level']}")
    
    # FinPet visualization based on level
    pet_container = st.container()
    with pet_container:
        # For levels below 10, show egg emoji
        if finpet['level'] < 10:
            st.markdown("""
            <div style="display: flex; justify-content: center; align-items: center; height: 300px;">
                <span style="font-size: 150px;">🥚</span>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='text-align: center;'><b>Egg FinPet (Level up to hatch!)</b></div>", unsafe_allow_html=True)
        
        # For levels 10-19, show first GIF
        elif finpet['level'] < 20:
            gif_path = "static/images/gif1.gif"
            if os.path.exists(gif_path):
                st.markdown(get_img_with_href(gif_path), unsafe_allow_html=True)
                st.markdown("<div style='text-align: center;'><b>Baby FinPet</b></div>", unsafe_allow_html=True)
            else:
                st.error(f"GIF file not found: {gif_path}")
        
        # For levels 20-29, show second GIF
        elif finpet['level'] < 30:
            gif_path = "static/images/gif2.gif"
            if os.path.exists(gif_path):
                st.markdown(get_img_with_href(gif_path), unsafe_allow_html=True)
                st.markdown("<div style='text-align: center;'><b>Teen FinPet</b></div>", unsafe_allow_html=True)
            else:
                st.error(f"GIF file not found: {gif_path}")
        
        # For levels 30+, show third GIF
        else:
            gif_path = "static/images/gif3.gif"
            if os.path.exists(gif_path):
                st.markdown(get_img_with_href(gif_path), unsafe_allow_html=True)
                st.markdown("<div style='text-align: center;'><b>Master FinPet</b></div>", unsafe_allow_html=True)
            else:
                st.error(f"GIF file not found: {gif_path}")
    
    # Progress to next level
    st.subheader("Progress")
    progress = finpet['xp'] / finpet['next_level_xp']
    st.progress(progress)
    st.write(f"XP: {finpet['xp']}/{finpet['next_level_xp']} ({progress*100:.1f}%)")
    
    # FinPet customization
    st.subheader("Customize Your FinPet")
    with st.form("customize_finpet"):
        new_name = st.text_input("Rename your FinPet", value=finpet['name'])
        submit_button = st.form_submit_button("Update Name")
        
        if submit_button and new_name:
            if update_finpet_name(st.session_state.username, new_name):
                st.success(f"Your FinPet is now named {new_name}!")
                st.rerun()
            else:
                st.error("Failed to update FinPet name. Please try again.")

with col2:
    st.subheader("How to Grow Your FinPet")
    
    st.write("""
    Your FinPet grows as you make good financial decisions:
    
    - **+5 XP** for each "Needs" expense (essential spending)
    - **+3 XP** for contributing to savings goals
    - **+25 XP** for completing a savings goal
    - **+10 XP** for staying under your weekly 'wants' budget
    - **+1-10 XP** for adding funds to your account (1 XP per $50 added)
    
    FinPet Evolution Stages:
    - **Level 1-9**: Egg stage
    - **Level 10-19**: Baby FinPet (hatched)
    - **Level 20-29**: Teen FinPet
    - **Level 30+**: Master FinPet
    
    **NEW: Rewards System!**
    Earn special rewards and trophies for:
    - Reaching savings milestones ($100, $500, $1000, $5000)
    - Achieving significant FinPet levels (5, 10, 20, 30)
    - Completing financial goals
    
    Keep making responsible financial choices to evolve your FinPet and collect rewards!
    """)
    
    # FinPet achievements
    st.subheader("Achievements")
    
    # Calculate achievements
    
    # Get total expenses count
    total_expenses = get_user_expense_count(st.session_state.username)
    
    # Get needs ratio
    expenses = utils.get_user_expenses(st.session_state.username)
    df = pd.DataFrame(expenses) if expenses else pd.DataFrame(columns=["type", "amount"])
    
    needs_wants_ratio = 0
    if not df.empty and 'type' in df.columns and df['amount'].sum() > 0:
        needs_wants = df.groupby('type')['amount'].sum().to_dict()
        needs = needs_wants.get('Needs', 0)
        total = df['amount'].sum()
        needs_wants_ratio = (needs / total) if total > 0 else 0
    
    # Get completed goals count
    completed_goals = get_user_goal_count(st.session_state.username)
    
    # Display achievements
    achievements = []
    
    # Level achievements
    if finpet['level'] >= 5:
        achievements.append("🏆 **First Steps**: Reached level 5")
    if finpet['level'] >= 10:
        achievements.append("🏆 **Hatched**: Reached level 10 and hatched from egg")
    if finpet['level'] >= 20:
        achievements.append("🏆 **Growing Up**: Reached level 20 and evolved")
    if finpet['level'] >= 30:
        achievements.append("🏆 **Financial Master**: Reached level 30 and achieved final form")
    
    # Expense tracking achievements
    if total_expenses >= 10:
        achievements.append("📊 **Tracker Beginner**: Recorded 10+ expenses")
    if total_expenses >= 50:
        achievements.append("📊 **Expense Expert**: Recorded 50+ expenses")
    
    # Needs/wants ratio achievements
    if needs_wants_ratio >= 0.6:
        achievements.append("🧠 **Needs-Focused**: 60%+ of spending on needs")
    if needs_wants_ratio >= 0.8:
        achievements.append("🧠 **Frugality Master**: 80%+ of spending on needs")
    
    # Goals achievements
    if completed_goals >= 1:
        achievements.append("🎯 **Goal Getter**: Completed first savings goal")
    if completed_goals >= 3:
        achievements.append("🎯 **Goal Master**: Completed 3+ savings goals")
    
    if achievements:
        for achievement in achievements:
            st.success(achievement)
    else:
        st.info("Start making good financial decisions to earn achievements!")
    
    # Rewards section
    st.subheader("Rewards & Trophies")
    
    # Get user's rewards
    rewards = []
    if 'rewards' in finpet:
        if isinstance(finpet['rewards'], list):
            rewards = finpet['rewards']
        elif isinstance(finpet['rewards'], str):
            try:
                import json
                rewards = json.loads(finpet['rewards'])
            except:
                st.warning("Could not parse rewards from database")
    
    # Display rewards in a pretty format with expandable details
    if rewards:
        for reward in rewards:
            if isinstance(reward, dict):
                icon = reward.get('icon', '🎁')
                name = reward.get('name', 'Unnamed Reward')
                description = reward.get('description', '')
                date_str = "Unknown"
                
                # Format the date if it exists
                if 'date' in reward:
                    try:
                        date_obj = datetime.fromisoformat(reward['date'].replace('Z', '+00:00'))
                        date_str = date_obj.strftime("%m/%d/%Y")
                    except:
                        pass
                
                # Display reward
                with st.expander(f"{icon} {name} - Earned {date_str}"):
                    st.write(description)
    else:
        st.info("Make good financial decisions to earn rewards and trophies!")
    
    # Activity log
    st.subheader("Activity Log")
    
    # Get recent expenses to show activity using direct SQL query
    recent_expenses = get_recent_expenses(st.session_state.username, 5)
    
    if recent_expenses:
        for expense in recent_expenses:
            # Handle date formatting
            date_obj = expense.get("date")
            if isinstance(date_obj, str):
                try:
                    date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
                except:
                    date_obj = None
            
            date_str = date_obj.strftime("%m/%d/%Y") if isinstance(date_obj, datetime) else "Unknown"
            
            # Display expense entry
            if expense.get("type") == "Needs":
                st.write(f"🟢 **{date_str}**: +5 XP for recording a Needs expense: {expense['description']}")
            else:
                st.write(f"🔵 **{date_str}**: Recorded a Wants expense: {expense['description']}")
    else:
        st.info("No recent activity. Add some expenses to see them here!")

# Bottom section for FinPet care
st.markdown("---")
st.subheader("FinPet Interaction")

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("🥩 Feed your FinPet (+3 XP)"):
        utils.add_finpet_xp(st.session_state.username, 3)
        st.success(f"You fed {finpet['name']}! +3 XP")
        st.rerun()

with col2:
    if st.button("✨ Groom your FinPet (+2 XP)"):
        utils.add_finpet_xp(st.session_state.username, 2)
        st.success(f"You groomed {finpet['name']}! +2 XP")
        st.rerun()

with col3:
    if st.button("🎮 Play with your FinPet (+5 XP)"):
        utils.add_finpet_xp(st.session_state.username, 5)
        st.success(f"You played with {finpet['name']}! +5 XP")
        st.rerun()

# Tips at the bottom
st.info("""
**FinPet Care Tips:**
- Feed your FinPet daily for consistent growth
- Make wise financial decisions to earn more XP
- Complete savings goals for big XP boosts
- Your FinPet grows as you improve your financial habits
""")
