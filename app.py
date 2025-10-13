# app.py
import altair as alt
import streamlit as st
import pandas as pd
import numpy as np
from db import (
    init_db,
    create_user,
    verify_user,
    add_transaction,
    get_transactions_by_user,
    update_transaction,
    delete_transaction,
)
from utils import CATEGORIES, to_df, classify_useful_waste, generate_insights
from datetime import datetime, date as dt_date

# Initialize database tables
init_db()

st.set_page_config(page_title="AI Spend Calculator", layout="wide")

# ----------- SESSION STATE SETUP -----------
if "user" not in st.session_state:
    st.session_state.user = None
if "txn_to_edit" not in st.session_state:
    st.session_state.txn_to_edit = None
if "show_edit_popup" not in st.session_state:
    st.session_state.show_edit_popup = False

# ----------- LOGIN / SIGNUP -----------
def login_page():
    st.title("AI Spend Calculator")
    st.title("Developed by Piyush")
    st.subheader("Login or Sign Up")

    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login"):
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                user = verify_user(username.strip(), password)
                if user:
                    st.session_state.user = user
                    st.success(f"Welcome {username.strip()}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")

    with col2:
        if st.button("Sign Up"):
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                uid = create_user(username.strip(), password)
                if uid == -1:
                    st.error("Username already exists. Try another.")
                elif uid == -2:
                    st.error("Error creating user. Please try again.")
                else:
                    st.success("Account created! Please login.")

