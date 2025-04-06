import streamlit as st
import utils
from database import get_db
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Zen Mode", page_icon="🧘", layout="wide")

# Check if user is logged in
if not st.session_state.get("logged_in", False):
    st.warning("Please login to access this page.")
    st.switch_page("app.py")

# Title
st.title("🧘 Zen Mode")
st.write("Mindful spending for financial peace")

# Get current Zen Mode status
zen_status = utils.get_zen_mode_status(st.session_state.username)

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("What is Zen Mode?")
    
    st.write("""
    **Zen Mode** is a mindful spending feature that helps you make more conscious decisions about your discretionary expenses.
    
    **When Zen Mode is active:**
    - You'll be asked to confirm before adding any 'wants' expense
    - This creates a moment of reflection before non-essential purchases
    - It helps reduce impulse spending and increase savings
    - Your FinPet earns extra XP when you choose to skip a 'want' purchase
    
    Activating Zen Mode is a commitment to more mindful spending habits.
    """)
    
    # Current status and toggle
    st.subheader("Current Status")
    
    # Create columns for status display and toggle
    status_col, toggle_col = st.columns([3, 1])
    
    with status_col:
        if zen_status:
            st.success("✅ Zen Mode is currently **ACTIVE**")
        else:
            st.info("❌ Zen Mode is currently **INACTIVE**")
    
    with toggle_col:
        if st.button("Toggle Zen Mode"):
            # Update to opposite of current status
            new_status = not zen_status
            utils.update_zen_mode(st.session_state.username, new_status)
            st.session_state.zen_mode = new_status
            st.rerun()
    
    # Zen Mode benefits
    st.subheader("Benefits of Zen Mode")
    
    benefits_col1, benefits_col2 = st.columns(2)
    
    with benefits_col1:
        st.markdown("""
        #### Psychological Benefits
        - Reduces impulse purchases
        - Creates mindful spending habits
        - Increases awareness of needs vs wants
        - Improves financial decision-making
        """)
    
    with benefits_col2:
        st.markdown("""
        #### Financial Benefits
        - Increases your savings rate
        - Redirects money to important goals
        - Reduces spending on low-value items
        - Helps achieve financial goals faster
        """)
    
    # Zen Mode impact
    if zen_status:
        st.subheader("Your Zen Mode Impact")
        
        # Get data since Zen Mode was activated
        db = get_db()
        user = db.users.find_one({"username": st.session_state.username})
        
        # For demo purposes, we'll show example impact data
        # In a real implementation, we would track when Zen Mode was activated
        today = datetime.now()
        thirty_days_ago = today - timedelta(days=30)
        
        # Get wants expenses from last 30 days
        wants_expenses = list(db.expenses.find({
            "username": st.session_state.username,
            "type": "Wants",
            "date": {"$gte": thirty_days_ago}
        }))
        
        if wants_expenses:
            df = pd.DataFrame(wants_expenses)
            total_wants = df['amount'].sum()
            
            # Estimated savings (assume 15% reduction in wants spending due to Zen Mode)
            estimated_savings = total_wants * 0.15
            
            st.metric(
                label="Estimated Monthly Savings with Zen Mode", 
                value=f"${estimated_savings:.2f}",
                delta="15% reduction in 'wants' spending"
            )
            
            # Project annual impact
            annual_impact = estimated_savings * 12
            st.write(f"If maintained for a full year, Zen Mode could help you save approximately **${annual_impact:.2f}**!")
        else:
            st.info("Start tracking your 'wants' expenses to see the impact of Zen Mode on your finances.")

with col2:
    st.subheader("Zen Mode Tips")
    
    tips = [
        "Before making a purchase, ask if it's aligned with your values and goals",
        "Try the 24-hour rule for any non-essential purchase over $50",
        "Keep a wish list and revisit it after 30 days - you may find you no longer want many items",
        "For each 'want' purchase, ask 'How many hours of work does this cost me?'",
        "Unsubscribe from retail emails and unfollow brands on social media to reduce temptation",
        "Track how often you choose to skip a purchase after the Zen Mode reflection",
        "Celebrate your wins by redirecting saved money to your goals"
    ]
    
    for tip in tips:
        st.info(tip)
    
    # Zen Challenge
    st.subheader("Zen Challenge")
    
    st.write("""
    **30-Day Zen Challenge:**
    
    1. Keep Zen Mode active for 30 days
    2. Record every 'want' purchase you skip
    3. Save the money you would have spent
    4. After 30 days, see how much you've saved!
    """)
    
    # Testimonial (fictional)
    st.subheader("User Experiences")
    
    st.success("""
    *"Zen Mode helped me save over $200 in just one month by making me pause before each impulse purchase. Now I'm much more intentional with my spending!"*
    
    — A happy user
    """)
    
    # Quick add to goal button
    st.subheader("Quick Actions")
    
    goals = utils.get_user_goals(st.session_state.username)
    if goals:
        with st.form("quick_savings"):
            st.write("Add savings from avoided 'wants' purchase:")
            amount = st.number_input("Amount Saved ($)", min_value=1.0, value=20.0, step=5.0)
            goal_options = {goal["name"]: str(goal["_id"]) for goal in goals}
            selected_goal = st.selectbox("Add to Goal", options=list(goal_options.keys()))
            
            submit_button = st.form_submit_button("Add to Goal")
            
            if submit_button and amount > 0:
                goal_id = goal_options[selected_goal]
                utils.update_goal(goal_id, amount)
                
                # Award extra XP for Zen savings
                utils.add_finpet_xp(st.session_state.username, 10)
                
                st.success(f"Added ${amount:.2f} to {selected_goal} and earned 10 XP for your FinPet!")
                st.rerun()
    else:
        st.info("Create a savings goal to track your Zen Mode savings!")
