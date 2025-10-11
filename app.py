# app.py
import altair as alt
import streamlit as st
from db import init_db, create_user, verify_user, add_transaction, get_transactions_by_user
from utils import CATEGORIES, to_df, classify_useful_waste, generate_insights
from datetime import datetime

# Initialize database tables
init_db()

# ----------- SESSION STATE SETUP -----------
if 'user' not in st.session_state:
    st.session_state.user = None

# ----------- LOGIN / SIGNUP -----------
def login_page():
    st.title("AI Spend Calculator")
    st.subheader("Login or Sign Up")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login"):
            user = verify_user(username, password)
            if user:
                st.session_state.user = user
                st.success(f"Welcome {username}!")
            else:
                st.error("Invalid credentials")

    with col2:
        if st.button("Sign Up"):
            user_id = create_user(username, password)
            if user_id != -1:
                st.success("Account created! Please login.")
            else:
                st.error("Username already exists")

def dashboard():
    # Top bar with logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"Welcome, {st.session_state.user['username']}")
    with col2:
        if st.button("Logout"):
            st.session_state.user = None
            st.success("Logged out successfully!")
            st.experimental_rerun()   # reloads the app

    st.subheader("Add Transaction")

    with st.form("transaction_form"):
        date = st.date_input("Date", datetime.today())
        category = st.selectbox("Category", CATEGORIES)
        amount = st.number_input("Amount", min_value=0.0, step=0.01)
        note = st.text_input("Note (optional)")
        submitted = st.form_submit_button("Add Transaction")

        if submitted:
            add_transaction(st.session_state.user['id'], str(date), category, amount, note)
            st.success("Transaction added!")

    # Display all transactions
    tx_list = get_transactions_by_user(st.session_state.user['id'])
    if tx_list:
        df = to_df(tx_list)
        st.subheader("Your Transactions")
        st.dataframe(df)

        # Spending summary
        summary = classify_useful_waste(df)
        st.subheader("Spending Summary")
        st.write(f"Total: ₹{summary['total']:.2f}")
        st.write(f"Useful: ₹{summary['useful']:.2f}")
        st.write(f"Wasteful: ₹{summary['wasteful']:.2f}")
        st.write(f"Other: ₹{summary['other']:.2f}")

        # ----------- CHARTS SECTION -----------
        st.subheader("Visualizations")

        # 1. Pie Chart: Category-wise spending
        st.write("**Category-wise Spending (Pie Chart)**")
        pie_chart_data = df.groupby("category")["amount"].sum().reset_index()
        pie_chart = alt.Chart(pie_chart_data).mark_arc().encode(
            theta="amount",
            color="category",
            tooltip=["category", "amount"]
        )
        st.altair_chart(pie_chart, use_container_width=True)

        # 2. Bar Chart: Monthly spending
        st.write("**Monthly Spending (Bar Chart)**")
        df["month"] = df["date"].dt.to_period("M").astype(str)
        monthly_data = df.groupby("month")["amount"].sum().reset_index()
        bar_chart = alt.Chart(monthly_data).mark_bar().encode(
            x="month",
            y="amount",
            tooltip=["month", "amount"]
        )
        st.altair_chart(bar_chart, use_container_width=True)

        # 3. Line Chart: Daily spending trend
        st.write("**Daily Spending Over Time (Line Chart)**")
        line_chart_data = df.groupby("date")["amount"].sum().reset_index()
        line_chart = alt.Chart(line_chart_data).mark_line(point=True).encode(
            x="date:T",
            y="amount",
            tooltip=["date", "amount"]
        )
        st.altair_chart(line_chart, use_container_width=True)

        # AI Insights (safe because df exists)
        st.subheader("AI Insights")
        insights = generate_insights(df)
        for i in insights:
            st.write(i)

    else:
        st.info("No transactions yet.")
        st.subheader("AI Insights")
        st.write("Add some transactions to see AI suggestions!")

# ----------- MAIN -----------
def main():
    if st.session_state.user is None:
        login_page()
    else:
        dashboard()

if __name__ == "__main__":
    main()