# ----------- DASHBOARD -----------
def dashboard():
    # Top bar with logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"Welcome, {st.session_state.user['username']}")
    with col2:
        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.show_edit_popup = False
            st.session_state.txn_to_edit = None
            st.success("Logged out successfully!")
            st.rerun()

    st.subheader("Add Transaction")
    with st.form("transaction_form", clear_on_submit=True):
        tx_date = st.date_input("Date", dt_date.today())
        category = st.selectbox("Category", CATEGORIES)
        amount = st.number_input("Amount (₹)", min_value=0.0, step=0.01)
        note = st.text_input("Note (optional)")
        submitted = st.form_submit_button("Add Transaction")
        if submitted:
            if amount <= 0:
                st.error("Amount must be greater than 0")
            else:
                result = add_transaction(st.session_state.user["id"], tx_date.isoformat(), category, float(amount), note)
                if result != -1:
                    st.success("Transaction added!")
                    st.rerun()
                else:
                    st.error("Failed to add transaction")

    # Display all transactions
    tx_list = get_transactions_by_user(st.session_state.user["id"])

    st.subheader("Your Transactions")
    if tx_list:
        # Show rows with Edit/Delete buttons
        for i, txn in enumerate(tx_list):
            # Parse date string -> readable
            try:
                d_display = datetime.fromisoformat(txn["date"]).strftime("%Y-%m-%d")
            except Exception:
                d_display = txn["date"]

            cols = st.columns([2, 2, 2, 3, 1, 1])
            cols[0].write(d_display)
            cols[1].write(txn["category"])
            cols[2].write(f"₹{float(txn['amount']):.2f}")
            cols[3].write(txn.get("note") or "-")
            
            with cols[4]:
                if st.button("Edit", key=f"edit_{txn['id']}"):
                    st.session_state.txn_to_edit = txn
                    st.session_state.show_edit_popup = True
                    st.rerun()
            
            with cols[5]:
                if st.button("Delete", key=f"delete_{txn['id']}"):
                    ok = delete_transaction(txn["id"], st.session_state.user["id"])
                    if ok:
                        st.success("Transaction deleted.")
                    else:
                        st.error("Failed to delete transaction.")
                    st.rerun()

        # Edit form (popup-like)
        if st.session_state.show_edit_popup and st.session_state.txn_to_edit:
            txn = st.session_state.txn_to_edit
            st.markdown("---")
            st.subheader("Edit Transaction")
            with st.form("edit_form"):
                # Parse txn date string to date
                try:
                    init_date = datetime.fromisoformat(txn["date"]).date()
                except Exception:
                    init_date = dt_date.today()
                
                new_date = st.date_input("Date", init_date, key="edit_date")
                
                try:
                    init_index = CATEGORIES.index(txn["category"])
                except ValueError:
                    init_index = 0
                new_category = st.selectbox("Category", CATEGORIES, index=init_index, key="edit_category")
                
                new_amount = st.number_input("Amount (₹)", value=float(txn["amount"]), step=0.01, key="edit_amount")
                new_note = st.text_input("Note (optional)", value=txn.get("note") or "", key="edit_note")
                
                col1, col2 = st.columns(2)
                with col1:
                    save = st.form_submit_button("Save")
                with col2:
                    cancel = st.form_submit_button("Cancel")
                
                if save:
                    if new_amount <= 0:
                        st.error("Amount must be greater than 0")
                    else:
                        updated = update_transaction(
                            txn["id"],
                            st.session_state.user["id"],
                            new_date.isoformat(),
                            new_category,
                            float(new_amount),
                            new_note,
                        )
                        if updated:
                            st.success("Transaction updated.")
                            st.session_state.show_edit_popup = False
                            st.session_state.txn_to_edit = None
                            st.rerun()
                        else:
                            st.error("Failed to update transaction.")
                
                if cancel:
                    st.session_state.show_edit_popup = False
                    st.session_state.txn_to_edit = None
                    st.rerun()

    # Analysis and Charts Section
    st.markdown("---")
    
    if tx_list:  # Only show analysis if there are transactions
        try:
            df = to_df(tx_list)
            
            # Spending summary
            st.subheader("Spending Summary")
            summary = classify_useful_waste(df)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Spending", f"₹{summary['total']:.2f}")
            col2.metric("Useful", f"₹{summary['useful']:.2f}")
            col3.metric("Wasteful", f"₹{summary['wasteful']:.2f}")
            col4.metric("Other", f"₹{summary['other']:.2f}")

            # ----------- CHARTS SECTION -----------
            st.subheader("Visualizations")

            # 1. Pie Chart: Category-wise spending
            st.write("**Category-wise Spending**")
            pie_chart_data = df.groupby("category")["amount"].sum().reset_index()
            pie_chart = alt.Chart(pie_chart_data).mark_arc().encode(
                theta=alt.Theta(field="amount", type="quantitative"),
                color=alt.Color(field="category", type="nominal"),
                tooltip=["category", "amount"]
            ).properties(width=400, height=400)
            st.altair_chart(pie_chart, use_container_width=True)

            # 2. Bar Chart: Monthly spending
            st.write("**Monthly Spending**")
            df["month"] = df["date"].dt.to_period("M").astype(str)
            monthly_data = df.groupby("month")["amount"].sum().reset_index()
            bar_chart = alt.Chart(monthly_data).mark_bar().encode(
                x=alt.X("month", title="Month"),
                y=alt.Y("amount", title="Amount (₹)"),
                tooltip=["month", "amount"]
            )
            st.altair_chart(bar_chart, use_container_width=True)

            # 3. Line Chart: Daily spending trend
            st.write("**Daily Spending Over Time**")
            line_chart_data = df.groupby("date")["amount"].sum().reset_index()
            line_chart = alt.Chart(line_chart_data).mark_line(point=True).encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("amount", title="Amount (₹)"),
                tooltip=["date", "amount"]
            )
            st.altair_chart(line_chart, use_container_width=True)

            # AI Insights
            st.subheader("AI Insights")
            insights = generate_insights(df)
            for i, insight in enumerate(insights):
                st.write(f"• {insight}")

        except Exception as e:
            st.error(f"Error generating analysis: {str(e)}")
            st.info("Please check if your transaction data is in the correct format.")
    else:
        st.info("No transactions yet. Add some transactions to see analysis and insights!")
    
    # Footer
    st.markdown("---")
    st.markdown("### All rights reserved. © Developed by Piyush Kumar")

# ----------- MAIN -----------
def main():
    if st.session_state.user is None:
        login_page()
    else:
        dashboard()

if __name__ == "__main__":
    main()