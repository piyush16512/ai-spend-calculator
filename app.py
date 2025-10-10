# app.py
import streamlit as st
from db import init_db, create_user, verify_user, add_transaction, get_transactions_by_user
from utils import CATEGORIES, to_df, classify_useful_waste
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


# ----------- DASHBOARD -----------
def dashboard():
    st.title(f"Welcome, {st.session_state.user['username']}")
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

    else:
        st.info("No transactions yet.")


# ----------- MAIN -----------
def main():
    if st.session_state.user is None:
        login_page()
    else:
        dashboard()

if __name__ == "__main__":
    main()
