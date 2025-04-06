import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import utils
from database import get_db

st.set_page_config(page_title="Expense History", page_icon="📜", layout="wide")

# Check if user is logged in
if not st.session_state.get("logged_in", False):
    st.warning("Please login to access this page.")
    st.switch_page("app.py")

# Title
st.title("📜 Expense History")

# Get all expenses
expenses = utils.get_user_expenses(st.session_state.username)

if not expenses:
    st.info("You don't have any recorded expenses yet. Add some expenses to see your history.")
else:
    # Convert to DataFrame
    df = pd.DataFrame(expenses)
    
    # Ensure date is datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    # Filters
    st.subheader("Filters")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Date range filter
        date_range = st.selectbox(
            "Date Range",
            ["All Time", "Last 7 Days", "Last 30 Days", "This Month", "Last Month", "Custom"],
            index=0
        )
        
        today = datetime.now()
        
        if date_range == "Last 7 Days":
            start_date = today - timedelta(days=7)
            df = df[(df['date'] >= start_date) & (df['date'] <= today)]
        elif date_range == "Last 30 Days":
            start_date = today - timedelta(days=30)
            df = df[(df['date'] >= start_date) & (df['date'] <= today)]
        elif date_range == "This Month":
            start_date = datetime(today.year, today.month, 1)
            df = df[(df['date'] >= start_date) & (df['date'] <= today)]
        elif date_range == "Last Month":
            if today.month == 1:
                start_date = datetime(today.year - 1, 12, 1)
                end_date = datetime(today.year, today.month, 1) - timedelta(days=1)
            else:
                start_date = datetime(today.year, today.month - 1, 1)
                end_date = datetime(today.year, today.month, 1) - timedelta(days=1)
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        elif date_range == "Custom":
            col1, col2 = st.columns(2)
            with col1:
                custom_start = st.date_input("Start Date", today - timedelta(days=30))
            with col2:
                custom_end = st.date_input("End Date", today)
            
            custom_start = datetime.combine(custom_start, datetime.min.time())
            custom_end = datetime.combine(custom_end, datetime.max.time())
            
            df = df[(df['date'] >= custom_start) & (df['date'] <= custom_end)]
    
    with col2:
        # Category filter
        if 'category' in df.columns:
            categories = ["All"] + list(df['category'].unique())
            selected_category = st.selectbox("Category", categories)
            
            if selected_category != "All":
                df = df[df['category'] == selected_category]
    
    with col3:
        # Type filter (Needs/Wants)
        if 'type' in df.columns:
            types = ["All", "Needs", "Wants"]
            selected_type = st.selectbox("Type", types)
            
            if selected_type != "All":
                df = df[df['type'] == selected_type]
    
    # Main expense display
    st.subheader("Expense Records")
    
    if df.empty:
        st.info("No expenses match your filter criteria.")
    else:
        # Format date
        display_df = df.copy()
        display_df['date'] = display_df['date'].dt.strftime('%m/%d/%Y %I:%M %p')
        
        # Sort by date (newest first)
        display_df = display_df.sort_values(by='date', ascending=False)
        
        # Select columns to display
        display_columns = ['description', 'amount', 'date', 'category', 'type']
        display_df = display_df[[col for col in display_columns if col in display_df.columns]]
        
        # Show the data
        st.dataframe(display_df, use_container_width=True)
        
        # Summary statistics
        st.subheader("Summary")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Total expenses
            total_expenses = df['amount'].sum()
            avg_expense = df['amount'].mean()
            count = len(df)
            
            st.metric("Total Expenses", f"${total_expenses:.2f}")
            st.metric("Average Expense", f"${avg_expense:.2f}")
            st.metric("Number of Expenses", count)
        
        with col2:
            # Needs vs Wants
            if 'type' in df.columns:
                needs_wants = df.groupby('type')['amount'].sum().to_dict()
                needs = needs_wants.get('Needs', 0)
                wants = needs_wants.get('Wants', 0)
                
                total = needs + wants
                if total > 0:
                    needs_percent = (needs / total) * 100
                    wants_percent = (wants / total) * 100
                else:
                    needs_percent = wants_percent = 0
                
                st.metric("Needs Expenses", f"${needs:.2f} ({needs_percent:.1f}%)")
                st.metric("Wants Expenses", f"${wants:.2f} ({wants_percent:.1f}%)")
    
    # Visualizations
    st.subheader("Visualizations")
    
    if not df.empty:
        tab1, tab2, tab3 = st.tabs(["Time Trend", "Category Breakdown", "Type Analysis"])
        
        with tab1:
            # Line chart of expenses over time
            if 'date' in df.columns:
                # Group by day
                df['day'] = df['date'].dt.date
                daily_expenses = df.groupby('day')['amount'].sum().reset_index()
                
                # Create chart
                chart = alt.Chart(daily_expenses).mark_line(point=True).encode(
                    x=alt.X('day:T', title='Date'),
                    y=alt.Y('amount:Q', title='Amount ($)'),
                    tooltip=['day:T', 'amount:Q']
                ).properties(
                    title='Daily Expenses',
                    width='container',
                    height=400
                ).interactive()
                
                st.altair_chart(chart, use_container_width=True)
        
        with tab2:
            # Category breakdown
            if 'category' in df.columns:
                category_expenses = df.groupby('category')['amount'].sum().reset_index()
                
                # Create chart
                chart = alt.Chart(category_expenses).mark_bar().encode(
                    x=alt.X('category:N', title='Category', sort='-y'),
                    y=alt.Y('amount:Q', title='Amount ($)'),
                    color='category:N',
                    tooltip=['category:N', 'amount:Q']
                ).properties(
                    title='Expenses by Category',
                    width='container',
                    height=400
                ).interactive()
                
                st.altair_chart(chart, use_container_width=True)
                
                # Category table
                st.write("Category Breakdown")
                category_expenses = category_expenses.sort_values('amount', ascending=False)
                
                # Add percentage column
                total = category_expenses['amount'].sum()
                category_expenses['percentage'] = (category_expenses['amount'] / total * 100).round(1)
                category_expenses['percentage'] = category_expenses['percentage'].astype(str) + '%'
                
                st.dataframe(category_expenses, use_container_width=True)
        
        with tab3:
            # Needs vs Wants analysis
            if 'type' in df.columns:
                type_expenses = df.groupby('type')['amount'].sum().reset_index()
                
                # Create chart
                chart = alt.Chart(type_expenses).mark_bar().encode(
                    x=alt.X('type:N', title='Type'),
                    y=alt.Y('amount:Q', title='Amount ($)'),
                    color=alt.Color('type:N', scale=alt.Scale(
                        domain=['Needs', 'Wants'],
                        range=['#1f77b4', '#ff7f0e']  # Blue for needs, orange for wants
                    )),
                    tooltip=['type:N', 'amount:Q']
                ).properties(
                    title='Needs vs Wants Expenses',
                    width='container',
                    height=300
                ).interactive()
                
                st.altair_chart(chart, use_container_width=True)
                
                # Additional analysis - Wants by category
                if 'category' in df.columns:
                    wants_df = df[df['type'] == 'Wants']
                    if not wants_df.empty:
                        wants_by_category = wants_df.groupby('category')['amount'].sum().reset_index()
                        wants_by_category = wants_by_category.sort_values('amount', ascending=False)
                        
                        st.write("'Wants' Spending by Category")
                        st.dataframe(wants_by_category, use_container_width=True)
                        
                        # Add visualization
                        chart = alt.Chart(wants_by_category).mark_bar().encode(
                            x=alt.X('category:N', title='Category', sort='-y'),
                            y=alt.Y('amount:Q', title='Amount ($)'),
                            color='category:N',
                            tooltip=['category:N', 'amount:Q']
                        ).properties(
                            title='Wants Spending by Category',
                            width='container',
                            height=300
                        ).interactive()
                        
                        st.altair_chart(chart, use_container_width=True)
