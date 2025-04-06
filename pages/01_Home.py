import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import matplotlib.pyplot as plt
import utils
from database import get_db

st.set_page_config(page_title="Home Dashboard", page_icon="🏠", layout="wide")

# Check if user is logged in
if not st.session_state.get("logged_in", False):
    st.warning("Please login to access this page.")
    st.switch_page("app.py")

# Title and user greeting
st.title("🏠 Financial Dashboard")
st.subheader(f"Welcome back, {st.session_state.username}!")

# Display current balance and Zen mode status
col1, col2, col3 = st.columns(3)
with col1:
    current_balance = utils.get_current_balance()
    st.metric(
        label="Current Balance", 
        value=f"${current_balance:.2f}"
    )

with col2:
    weekly_expenses = utils.get_weekly_expenses()
    st.metric(
        label="This Week's Expenses", 
        value=f"${weekly_expenses:.2f}",
        delta=f"{utils.get_expense_trend():.1f}%"
    )

with col3:
    needs_wants = utils.get_needs_wants_ratio(st.session_state.username)
    needs_total = needs_wants.get("Needs", 0)
    wants_total = needs_wants.get("Wants", 0)
    total = needs_total + wants_total
    
    if total > 0:
        needs_percentage = (needs_total / total) * 100
    else:
        needs_percentage = 0
    
    st.metric(
        label="Needs vs. Wants", 
        value=f"{needs_percentage:.1f}% Needs",
        delta=f"{100-needs_percentage:.1f}% Wants",
        delta_color="off"
    )

# Main dashboard content
col1, col2 = st.columns([2, 1])

with col1:
    # Spending trend chart
    st.subheader("📈 Spending Trends")
    spending_chart = utils.plot_spending_trend(st.session_state.username)
    st.altair_chart(spending_chart, use_container_width=True)
    
    # Category breakdown
    st.subheader("📊 Spending by Category")
    chart_type = st.radio("Chart Type", ["pie", "bar"], horizontal=True)
    
    if chart_type == "pie":
        fig = utils.plot_category_breakdown(st.session_state.username, "pie")
        if isinstance(fig, str):
            st.info(fig)  # Show the message if no data
        else:
            st.pyplot(fig)
    else:
        chart = utils.plot_category_breakdown(st.session_state.username, "bar")
        if isinstance(chart, str):
            st.info(chart)  # Show the message if no data
        else:
            st.altair_chart(chart, use_container_width=True)

with col2:
    # Quick add expense
    st.subheader("➕ Quick Add")
    with st.form("quick_add_form"):
        description = st.text_input("Description")
        amount = st.number_input("Amount ($)", min_value=0.01, step=0.01)
        add_button = st.form_submit_button("Add Expense")
        
        if add_button and description and amount > 0:
            # Predict type and category
            expense_type = utils.predict_expense_type(description)
            category = utils.predict_expense_category(description)
            
            # Check Zen mode for wants
            if st.session_state.zen_mode and expense_type == "Wants":
                st.warning("⚠️ Zen Mode is active. Are you sure you want to add this non-essential expense?")
                confirm = st.button("Confirm Expense")
                if confirm:
                    utils.add_expense(st.session_state.username, description, amount)
                    st.success(f"Added: {description} (${amount:.2f}) - {category} ({expense_type})")
                    st.rerun()
            else:
                utils.add_expense(st.session_state.username, description, amount)
                st.success(f"Added: {description} (${amount:.2f}) - {category} ({expense_type})")
                st.rerun()
    
    # Savings advice
    st.subheader("💡 Savings Tips")
    tips = utils.generate_savings_tips(st.session_state.username)
    for tip in tips:
        st.info(tip)
    
    # Goals progress
    st.subheader("🎯 Goals Progress")
    goals = utils.get_user_goals(st.session_state.username)
    
    if not goals:
        st.info("You don't have any savings goals yet. Create one in the Funds & Goals section!")
    else:
        for goal in goals[:3]:  # Show top 3 goals
            progress = goal["current_amount"] / goal["target_amount"] * 100
            st.write(f"**{goal['name']}**")
            st.progress(min(progress/100, 1.0))
            st.write(f"${goal['current_amount']:.2f} / ${goal['target_amount']:.2f} ({progress:.1f}%)")
        
        if len(goals) > 3:
            st.write(f"... and {len(goals) - 3} more goals")
    
    # FinPet status
    st.subheader("🐾 FinPet Status")
    finpet = utils.get_user_finpet(st.session_state.username)
    
    st.write(f"**{finpet['name']}** (Level {finpet['level']})")
    xp_progress = finpet["xp"] / finpet["next_level_xp"]
    st.progress(xp_progress)
    st.write(f"XP: {finpet['xp']}/{finpet['next_level_xp']}")
    
    # Display FinPet rewards count
    rewards = []
    if 'rewards' in finpet:
        if isinstance(finpet['rewards'], list):
            rewards = finpet['rewards']
        elif isinstance(finpet['rewards'], str):
            try:
                import json
                rewards = json.loads(finpet['rewards'])
            except:
                rewards = []
    
    st.write(f"**Rewards:** {len(rewards)} collected")
    
    # Display a recent reward if available
    if rewards:
        recent_reward = rewards[-1] if isinstance(rewards, list) else None
        if isinstance(recent_reward, dict):
            icon = recent_reward.get('icon', '🎁')
            name = recent_reward.get('name', 'Reward')
            st.success(f"Most recent: {icon} {name}")
    
    # Enhanced description
    with st.expander("About FinPet"):
        st.write("""
        **NEW!** Your FinPet now earns special rewards as you achieve financial milestones! 
        
        - Earn XP for responsible financial decisions
        - Collect special rewards for meeting savings goals
        - Watch your FinPet evolve as you improve your finances
        - Visit the FinPet page to see all your rewards
        """)
    
    # Visit button
    if st.button("Visit FinPet"):
        st.switch_page("pages/05_FinPet.py")
