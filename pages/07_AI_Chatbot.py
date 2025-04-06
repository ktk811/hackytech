import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import utils
from database import get_db

st.set_page_config(page_title="AI Chatbot", page_icon="💬", layout="wide")

# Check if user is logged in
if not st.session_state.get("logged_in", False):
    st.warning("Please login to access this page.")
    st.switch_page("app.py")

# Title
st.title("💬 Financial Assistant")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm your financial assistant. How can I help you today?"}
    ]

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Financial advice knowledge base
financial_advice = {
    "budget": [
        "Creating a budget is the first step to financial control. Start by tracking all your income and expenses.",
        "Try the 50/30/20 rule: 50% for needs, 30% for wants, and 20% for savings and debt repayment.",
        "Review your budget regularly and adjust as needed. Life changes, and so should your budget.",
        "Consider using envelope budgeting or zero-based budgeting methods."
    ],
    "save": [
        "Set up automatic transfers to your savings account on payday.",
        "Try to save at least 20% of your income if possible.",
        "Build an emergency fund that covers 3-6 months of expenses.",
        "Consider setting up separate savings accounts for different goals."
    ],
    "debt": [
        "Focus on paying off high-interest debt first, like credit cards.",
        "Consider the debt snowball method (smallest to largest) for psychological wins.",
        "Look into debt consolidation if you have multiple high-interest debts.",
        "Avoid taking on new debt while paying off existing debt."
    ],
    "invest": [
        "Start investing as early as possible to benefit from compound interest.",
        "Consider low-cost index funds for beginners.",
        "Diversify your investments across different asset classes.",
        "Max out tax-advantaged accounts like 401(k)s and IRAs before taxable accounts."
    ],
    "credit": [
        "Pay your credit card bills on time and in full each month.",
        "Keep your credit utilization below 30% of your available credit.",
        "Check your credit report regularly for errors.",
        "Avoid applying for too many new credit accounts in a short period."
    ],
    "spending": [
        "Track your spending to identify areas where you can cut back.",
        "Use the 24-hour rule for non-essential purchases.",
        "Look for free or low-cost alternatives for entertainment.",
        "Cook at home instead of eating out to save money."
    ]
}

# Function to generate contextual responses
def generate_response(prompt):
    # Convert prompt to lowercase for easier matching
    prompt_lower = prompt.lower()
    
    # Get user data for context
    username = st.session_state.username
    balance = utils.get_current_balance()
    weekly_spending = utils.get_weekly_expenses()
    
    # Check for specific financial queries
    if "budget" in prompt_lower or "spending plan" in prompt_lower:
        return random.choice(financial_advice["budget"])
    
    elif "save" in prompt_lower or "saving" in prompt_lower:
        return random.choice(financial_advice["save"])
    
    elif "debt" in prompt_lower or "loan" in prompt_lower or "credit card" in prompt_lower:
        return random.choice(financial_advice["debt"])
    
    elif "invest" in prompt_lower or "investment" in prompt_lower:
        return random.choice(financial_advice["invest"])
    
    elif "credit" in prompt_lower or "credit score" in prompt_lower:
        return random.choice(financial_advice["credit"])
    
    elif "spend" in prompt_lower or "spending" in prompt_lower:
        return random.choice(financial_advice["spending"])
    
    # Check for account-specific queries
    elif "balance" in prompt_lower or "how much" in prompt_lower and "have" in prompt_lower:
        return f"Your current balance is ${balance:.2f}."
    
    elif "spending" in prompt_lower and "week" in prompt_lower:
        return f"You've spent ${weekly_spending:.2f} this week."
    
    elif "goal" in prompt_lower or "target" in prompt_lower:
        goals = utils.get_user_goals(username)
        if not goals:
            return "You don't have any savings goals set up yet. Would you like to create one?"
        else:
            goal = goals[0]  # Get the first goal
            progress = (goal["current_amount"] / goal["target_amount"]) * 100
            return f"For your '{goal['name']}' goal, you've saved ${goal['current_amount']:.2f} out of ${goal['target_amount']:.2f} ({progress:.1f}%)."
    
    elif "needs" in prompt_lower and "wants" in prompt_lower:
        needs_wants = utils.get_needs_wants_ratio(username)
        needs = needs_wants.get("Needs", 0)
        wants = needs_wants.get("Wants", 0)
        total = needs + wants
        
        if total > 0:
            needs_percent = (needs / total) * 100
            wants_percent = (wants / total) * 100
            return f"Your spending is {needs_percent:.1f}% on needs and {wants_percent:.1f}% on wants. A good rule of thumb is 50% needs, 30% wants, and 20% savings."
        else:
            return "You haven't recorded any expenses yet, so I can't analyze your needs vs. wants ratio."
    
    elif "tip" in prompt_lower or "advice" in prompt_lower:
        tips = utils.generate_savings_tips(username)
        return random.choice(tips)
    
    # General conversation or greeting
    elif any(word in prompt_lower for word in ["hello", "hi", "hey", "greetings"]):
        return f"Hello! How can I help with your finances today?"
    
    elif any(word in prompt_lower for word in ["bye", "goodbye", "see you"]):
        return "Goodbye! Remember to check your budget before your next purchase!"
    
    elif "thank" in prompt_lower:
        return "You're welcome! Is there anything else I can help with?"
    
    # Default response for unrecognized queries
    else:
        return "I'm not sure how to help with that specific question about finances. You can ask me about your balance, spending, savings goals, or for general financial advice on budgeting, saving, debt, investing, credit, or spending."

# Handle user input
if prompt := st.chat_input("Ask about your finances..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    
    # Generate and display assistant response
    response = generate_response(prompt)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Display assistant response
    with st.chat_message("assistant"):
        st.write(response)

# Sidebar with suggested questions
with st.sidebar:
    st.subheader("Suggested Questions")
    st.write("Try asking:")
    
    questions = [
        "What's my current balance?",
        "How much have I spent this week?",
        "How are my savings goals doing?",
        "What's my needs vs. wants ratio?",
        "Give me a savings tip",
        "Help me create a budget",
        "How can I reduce my debt?",
        "What should I know about investing?",
        "How can I improve my credit score?",
        "How can I reduce my spending?"
    ]
    
    for question in questions:
        if st.button(question):
            # Add question to chat history
            st.session_state.messages.append({"role": "user", "content": question})
            
            # Generate response
            response = generate_response(question)
            
            # Add response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Rerun to update the chat display
            st.rerun()

# Clear chat button
if st.sidebar.button("Clear Chat"):
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm your financial assistant. How can I help you today?"}
    ]
    st.rerun()
