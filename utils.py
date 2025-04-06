import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import matplotlib.pyplot as plt
from database import get_db
import random
import json
from ml_models import predict_expense_type, predict_expense_category
from datetime import datetime
# ------------------------
# Database utility functions
# ------------------------

def get_user_expenses(username):
    """Get all expenses for a specific user."""
    db = get_db()
    expenses = list(db.expenses.find({"username": username}))
    # Convert date strings back to datetime objects
    for expense in expenses:
        if 'date' in expense and expense['date']:
            try:
                expense['date'] = datetime.fromisoformat(expense['date'])
            except (ValueError, TypeError):
                expense['date'] = datetime.now()
    return expenses

def get_user_funds(username):
    """Get funds for a specific user."""
    db = get_db()
    funds = db.funds.find_one({"username": username})
    if not funds:
        # Initialize funds if not exists
        funds = {"username": username, "balance": 0}
        db.funds.insert_one(funds)
    return funds

def get_user_goals(username):
    """Get all savings goals for a specific user."""
    db = get_db()
    goals = list(db.goals.find({"username": username}))
    return goals

def get_user_finpet(username):
    """Get finpet status for a specific user."""
    db = get_db()
    finpet = db.finpet.find_one({"username": username})
    if not finpet:
        # Initialize FinPet if not exists
        current_time = datetime.now().isoformat()
        finpet = {
            "username": username,
            "level": 1,
            "xp": 0,
            "next_level_xp": 75,  # Reduced from 100 to 75
            "name": "Penny",
            "last_fed": current_time,
            "rewards": []  # New field to track rewards
        }
        db.finpet.insert_one(finpet)
    else:
        # Convert last_fed from string to datetime if it exists
        if 'last_fed' in finpet and finpet['last_fed']:
            try:
                finpet['last_fed'] = datetime.fromisoformat(finpet['last_fed'])
            except (ValueError, TypeError):
                finpet['last_fed'] = datetime.now()
        
        # Make sure rewards field exists
        if 'rewards' not in finpet:
            db.finpet.update_one(
                {"username": username},
                {"$set": {"rewards": []}}
            )
            finpet['rewards'] = []
    
    return finpet

def get_zen_mode_status(username):
    """Get Zen mode status for a user."""
    db = get_db()
    user = db.users.find_one({"username": username})
    if user and "zen_mode" in user:
        # Convert SQLite integer to boolean
        return bool(user["zen_mode"])
    return False

def update_zen_mode(username, status):
    """Update Zen mode status for a user."""
    db = get_db()
    # Convert boolean to SQLite integer (0 or 1)
    status_int = 1 if status else 0
    
    db.users.update_one(
        {"username": username},
        {"$set": {"zen_mode": status_int}}
    )
    st.session_state.zen_mode = status

def add_expense(username, description, amount, date=None, category=None, expense_type=None):
    """Add a new expense for a user."""
    if date is None:
        date = datetime.now()
    
    # Convert datetime to string for SQLite
    date_str = date.isoformat()
    
    # Use ML to predict category and type if not provided
    if category is None:
        category = predict_expense_category(description)
    if expense_type is None:
        expense_type = predict_expense_type(description)
    
    db = get_db()
    expense = {
        "username": username,
        "description": description,
        "amount": float(amount),
        "date": date_str,
        "category": category,
        "type": expense_type
    }
    db.expenses.insert_one(expense)
    
    # Update balance
    update_balance(username, -float(amount))
    
    # Update FinPet XP if it's a "needs" expense (responsible spending)
    if expense_type == "Needs":
        add_finpet_xp(username, 5)  # 5 XP for needs expenses
    
    # Add back the datetime object for immediate use
    expense["date"] = date
    return expense

from datetime import datetime

from datetime import datetime

def add_funds(username, amount, description="Deposit"):
    """Add funds to user's balance."""
    # Get the SQLite connection from your get_db() function
    db = get_db()
    
    # Create the fund_transactions table if it doesn't exist
    db.execute('''
    CREATE TABLE IF NOT EXISTS fund_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT,
        date TEXT NOT NULL,
        FOREIGN KEY (username) REFERENCES users(username)
    )
    ''')
    db.commit()
    
    # Create the fund entry dictionary with the current timestamp
    fund_entry = {
        "username": username,
        "amount": float(amount),
        "description": description,
        "date": datetime.now().isoformat()
    }
    
    # Insert the new fund entry into the fund_transactions table using SQL
    cursor = db.cursor()
    cursor.execute('''
    INSERT INTO fund_transactions (username, amount, description, date)
    VALUES (?, ?, ?, ?)
    ''', (fund_entry["username"], fund_entry["amount"], fund_entry["description"], fund_entry["date"]))
    db.commit()
    
    # Optionally, add the newly created record's ID into the dictionary
    fund_entry["id"] = cursor.lastrowid
    
    # Update the user's balance with the new deposit
    update_balance(username, float(amount))
    
    # Add FinPet XP for adding funds (savings behavior)
    # 1 XP per $50 deposited, capped at 10 XP
    xp_amount = min(10, int(float(amount) / 50))
    if xp_amount > 0:
        add_finpet_xp(username, xp_amount)
    
    # Get the current balance to check for savings milestones
    funds = get_user_funds(username)
    current_balance = funds.get("balance", 0)
    
    # Check if the user qualifies for savings rewards
    check_and_add_savings_rewards(username, current_balance)
    
    return fund_entry



