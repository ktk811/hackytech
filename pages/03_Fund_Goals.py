import streamlit as st
import pandas as pd
from datetime import datetime
import utils
from database import get_db

st.set_page_config(page_title="Funds & Goals", page_icon="💰", layout="wide")

# Check if user is logged in
if not st.session_state.get("logged_in", False):
    st.warning("Please login to access this page.")
    st.switch_page("app.py")

# Title
st.title("💰 Funds & Goals")

# Main content split into two columns
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("💵 Manage Your Funds")
    
    # Current balance card
    current_balance = utils.get_current_balance()
    st.metric(
        label="Current Balance",
        value=f"${current_balance:.2f}"
    )
    
    # Add funds form
    with st.expander("Add Funds"):
        with st.form("add_funds_form"):
            amount = st.number_input("Amount ($)", min_value=0.01, value=50.0, step=0.01)
            description = st.text_input("Description (optional)", placeholder="E.g., Paycheck, Gift, etc.")
            
            submit_button = st.form_submit_button("Add Funds")
            
            if submit_button:
                if amount > 0:
                    utils.add_funds(
                        st.session_state.username,
                        amount,
                        description if description else "Deposit"
                    )
                    st.success(f"Added ${amount:.2f} to your balance!")
                    st.rerun()
                else:
                    st.error("Please enter a valid amount.")
    
    # Recent transactions
    st.subheader("Recent Transactions")
    
    db = get_db()
    # Get both expenses and fund additions
    expenses = list(db.expenses.find({"username": st.session_state.username}))
    
    # Get fund transactions if the table exists
    try:
        deposits = list(db.fund_transactions.find({"username": st.session_state.username}))
    except:
        deposits = []
    
    # Add transaction type
    for expense in expenses:
        expense["transaction_type"] = "Expense"
        expense["amount"] = -expense["amount"]  # Negate amount for expenses
    
    for deposit in deposits:
        deposit["transaction_type"] = "Deposit"
        deposit["type"] = "Income"  # Add type to match expense schema
    
    # Combine and sort
    transactions = expenses + deposits
    transactions.sort(key=lambda x: x["date"], reverse=True)
    
    if transactions:
        # Convert to DataFrame
        df = pd.DataFrame(transactions[:10])  # Show top 10 recent transactions
        
        # Format date
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%m/%d/%Y %I:%M %p')
        
        # Format for display
        display_df = df[['description', 'amount', 'date', 'transaction_type']].copy()
        
        # Colorize the amounts based on transaction type
        def highlight_transactions(val):
            if val < 0:
                return 'color: red'
            else:
                return 'color: green'
        
        st.dataframe(
            display_df.style.applymap(highlight_transactions, subset=['amount']),
            use_container_width=True
        )
    else:
        st.info("No transactions recorded yet.")

with col2:
    st.subheader("🎯 Savings Goals")
    
    # Add new goal form
    with st.expander("Add New Goal"):
        with st.form("add_goal_form"):
            goal_name = st.text_input("Goal Name", placeholder="E.g., Vacation, Emergency Fund, etc.")
            target_amount = st.number_input("Target Amount ($)", min_value=1.0, value=500.0, step=10.0)
            initial_amount = st.number_input("Initial Amount ($)", min_value=0.0, value=0.0, step=10.0)
            
            submit_button = st.form_submit_button("Create Goal")
            
            if submit_button:
                if goal_name and target_amount > 0:
                    utils.add_goal(
                        st.session_state.username,
                        goal_name,
                        target_amount,
                        initial_amount
                    )
                    st.success(f"Created new goal: {goal_name}")
                    st.rerun()
                else:
                    st.error("Please enter a goal name and a valid target amount.")
    
    # List existing goals
    goals = utils.get_user_goals(st.session_state.username)
    
    if not goals:
        st.info("You don't have any savings goals yet. Create one above!")
    else:
        for i, goal in enumerate(goals):
            # Create an expander for each goal
            with st.expander(f"{goal['name']} - ${goal['target_amount']:.2f}", expanded=i == 0):
                # Calculate progress
                progress = goal["current_amount"] / goal["target_amount"] * 100
                
                # Progress bar
                st.progress(min(progress/100, 1.0))
                st.write(f"${goal['current_amount']:.2f} / ${goal['target_amount']:.2f} ({progress:.1f}%)")
                
                # Calculate remaining amount
                remaining = goal["target_amount"] - goal["current_amount"]
                
                if goal["completed"]:
                    st.success("✅ Goal Completed!")
                else:
                    st.write(f"Remaining: ${remaining:.2f}")
                
                # Add funds to this goal form
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    contribute_amount = st.number_input(f"Amount for '{goal['name']}'", 
                                                         min_value=0.01, 
                                                         value=min(10.0, remaining) if remaining > 0 else 0.01,
                                                         step=1.0,
                                                         key=f"goal_{i}")
                
                with col2:
                    if st.button("Contribute", key=f"contribute_{i}"):
                        if contribute_amount > 0:
                            if contribute_amount <= current_balance:
                                # Update goal
                                new_amount, completed = utils.update_goal(goal["id"], contribute_amount)
                                
                                # Update balance
                                utils.update_balance(st.session_state.username, -contribute_amount)
                                
                                if completed:
                                    st.success(f"🎉 Congratulations! You've reached your goal: {goal['name']}")
                                    # Add a special reward for completing a savings goal
                                    utils.add_finpet_reward(
                                        st.session_state.username,
                                        "Goal Achieved",
                                        f"Completed savings goal: {goal['name']} (${goal['target_amount']:.2f})",
                                        "🏆"
                                    )
                                    st.info("🏆 You've earned a special FinPet reward for reaching your goal! +25 XP")
                                else:
                                    st.success(f"Added ${contribute_amount:.2f} to {goal['name']}")
                                    # Note about XP earned
                                    st.info("🐾 Your FinPet earned +3 XP for saving money!")
                                
                                st.rerun()
                            else:
                                st.error("Insufficient funds in your balance.")
                        else:
                            st.error("Please enter a valid amount.")
                
                # Show creation date
                if "date_created" in goal:
                    created_date = goal["date_created"].strftime("%B %d, %Y") if isinstance(goal["date_created"], datetime) else "Unknown"
                    st.caption(f"Goal created: {created_date}")
    
    # Zen Mode promotion
    st.subheader("🧘 Zen Savings")
    
    zen_status = utils.get_zen_mode_status(st.session_state.username)
    
    if zen_status:
        st.success("Zen Mode is currently active! You're on your way to mindful spending.")
    else:
        st.info("Activate Zen Mode to help you save more by encouraging reflection before non-essential purchases.")
    
    st.write("""
    **How Zen Mode helps you save:**
    - Adds a reflection step before 'wants' purchases
    - Helps you distinguish between needs and wants
    - Encourages mindful spending habits
    """)
    
    if st.button("Go to Zen Mode Settings"):
        st.switch_page("pages/08_Zen_Mode.py")
