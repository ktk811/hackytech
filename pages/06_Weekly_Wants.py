import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import utils
import sqlite3
import threading

# Thread-local storage for database connections
thread_local = threading.local()

# Set page config
st.set_page_config(page_title="Weekly Wants", page_icon="📅", layout="wide")

# Check if user is logged in
if not st.session_state.get("logged_in", False):
    st.warning("Please login to access this page.")
    st.switch_page("app.py")

# Title
st.title("📅 Weekly Wants Budget")
st.write("Track and manage your discretionary spending")

# Helper functions for direct database access
def get_db_connection():
    if not hasattr(thread_local, 'conn'):
        thread_local.conn = sqlite3.connect('finance_tracker.db', check_same_thread=False)
        # Enable foreign keys
        thread_local.conn.execute("PRAGMA foreign_keys = ON")
    return thread_local.conn

def get_user_data(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user_data = cursor.fetchone()
    if user_data:
        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, user_data))
    return None

def update_user_budget(username, budget):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET wants_budget = ? WHERE username = ?", 
                  (budget, username))
    conn.commit()
    return cursor.rowcount > 0

def get_weekly_wants_expenses(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calculate current week's start date
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_start = datetime.combine(week_start, datetime.min.time())
    
    # Query for this week's wants expenses
    cursor.execute("""
        SELECT * FROM expenses 
        WHERE username = ? AND type = 'Wants' AND date >= ? AND date <= ?
        ORDER BY date DESC
    """, (username, week_start, today))
    
    results = cursor.fetchall()
    if results:
        columns = [description[0] for description in cursor.description]
        expenses = [dict(zip(columns, row)) for row in results]
        return expenses
    return []

def get_monthly_wants_expenses(username, days=28):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Query for the past X days of wants expenses
    cursor.execute("""
        SELECT * FROM expenses 
        WHERE username = ? AND type = 'Wants' AND date >= ? AND date <= ?
    """, (username, start_date, end_date))
    
    results = cursor.fetchall()
    if results:
        columns = [description[0] for description in cursor.description]
        expenses = [dict(zip(columns, row)) for row in results]
        return expenses
    return []

# Get user data
user = get_user_data(st.session_state.username)
weekly_wants_budget = user.get("wants_budget", 100.0) if user else 100.0

# Current week's wants spending from utils
current_wants_spending = utils.get_weekly_wants_spending(st.session_state.username)

# Main dashboard layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Your Weekly 'Wants' Budget")
    
    # Budget progress
    progress_percentage = min((current_wants_spending / weekly_wants_budget) * 100, 100) if weekly_wants_budget > 0 else 0
    
    # Determine color based on percentage
    if progress_percentage < 70:
        st.success(f"You've spent ${current_wants_spending:.2f} of your ${weekly_wants_budget:.2f} weekly 'wants' budget")
    elif progress_percentage < 90:
        st.warning(f"You've spent ${current_wants_spending:.2f} of your ${weekly_wants_budget:.2f} weekly 'wants' budget")
    else:
        st.error(f"You've spent ${current_wants_spending:.2f} of your ${weekly_wants_budget:.2f} weekly 'wants' budget")
    
    st.progress(progress_percentage / 100)
    
    # Remaining budget
    remaining_budget = max(weekly_wants_budget - current_wants_spending, 0)
    st.metric(
        label="Remaining Budget", 
        value=f"${remaining_budget:.2f}",
        delta=f"{100 - progress_percentage:.1f}% remaining"
    )
    
    # Add reward for staying under budget
    if weekly_wants_budget > 0 and progress_percentage < 90:
        if st.button("🏆 Claim reward for staying under budget (+10 XP)"):
            # Only allow claiming reward if under budget
            utils.add_finpet_xp(st.session_state.username, 10)
            
            # Add special reward if significantly under budget (below 50%)
            if progress_percentage < 50:
                utils.add_finpet_reward(
                    st.session_state.username,
                    "Budget Champion",
                    f"Used less than 50% of your weekly wants budget (${weekly_wants_budget:.2f})",
                    "🎖️"
                )
                st.success("Congratulations! You've earned the Budget Champion reward (+10 XP)!")
            else:
                st.success("Great job staying under budget! +10 XP for your FinPet")
            
            st.rerun()
    
    # Budget adjustment form
    st.subheader("Adjust Your Budget")
    with st.form("adjust_budget"):
        new_budget = st.number_input(
            "Weekly 'Wants' Budget ($)", 
            min_value=0.0, 
            value=weekly_wants_budget,
            step=10.0
        )
        
        submit_button = st.form_submit_button("Update Budget")
        
        if submit_button:
            if update_user_budget(st.session_state.username, new_budget):
                st.success(f"Budget updated to ${new_budget:.2f} per week")
                st.rerun()
            else:
                st.error("Failed to update budget. Please try again.")
    
    # Weekly spending chart
    st.subheader("Weekly 'Wants' Spending History")
    
    # Get data for the past 4 weeks
    monthly_expenses = get_monthly_wants_expenses(st.session_state.username)
    
    if monthly_expenses:
        # Convert to DataFrame
        df = pd.DataFrame(monthly_expenses)
        df['date'] = pd.to_datetime(df['date'])
        df['week'] = df['date'].dt.isocalendar().week
        
        # Group by week
        weekly_spending = df.groupby('week')['amount'].sum().reset_index()
        
        # Create labels for weeks
        weeks = []
        for week_num in weekly_spending['week']:
            weeks.append(f"Week {week_num}")
        
        weekly_spending['week_label'] = weeks
        
        # Create chart
        chart = alt.Chart(weekly_spending).mark_bar().encode(
            x=alt.X('week_label:N', title='Week'),
            y=alt.Y('amount:Q', title='Amount ($)'),
            color=alt.condition(
                alt.datum.amount > weekly_wants_budget,
                alt.value('red'),  # over budget
                alt.value('blue')  # within budget
            ),
            tooltip=['week_label:N', 'amount:Q']
        ).properties(
            title='Weekly Wants Spending',
            width='container',
            height=300
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)
        
        # Compare to budget
        for i, row in weekly_spending.iterrows():
            if row['amount'] > weekly_wants_budget:
                over_amount = row['amount'] - weekly_wants_budget
                st.warning(f"{row['week_label']}: Over budget by ${over_amount:.2f}")
            else:
                under_amount = weekly_wants_budget - row['amount']
                st.success(f"{row['week_label']}: Under budget by ${under_amount:.2f}")
    else:
        st.info("No 'wants' spending data available for the past 4 weeks.")

with col2:
    st.subheader("This Week's Wants")
    
    # Get current week's wants expenses
    weekly_wants = get_weekly_wants_expenses(st.session_state.username)
    
    if weekly_wants:
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(weekly_wants)
        df['date'] = pd.to_datetime(df['date'])
        
        # Format date for display
        df['formatted_date'] = df['date'].dt.strftime('%m/%d/%Y')
        
        # Display the expenses
        for i, row in df.iterrows():
            with st.expander(f"{row['description']} - ${row['amount']:.2f}", expanded=i==0):
                st.write(f"**Date:** {row['formatted_date']}")
                st.write(f"**Category:** {row['category']}")
                st.write(f"**Amount:** ${row['amount']:.2f}")
                
                # Add context about impact on budget
                percent_of_budget = (row['amount'] / weekly_wants_budget) * 100
                st.write(f"This expense was **{percent_of_budget:.1f}%** of your weekly 'wants' budget.")
    else:
        st.info("You haven't recorded any 'wants' expenses this week.")
    
    # Tips and suggestions
    st.subheader("Tips for Managing 'Wants'")
    
    tips = [
        "Use the 24-hour rule: Wait 24 hours before making non-essential purchases over $50",
        "Try the 50/30/20 rule: 50% for needs, 30% for wants, 20% for savings",
        "Consider if a 'want' purchase will bring lasting joy or just momentary satisfaction",
        "Track your 'wants' spending daily to stay within your budget",
        "Prioritize experiences over material possessions for greater happiness",
        "Set specific spending limits for different 'wants' categories",
        "Activate Zen Mode to help pause and reflect before impulse purchases"
    ]
    
    for tip in tips:
        st.info(tip)
    
    # Link to Zen Mode
    st.subheader("Consider Zen Mode")
    st.write("Activate Zen Mode to help control impulse spending on 'wants'")
    
    if st.button("Go to Zen Mode Settings"):
        st.switch_page("pages/08_Zen_Mode.py")