def update_balance(username, amount_change):
    """Update user's balance by the given amount."""
    db = get_db()
    
    # Get current balance
    funds = get_user_funds(username)
    current_balance = funds.get("balance", 0)
    
    # Calculate new balance
    new_balance = current_balance + amount_change
    
    # Update the balance
    db.funds.update_one(
        {"username": username},
        {"$set": {"balance": new_balance}}
    )

def add_goal(username, name, target_amount, current_amount=0):
    """Add a new savings goal."""
    db = get_db()
    
    # Convert datetime to string for SQLite
    date_created = datetime.now().isoformat()
    
    # In SQLite, boolean is represented as integer
    goal = {
        "username": username,
        "name": name,
        "target_amount": float(target_amount),
        "current_amount": float(current_amount),
        "date_created": date_created,
        "completed": 0  # 0 for False in SQLite
    }
    db.goals.insert_one(goal)
    return goal

def update_goal(goal_id, amount_change):
    """Update progress towards a goal."""
    db = get_db()
    
    # In SQLite, goal_id is an integer
    goal = db.goals.find_one({"id": goal_id})
    if not goal:
        return 0, False
    
    new_amount = goal["current_amount"] + amount_change
    completed = new_amount >= goal["target_amount"]
    
    # Convert completed to integer for SQLite
    completed_int = 1 if completed else 0
    
    db.goals.update_one(
        {"id": goal_id},
        {
            "$set": {
                "current_amount": new_amount,
                "completed": completed_int
            }
        }
    )
    
    # Add FinPet XP for goal progress
    if completed:
        add_finpet_xp(goal["username"], 25)  # Bonus XP for completing a goal
    else:
        add_finpet_xp(goal["username"], 3)  # Small XP for progress
    
    return new_amount, completed

def add_finpet_reward(username, reward_name, description, icon="🎁"):
    """Add a reward to the user's FinPet."""
    db = get_db()
    finpet = get_user_finpet(username)
    
    # Create the reward object
    reward = {
        "name": reward_name,
        "description": description,
        "icon": icon,
        "date": datetime.now().isoformat()
    }
    
    # Get current rewards and handle different types
    rewards_data = finpet.get("rewards", [])
    
    # Handle rewards as a string (JSON format)
    if isinstance(rewards_data, str):
        try:
            rewards = json.loads(rewards_data)
            if not isinstance(rewards, list):
                rewards = []
        except json.JSONDecodeError:
            rewards = []
    elif isinstance(rewards_data, list):
        rewards = rewards_data
    else:
        rewards = []
    
    # Add the new reward
    rewards.append(reward)
    
    # Update the FinPet with the new reward
    db.finpet.update_one(
        {"username": username},
        {"$set": {"rewards": rewards}}
    )
    
    return reward

def check_and_add_savings_rewards(username, amount_saved):
    """Check if user qualifies for savings-based rewards and add them."""
    # Define savings milestones
    milestones = [
        (100, "Saving Starter", "Saved your first $100", "💰"),
        (500, "Penny Pincher", "Reached $500 in savings", "🪙"),
        (1000, "Money Master", "Saved $1,000", "💵"),
        (5000, "Wealth Builder", "Accumulated $5,000 in savings", "🏆")
    ]
    
    rewards_added = []
    db = get_db()
    
    # Get user's finpet
    finpet = get_user_finpet(username)
    existing_rewards = [r.get("name") for r in finpet.get("rewards", [])]
    
    for milestone, name, desc, icon in milestones:
        if amount_saved >= milestone and name not in existing_rewards:
            reward = add_finpet_reward(username, name, desc, icon)
            rewards_added.append(reward)
            
            # Also give XP for achieving a savings milestone
            bonus_xp = milestone // 100  # 1 XP per $100 saved at milestone
            add_finpet_xp(username, bonus_xp)
    
    return rewards_added

