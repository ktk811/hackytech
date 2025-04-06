import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import matplotlib.pyplot as plt
import random
import json
from ml_models import predict_expense_type, predict_expense_category
import sqlite3

def get_db():
    # Connect to (or create) your SQLite database file
    conn = sqlite3.connect("finance.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Allows access by column name
    return conn

# ------------------------
# Database utility functions
# ------------------------

def get_user_expenses(username):
    """Get all expenses for a specific user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses WHERE username = ?", (username,))
    rows = cursor.fetchall()
    # Convert rows to list of dictionaries
    columns = [desc[0] for desc in cursor.description]
    expenses = [dict(zip(columns, row)) for row in rows]
    # Convert date strings back to datetime objects
    for expense in expenses:
        if expense.get('date'):
            try:
                expense['date'] = datetime.fromisoformat(expense['date'])
            except (ValueError, TypeError):
                expense['date'] = datetime.now()
    return expenses

def get_user_funds(username):
    """Get funds for a specific user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM funds WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row is None:
        # Initialize funds if not exists
        cursor.execute("INSERT INTO funds (username, balance) VALUES (?, ?)", (username, 0))
        conn.commit()
        funds = {"username": username, "balance": 0}
    else:
        columns = [desc[0] for desc in cursor.description]
        funds = dict(zip(columns, row))
    return funds

def get_user_goals(username):
    """Get all savings goals for a specific user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM goals WHERE username = ?", (username,))
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    goals = [dict(zip(columns, row)) for row in rows]
    return goals

def get_user_finpet(username):
    """Get FinPet status for a specific user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM finpet WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row is None:
        # Initialize FinPet if not exists
        current_time = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO finpet (username, level, xp, next_level_xp, name, last_fed, rewards) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (username, 1, 0, 75, "Penny", current_time, json.dumps([]))
        )
        conn.commit()
        finpet = {
            "username": username,
            "level": 1,
            "xp": 0,
            "next_level_xp": 75,
            "name": "Penny",
            "last_fed": current_time,
            "rewards": []
        }
    else:
        columns = [desc[0] for desc in cursor.description]
        finpet = dict(zip(columns, row))
        # Convert last_fed to datetime
        if finpet.get('last_fed'):
            try:
                finpet['last_fed'] = datetime.fromisoformat(finpet['last_fed'])
            except:
                finpet['last_fed'] = datetime.now()
        # Ensure rewards is a list
        if isinstance(finpet.get('rewards'), str):
            try:
                finpet['rewards'] = json.loads(finpet['rewards'])
            except json.JSONDecodeError:
                finpet['rewards'] = []
        elif finpet.get('rewards') is None:
            finpet['rewards'] = []
    return finpet

