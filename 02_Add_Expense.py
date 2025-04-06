import streamlit as st
import pandas as pd
from datetime import datetime
import utils
from ml_models import predict_expense_type, predict_expense_category
from database import get_db

st.set_page_config(page_title="Add Expense", page_icon="➕", layout="wide")

# Check if user is logged in
if not st.session_state.get("logged_in", False):
    st.warning("Please login to access this page.")
    st.switch_page("app.py")

# Title
st.title("➕ Add Expense")
st.write("Track your spending by adding expenses below.")

# Main form
col1, col2 = st.columns([2, 1])

with col1:
    with st.form("add_expense_form"):
        description = st.text_input("Description", placeholder="E.g., Grocery shopping at Walmart")
        amount = st.number_input("Amount ($)", min_value=0.01, value=10.0, step=0.01)
        date = st.date_input("Date", value=datetime.now())
        
        # Optional fields - will be predicted if left empty
        st.markdown("### Advanced (Optional)")
        st.info("Category and expense type will be automatically predicted if left empty.")
        
        with st.expander("Manual classification"):
            categories = ["Food", "Utilities", "Housing", "Transport", 
                          "Shopping", "Electronics", "Education", "Entertainment", 
                          "Health", "Personal Care", "Fitness", "Gifts", "Charity", "Other"]
            
            category = st.selectbox("Category", ["Auto-detect"] + categories)
            expense_type = st.selectbox("Type", ["Auto-detect", "Needs", "Wants"])
            
            # Convert "Auto-detect" to None for processing
            category = None if category == "Auto-detect" else category
            expense_type = None if expense_type == "Auto-detect" else expense_type
        
        submit_button = st.form_submit_button("Add Expense")
        
        if submit_button:
            if description and amount > 0:
                # Before adding expense, analyze if it's a "want" and Zen mode is active
                predicted_type = predict_expense_type(description) if expense_type is None else expense_type
                predicted_category = predict_expense_category(description) if category is None else category
                
                # Check if we need to warn about Zen mode
                needs_zen_confirmation = (st.session_state.zen_mode and predicted_type == "Wants")
                
                if needs_zen_confirmation:
                    # We'll handle the confirmation outside the form
                    st.session_state.pending_expense = {
                        "description": description,
                        "amount": amount,
                        "date": datetime.combine(date, datetime.now().time()),
                        "category": predicted_category,
                        "type": predicted_type
                    }
                    st.rerun()  # Force rerun to show confirmation dialog
                else:
                    # Add expense directly
                    utils.add_expense(
                        st.session_state.username,
                        description,
                        amount,
                        datetime.combine(date, datetime.now().time()),
                        predicted_category,
                        predicted_type
                    )
                    st.success(f"Added expense: {description} (${amount:.2f}) - {predicted_category} ({predicted_type})")
                    
                    # Clear form by rerunning
                    st.rerun()
            else:
                st.error("Please enter a description and a valid amount.")

# Zen mode confirmation dialog
if "pending_expense" in st.session_state:
    with st.container():
        st.warning("⚠️ Zen Mode Alert!")
        st.write(f"""
        You're about to add a **'Want'** expense while Zen Mode is active:
        
        **Description:** {st.session_state.pending_expense['description']}  
        **Amount:** ${st.session_state.pending_expense['amount']:.2f}  
        **Category:** {st.session_state.pending_expense['category']}
        
        Zen Mode encourages mindful spending by adding a reflection step before non-essential purchases.
        """)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("👍 Still want to add it"):
                # Add the expense
                utils.add_expense(
                    st.session_state.username,
                    st.session_state.pending_expense['description'],
                    st.session_state.pending_expense['amount'],
                    st.session_state.pending_expense['date'],
                    st.session_state.pending_expense['category'],
                    st.session_state.pending_expense['type']
                )
                st.success(f"Added expense: {st.session_state.pending_expense['description']}")
                
                # Clear pending expense
                del st.session_state.pending_expense
                st.rerun()
        
        with col2:
            if st.button("🧠 Let me reconsider"):
                # Clear pending expense
                del st.session_state.pending_expense
                st.rerun()

with col2:
    # Real-time prediction
    st.subheader("📊 Expense Analysis")
    
    if description:
        predicted_type = predict_expense_type(description) if expense_type is None else expense_type
        predicted_category = predict_expense_category(description) if category is None else category
        
        st.write("Based on your description, this expense appears to be:")
        
        # Type prediction
        if predicted_type == "Needs":
            st.info(f"Type: **{predicted_type}** (Essential expense)")
        else:
            st.warning(f"Type: **{predicted_type}** (Discretionary expense)")
        
        # Category prediction
        st.success(f"Category: **{predicted_category}**")
        
        # Budget check
        if predicted_type == "Wants":
            weekly_wants_budget = utils.get_weekly_wants_budget(st.session_state.username)
            current_wants_spending = utils.get_weekly_wants_spending(st.session_state.username)
            
            remaining_budget = weekly_wants_budget - current_wants_spending
            if amount > remaining_budget:
                st.error(f"⚠️ Warning: This expense will exceed your weekly 'wants' budget by ${amount - remaining_budget:.2f}")
            else:
                st.success(f"Within budget: ${remaining_budget:.2f} remaining for 'wants' this week")
    
    # Budget summary
    st.subheader("💰 Weekly Budget")
    weekly_wants_budget = utils.get_weekly_wants_budget(st.session_state.username)
    current_wants_spending = utils.get_weekly_wants_spending(st.session_state.username)
    
    # Calculate percentage
    if weekly_wants_budget > 0:
        percentage = min((current_wants_spending / weekly_wants_budget) * 100, 100)
    else:
        percentage = 0
    
    st.write(f"Weekly 'Wants' Budget: **${weekly_wants_budget:.2f}**")
    st.write(f"Current Spending: **${current_wants_spending:.2f}** ({percentage:.1f}%)")
    st.progress(percentage / 100)
    
    # Recent expenses
    st.subheader("📝 Recent Expenses")
    expenses = utils.get_user_expenses(st.session_state.username)
    
    if expenses:
        # Convert to DataFrame and format
        df = pd.DataFrame(expenses[-5:])  # Last 5 expenses
        df = df.sort_values(by="date", ascending=False)
        
        # Format for display
        if not df.empty and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%m/%d/%Y')
            
            # Display columns we want to show
            display_columns = ['description', 'amount', 'date', 'category', 'type']
            available_columns = [col for col in display_columns if col in df.columns]
            
            st.dataframe(df[available_columns], use_container_width=True)
    else:
        st.info("No expenses recorded yet. Add your first expense above!")