def add_finpet_xp(username, xp_amount):
    """Add XP to user's FinPet and handle level ups."""
    db = get_db()
    finpet = get_user_finpet(username)
    
    new_xp = finpet["xp"] + xp_amount
    level_up = new_xp >= finpet["next_level_xp"]
    
    # Current time as string for SQLite
    current_time = datetime.now().isoformat()
    
    if level_up:
        new_level = finpet["level"] + 1
        # Reduced XP requirement - only 30% more XP needed for next level instead of 50%
        new_next_level_xp = int(finpet["next_level_xp"] * 1.3)
        
        db.finpet.update_one(
            {"username": username},
            {
                "$set": {
                    "xp": new_xp - finpet["next_level_xp"],  # Carry over excess XP
                    "level": new_level,
                    "next_level_xp": new_next_level_xp,
                    "last_fed": current_time
                }
            }
        )
        
        # Add reward for leveling up
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
        db.finpet.update_one(
            {"username": username},
            {
                "$set": {
                    "xp": new_xp,
                    "last_fed": current_time
                }
            }
        )
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
        # Return empty dataframe with date structure
        dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
        return pd.DataFrame({"date": dates, "amount": [0] * 7})
    
    # Ensure date is datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        
        # Calculate last 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        recent_df = df[mask].copy()
        
        if not recent_df.empty:
            # Group by day
            recent_df['day'] = recent_df['date'].dt.strftime('%Y-%m-%d')
            daily_spending = recent_df.groupby('day')['amount'].sum().reset_index()
            
            # Ensure all 7 days are represented
            all_days = pd.DataFrame({
                'day': [(end_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
            })
            result = pd.merge(all_days, daily_spending, on='day', how='left').fillna(0)
            return result
    
    # Return empty dataframe with date structure if no data
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
    
    # Ensure date is datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        
        # Calculate current week (last 7 days)
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
    
    # Ensure date is datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        
        # Current week (last 7 days)
        current_end = datetime.now()
        current_start = current_end - timedelta(days=7)
        
        # Previous week (7 days before that)
        prev_end = current_start
        prev_start = prev_end - timedelta(days=7)
        
        # Filter for both periods
        current_mask = (df['date'] >= current_start) & (df['date'] <= current_end)
        prev_mask = (df['date'] >= prev_start) & (df['date'] <= prev_end)
        
        current_total = df[current_mask]['amount'].sum() if not df[current_mask].empty else 0
        prev_total = df[prev_mask]['amount'].sum() if not df[prev_mask].empty else 1  # Avoid division by zero
        
        if prev_total == 0:
            return 0  # No previous week data
        
        percent_change = ((current_total - prev_total) / prev_total) * 100
        return percent_change
    
    return 0

def plot_spending_trend(username):
    """Create a line chart of daily spending for the last 7 days."""
    data = get_weekly_spending(username)
    
    # Create Altair chart
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
        # Create a placeholder message
        return "No category data available"
    
    if chart_type == "pie":
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.pie(data['amount'], labels=data['category'], autopct='%1.1f%%', startangle=90)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
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
    db = get_db()
    user = db.users.find_one({"username": username})
    
    if user and "wants_budget" in user:
        return user["wants_budget"]
    
    # Default weekly wants budget
    return 100.0

def get_weekly_wants_spending(username):
    """Calculate the current week's 'wants' spending."""
    df = get_expenses_df(username)
    if df.empty:
        return 0
    
    # Filter for current week and 'Wants' type
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
    
    # Basic tips
    tips.append("Set up automatic transfers to your savings account on payday.")
    tips.append("Try the 50/30/20 rule: 50% for needs, 30% for wants, 20% for savings.")
    
    # Category-specific tips based on spending patterns
    if 'category' in df.columns:
        category_spending = df.groupby('category')['amount'].sum()
        
        if 'Food' in category_spending and category_spending['Food'] > 100:
            tips.append("Consider meal planning to reduce your food expenses.")
        
        if 'Entertainment' in category_spending and category_spending['Entertainment'] > 50:
            tips.append("Look for free or low-cost entertainment options in your area.")
        
        if 'Shopping' in category_spending and category_spending['Shopping'] > 100:
            tips.append("Try a 24-hour waiting period before making non-essential purchases.")
    
    # Wants vs Needs insights
    if 'type' in df.columns:
        type_spending = df.groupby('type')['amount'].sum()
        total = type_spending.sum()
        
        if 'Wants' in type_spending and total > 0:
            wants_percentage = (type_spending.get('Wants', 0) / total) * 100
            if wants_percentage > 40:
                tips.append(f"Your 'wants' spending is {wants_percentage:.1f}% of your total. Try to keep it under 30%.")
    
    # Add a tip about Zen Mode
    if not get_zen_mode_status(username):
        tips.append("Activate Zen Mode to help you save money on non-essential purchases.")
    
    # Return a subset of tips (3-5)
    if len(tips) > 5:
        return random.sample(tips, 5)
    return tips