def get_zen_mode_status(username):
    """Get Zen mode status for a user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT zen_mode FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row:
        return bool(row[0])
    return False

def update_zen_mode(username, status):
    """Update Zen mode status for a user."""
    conn = get_db()
    status_int = 1 if status else 0
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET zen_mode = ? WHERE username = ?", (status_int, username))
    conn.commit()
    st.session_state.zen_mode = status

def add_expense(username, description, amount, date=None, category=None, expense_type=None):
    """Add a new expense for a user."""
    if date is None:
        date = datetime.now()
    date_str = date.isoformat()
    
    # Use ML to predict category and type if not provided
    if category is None:
        category = predict_expense_category(description)
    if expense_type is None:
        expense_type = predict_expense_type(description)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (username, description, amount, date, category, type) VALUES (?, ?, ?, ?, ?, ?)",
        (username, description, float(amount), date_str, category, expense_type)
    )
    conn.commit()
    
    # Update balance
    update_balance(username, -float(amount))
    
    # Update FinPet XP if it's a "Needs" expense (responsible spending)
    if expense_type == "Needs":
        add_finpet_xp(username, 5)
    
    expense = {
        "username": username,
        "description": description,
        "amount": float(amount),
        "date": date,  # Return datetime object
        "category": category,
        "type": expense_type
    }
    return expense

def add_funds(username, amount, description="Deposit"):
    """Add funds to user's balance."""
    conn = get_db()
    cursor = conn.cursor()
    # Create the fund_transactions table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fund_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT,
        date TEXT NOT NULL,
        FOREIGN KEY (username) REFERENCES users(username)
    )
    ''')
    conn.commit()
    
    fund_entry = {
        "username": username,
        "amount": float(amount),
        "description": description,
        "date": datetime.now().isoformat()
    }
    
    cursor.execute('''
    INSERT INTO fund_transactions (username, amount, description, date)
    VALUES (?, ?, ?, ?)
    ''', (fund_entry["username"], fund_entry["amount"], fund_entry["description"], fund_entry["date"]))
    conn.commit()
    fund_entry["id"] = cursor.lastrowid
    
    # Update the user's balance with the new deposit
    update_balance(username, float(amount))
    
    # Add FinPet XP for adding funds (savings behavior)
    xp_amount = min(10, int(float(amount) / 50))
    if xp_amount > 0:
        add_finpet_xp(username, xp_amount)
    
    # Check for savings rewards
    funds = get_user_funds(username)
    current_balance = funds.get("balance", 0)
    check_and_add_savings_rewards(username, current_balance)
    
    return fund_entry

def update_balance(username, amount_change):
    """Update user's balance by the given amount."""
    conn = get_db()
    funds = get_user_funds(username)
    current_balance = funds.get("balance", 0)
    new_balance = current_balance + amount_change
    cursor = conn.cursor()
    cursor.execute("UPDATE funds SET balance = ? WHERE username = ?", (new_balance, username))
    conn.commit()

def add_goal(username, name, target_amount, current_amount=0):
    """Add a new savings goal."""
    conn = get_db()
    date_created = datetime.now().isoformat()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO goals (username, name, target_amount, current_amount, date_created, completed) VALUES (?, ?, ?, ?, ?, ?)",
        (username, name, float(target_amount), float(current_amount), date_created, 0)
    )
    conn.commit()
    goal_id = cursor.lastrowid
    goal = {
        "id": goal_id,
        "username": username,
        "name": name,
        "target_amount": float(target_amount),
        "current_amount": float(current_amount),
        "date_created": date_created,
        "completed": 0
    }
    return goal

def update_goal(goal_id, amount_change):
    """Update progress towards a goal."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))
    row = cursor.fetchone()
    if row is None:
        return 0, False
    columns = [desc[0] for desc in cursor.description]
    goal = dict(zip(columns, row))
    new_amount = goal["current_amount"] + amount_change
    completed = new_amount >= goal["target_amount"]
    completed_int = 1 if completed else 0
    cursor.execute("UPDATE goals SET current_amount = ?, completed = ? WHERE id = ?", (new_amount, completed_int, goal_id))
    conn.commit()
    
    # Add FinPet XP for goal progress
    if completed:
        add_finpet_xp(goal["username"], 25)  # Bonus XP for completing a goal
    else:
        add_finpet_xp(goal["username"], 3)  # Small XP for progress
    
    return new_amount, completed

def add_finpet_reward(username, reward_name, description, icon="🎁"):
    """Add a reward to the user's FinPet."""
    conn = get_db()
    finpet = get_user_finpet(username)
    reward = {
        "name": reward_name,
        "description": description,
        "icon": icon,
        "date": datetime.now().isoformat()
    }
    rewards = finpet.get("rewards", [])
    if not isinstance(rewards, list):
        try:
            rewards = json.loads(rewards)
            if not isinstance(rewards, list):
                rewards = []
        except json.JSONDecodeError:
            rewards = []
    rewards.append(reward)
    cursor = conn.cursor()
    cursor.execute("UPDATE finpet SET rewards = ? WHERE username = ?", (json.dumps(rewards), username))
    conn.commit()
    return reward

def check_and_add_savings_rewards(username, amount_saved):
    """Check if user qualifies for savings-based rewards and add them."""
    milestones = [
        (100, "Saving Starter", "Saved your first $100", "💰"),
        (500, "Penny Pincher", "Reached $500 in savings", "🪙"),
        (1000, "Money Master", "Saved $1,000", "💵"),
        (5000, "Wealth Builder", "Accumulated $5,000 in savings", "🏆")
    ]
    
    rewards_added = []
    finpet = get_user_finpet(username)
    existing_rewards = [r.get("name") for r in finpet.get("rewards", [])]
    
    for milestone, name, desc, icon in milestones:
        if amount_saved >= milestone and name not in existing_rewards:
            reward = add_finpet_reward(username, name, desc, icon)
            rewards_added.append(reward)
            bonus_xp = milestone // 100  # 1 XP per $100 saved at milestone
            add_finpet_xp(username, bonus_xp)
    
    return rewards_added

def add_finpet_xp(username, xp_amount):
    """Add XP to user's FinPet and handle level ups."""
    conn = get_db()
    finpet = get_user_finpet(username)
    new_xp = finpet["xp"] + xp_amount
    level_up = new_xp >= finpet["next_level_xp"]
    current_time = datetime.now().isoformat()
    cursor = conn.cursor()
    if level_up:
        new_level = finpet["level"] + 1
        new_next_level_xp = int(finpet["next_level_xp"] * 1.3)
        cursor.execute(
            "UPDATE finpet SET xp = ?, level = ?, next_level_xp = ?, last_fed = ? WHERE username = ?",
            (new_xp - finpet["next_level_xp"], new_level, new_next_level_xp, current_time, username)
        )
        conn.commit()
        # Add reward for leveling up at specific milestones
        if new_level in [5, 10, 20, 30]:
            level_milestones = {
                5: ("Level 5 Badge", "Reached level 5 with your FinPet", "🌱"),
                10: ("Hatched", "Your FinPet hatched from its egg at level 10", "🐣"),
                20: ("Evolution", "Your FinPet evolved to its teen form", "✨"),
                30: ("Final Form", "Your FinPet reached its final form", "🌟")
            }
            name, desc, icon = level_milestones[new_level]
            add_finpet_reward(username, name, desc, icon)
        return True  # Indicates level up occurred
    else:
        cursor.execute(
            "UPDATE finpet SET xp = ?, last_fed = ? WHERE username = ?",
            (new_xp, current_time, username)
        )
        conn.commit()
        return False  # No level up

# ------------------------
# Data processing functions
# ------------------------

def get_expenses_df(username):
    """Convert expenses to a pandas DataFrame."""
    expenses = get_user_expenses(username)
    if not expenses:
        return pd.DataFrame(columns=["description", "amount", "date", "category", "type"])
    return pd.DataFrame(expenses)

def get_weekly_spending(username):
    """Get spending data for the last 7 days by day."""
    df = get_expenses_df(username)
    if df.empty:
        dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
        return pd.DataFrame({"date": dates, "amount": [0] * 7})
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        recent_df = df[mask].copy()
        if not recent_df.empty:
            recent_df['day'] = recent_df['date'].dt.strftime('%Y-%m-%d')
            daily_spending = recent_df.groupby('day')['amount'].sum().reset_index()
            all_days = pd.DataFrame({
                'day': [(end_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
            })
            result = pd.merge(all_days, daily_spending, on='day', how='left').fillna(0)
            return result
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
    return pd.DataFrame({"day": dates, "amount": [0] * 7})

def get_category_spending(username):
    """Get spending by category."""
    df = get_expenses_df(username)
    if df.empty or 'category' not in df.columns:
        return pd.DataFrame(columns=["category", "amount"])
    return df.groupby('category')['amount'].sum().reset_index()

def get_needs_wants_ratio(username):
    """Calculate the ratio of needs vs wants spending."""
    df = get_expenses_df(username)
    if df.empty or 'type' not in df.columns:
        return {"Needs": 0, "Wants": 0}
    type_spending = df.groupby('type')['amount'].sum().to_dict()
    return type_spending

# ------------------------
# Dashboard helper functions
# ------------------------

def get_current_balance():
    """Get current balance for the logged-in user."""
    if not st.session_state.logged_in:
        return 0
    funds = get_user_funds(st.session_state.username)
    return funds.get("balance", 0)

def get_weekly_expenses():
    """Get total expenses for the current week."""
    if not st.session_state.logged_in:
        return 0
    df = get_expenses_df(st.session_state.username)
    if df.empty:
        return 0
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        recent_df = df[mask]
        if not recent_df.empty:
            return recent_df['amount'].sum()
    return 0

def get_expense_trend():
    """Calculate the trend in expenses compared to previous week."""
    if not st.session_state.logged_in:
        return 0
    df = get_expenses_df(st.session_state.username)
    if df.empty:
        return 0
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        current_end = datetime.now()
        current_start = current_end - timedelta(days=7)
        prev_end = current_start
        prev_start = prev_end - timedelta(days=7)
        current_total = df[(df['date'] >= current_start) & (df['date'] <= current_end)]['amount'].sum() if not df[(df['date'] >= current_start) & (df['date'] <= current_end)].empty else 0
        prev_total = df[(df['date'] >= prev_start) & (df['date'] <= prev_end)]['amount'].sum() if not df[(df['date'] >= prev_start) & (df['date'] <= prev_end)].empty else 1
        if prev_total == 0:
            return 0
        percent_change = ((current_total - prev_total) / prev_total) * 100
        return percent_change
    return 0

def plot_spending_trend(username):
    """Create a line chart of daily spending for the last 7 days."""
    data = get_weekly_spending(username)
    chart = alt.Chart(data).mark_line(point=True).encode(
        x=alt.X('day:T', title='Date'),
        y=alt.Y('amount:Q', title='Amount ($)'),
        tooltip=['day:T', 'amount:Q']
    ).properties(
        title='Daily Spending (Last 7 Days)',
        width='container',
        height=300
    ).interactive()
    return chart

def plot_category_breakdown(username, chart_type="pie"):
    """Create a chart showing spending by category."""
    data = get_category_spending(username)
    if data.empty:
        return "No category data available"
    if chart_type == "pie":
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.pie(data['amount'], labels=data['category'], autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        plt.title('Spending by Category')
        return fig
    else:  # bar chart
        chart = alt.Chart(data).mark_bar().encode(
            x=alt.X('category:N', title='Category'),
            y=alt.Y('amount:Q', title='Amount ($)'),
            color='category:N',
            tooltip=['category:N', 'amount:Q']
        ).properties(
            title='Spending by Category',
            width='container',
            height=300
        ).interactive()
        return chart

def get_weekly_wants_budget(username):
    """Get the weekly budget for 'wants' expenses."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT wants_budget FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row:
        return row[0]
    return 100.0

def get_weekly_wants_spending(username):
    """Calculate the current week's 'wants' spending."""
    df = get_expenses_df(username)
    if df.empty:
        return 0
    if 'date' in df.columns and 'type' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        current_end = datetime.now()
        current_start = current_end - timedelta(days=7)
        mask = ((df['date'] >= current_start) & (df['date'] <= current_end) & (df['type'] == 'Wants'))
        current_wants = df[mask]
        return current_wants['amount'].sum() if not current_wants.empty else 0
    return 0

def generate_savings_tips(username):
    """Generate personalized savings tips based on spending patterns."""
    df = get_expenses_df(username)
    if df.empty:
        return ["Start tracking your expenses to get personalized savings tips!"]
    tips = []
    tips.append("Set up automatic transfers to your savings account on payday.")
    tips.append("Try the 50/30/20 rule: 50% for needs, 30% for wants, 20% for savings.")
    if 'category' in df.columns:
        category_spending = df.groupby('category')['amount'].sum()
        if 'Food' in category_spending and category_spending['Food'] > 100:
            tips.append("Consider meal planning to reduce your food expenses.")
        if 'Entertainment' in category_spending and category_spending['Entertainment'] > 50:
            tips.append("Look for free or low-cost entertainment options in your area.")
        if 'Shopping' in category_spending and category_spending['Shopping'] > 100:
            tips.append("Try a 24-hour waiting period before making non-essential purchases.")
    if 'type' in df.columns:
        type_spending = df.groupby('type')['amount'].sum()
        total = type_spending.sum()
        if 'Wants' in type_spending and total > 0:
            wants_percentage = (type_spending.get('Wants', 0) / total) * 100
            if wants_percentage > 40:
                tips.append(f"Your 'wants' spending is {wants_percentage:.1f}% of your total. Try to keep it under 30%.")
    if not get_zen_mode_status(username):
        tips.append("Activate Zen Mode to help you save money on non-essential purchases.")
    if len(tips) > 5:
        return random.sample(tips, 5)
    return tips
