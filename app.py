import altair as alt
import streamlit as st
import pandas as pd
from db import (
    init_db,
    create_user,
    verify_user,
    add_transaction,
    get_transactions_by_user,
    update_transaction,
    delete_transaction,
    get_budget,
    set_budget,
    change_password,
)
from utils import CATEGORIES, to_df, classify_useful_waste, auto_suggest_category
from datetime import datetime, date as dt_date
import io

# ----------------- SESSION STATE INITIALIZATION -----------------
if "user" not in st.session_state:
    st.session_state.user = None
if "txn_to_edit" not in st.session_state:
    st.session_state.txn_to_edit = None
if "show_edit_popup" not in st.session_state:
    st.session_state.show_edit_popup = False

# Initialize DB
init_db()
st.set_page_config(page_title="AI Spend Calculator", layout="wide")

# ---------- Apply white text CSS ----------
def apply_white_text_css():
    """Apply CSS for white text throughout the app"""
    css = """
    <style>
        /* Main text colors */
        .css-1d391kg, .css-1lcbmhc, .css-1outpf7, .css-1y4p8pa, 
        .stMarkdown, .stText, .stTitle, .stHeader, .stSubheader,
        .stButton>button, .stSelectbox, .stTextInput, .stNumberInput,
        .stDateInput, .stMultiSelect, .stRadio, .stCheckbox,
        .widget-label, .css-1ue5jrs, .css-1v3fvcr, .css-16idsys,
        .stAlert, .stProgress, .stSuccess, .stWarning, .stError,
        .stInfo {
            color: white !important;
        }
        
        /* Footer and caption */
        .footer-center {
            text-align: center;
            font-weight: 700;
            color: white;
            margin-top: 24px;
        }
        .caption-muted {
            color: white;
            font-size: 0.9rem;
        }
        
        /* Dataframe and table text */
        .dataframe, .stTable {
            color: white !important;
        }
        
        /* Chart text */
        .vega-embed summary, .vega-embed .vega-actions {
            color: white !important;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Apply CSS
apply_white_text_css()

# ----------------- LOGIN / SIGNUP -----------------
def login_page():
    st.title("AI Spend Calculator")
    st.write("A light personal finance tracker")
    st.markdown("<div class='caption-muted'>Developed by <strong>Piyush Kumar</strong></div>", unsafe_allow_html=True)

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
                    st.success("Logged in")
                    st.rerun()
                else:
                    st.error("Invalid credentials")

    with col2:
        if st.button("Sign Up"):
            if not username or not password:
                st.error("Please enter username and password")
            else:
                uid = create_user(username.strip(), password)
                if uid == -1:
                    st.error("Username taken")
                else:
                    st.success("Account created. Please log in.")

# ----------------- DASHBOARD -----------------
def dashboard_page():
    # Header + controls
    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        st.title(f"Welcome, {st.session_state.user['username']}")

    with col2:
        budget_val = get_budget(st.session_state.user["id"])
        st.write(f"Monthly budget: ₹{budget_val:.2f}")

    with col3:
        if st.button("Logout"):
            st.session_state.user = None
            st.success("Logged out")
            st.rerun()

    st.markdown("---")

    # Add transaction
    st.subheader("Add Transaction")
    with st.form("add_tx"):
        tx_date = st.date_input("Date", dt_date.today())
        note = st.text_input("Note / Description (e.g., 'coffee at starbucks')")
        suggested = auto_suggest_category(note) if note else None
        default_idx = CATEGORIES.index(suggested) if suggested in CATEGORIES else 0
        category = st.selectbox("Category", CATEGORIES, index=default_idx)
        amount = st.number_input("Amount (₹)", min_value=0.0, step=0.01)
        submitted = st.form_submit_button("Add")
        if submitted:
            add_transaction(st.session_state.user["id"], tx_date.isoformat(), category, float(amount), note)
            st.success("Added transaction")
            st.rerun()

    # ---------------- Filters & Search ----------------
    st.markdown("### Transactions / Filters")
    txs = get_transactions_by_user(st.session_state.user["id"])
    df_all = to_df(txs)

    if not df_all.empty:
        with st.form("filters"):
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])

            with c1:
                dr = st.date_input("From", value=df_all['date'].min().date())
                dr2 = st.date_input("To", value=df_all['date'].max().date())

            with c2:
                cat_sel = st.multiselect("Category", options=CATEGORIES, default=CATEGORIES)

            with c3:
                min_amt = st.number_input("Min amount", min_value=0.0, value=0.0)
                max_amt = st.number_input("Max amount", min_value=0.0, value=float(df_all['amount'].max()))

            with c4:
                q = st.text_input("Search notes or category")
                sort_by = st.selectbox("Sort by", ["date_desc", "date_asc", "amount_desc", "amount_asc"], index=0)

            apply_filters = st.form_submit_button("Apply")

        df = df_all.copy()
        if apply_filters:
            df = df[(df['date'] >= pd.to_datetime(dr)) & (df['date'] <= pd.to_datetime(dr2))]
            df = df[df['category'].isin(cat_sel)]
            df = df[(df['amount'] >= float(min_amt)) & (df['amount'] <= float(max_amt))]
            if q:
                df = df[df['note'].str.contains(q, case=False, na=False) |
                        df['category'].str.contains(q, case=False, na=False)]
            if sort_by == "date_desc":
                df = df.sort_values("date", ascending=False)
            elif sort_by == "date_asc":
                df = df.sort_values("date", ascending=True)
            elif sort_by == "amount_desc":
                df = df.sort_values("amount", ascending=False)
            else:
                df = df.sort_values("amount", ascending=True)
    else:
        df = df_all.copy()

    # Display transactions with Edit/Delete
    st.subheader("Your Transactions")
    if df.empty:
        st.info("No transactions to show.")
    else:
        for _, row in df.iterrows():
            try:
                d_display = row['date'].date()
            except Exception:
                d_display = row['date']
            cols = st.columns([2, 2, 2, 4, 1, 1])
            cols[0].write(str(d_display))
            cols[1].write(row['category'])
            cols[2].write(f"₹{float(row['amount']):.2f}")
            cols[3].write(row.get('note') or "-")
            if cols[4].button("Edit", key=f"edit_{row['id']}"):
                st.session_state.txn_to_edit = row.to_dict()
                st.session_state.show_edit_popup = True
            if cols[5].button("Delete", key=f"del_{row['id']}"):
                ok = delete_transaction(int(row['id']), st.session_state.user['id'])
                if ok:
                    st.success("Deleted")
                else:
                    st.error("Delete failed")
                st.rerun()

    # Edit popup
    if st.session_state.show_edit_popup and st.session_state.txn_to_edit is not None:
        st.markdown("---")
        st.subheader("Edit Transaction")
        txn = st.session_state.txn_to_edit
        with st.form("edit_form"):
            try:
                init_date = pd.to_datetime(txn['date']).date()
            except Exception:
                init_date = dt_date.today()
            new_date = st.date_input("Date", init_date)
            try:
                init_idx = CATEGORIES.index(txn['category'])
            except ValueError:
                init_idx = 0
            new_cat = st.selectbox("Category", CATEGORIES, index=init_idx)
            new_amt = st.number_input("Amount (₹)", value=float(txn['amount']), step=0.01)
            new_note = st.text_input("Note", value=txn.get('note') or "")
            save = st.form_submit_button("Save")
            cancel = st.form_submit_button("Cancel")
            if save:
                ok = update_transaction(int(txn['id']), st.session_state.user['id'],
                                        new_date.isoformat(), new_cat, float(new_amt), new_note)
                if ok:
                    st.success("Updated")
                else:
                    st.error("Update failed")
                st.session_state.show_edit_popup = False
                st.session_state.txn_to_edit = None
                st.rerun()
            if cancel:
                st.session_state.show_edit_popup = False
                st.session_state.txn_to_edit = None
                st.rerun()

    # ---------------- Budget ----------------
    st.markdown("---")
    st.subheader("Budget")
    current_budget = get_budget(st.session_state.user['id'])
    st.write(f"Monthly budget: ₹{current_budget:.2f}")
    with st.form("set_budget"):
        new_budget = st.number_input("Set monthly budget (₹)", value=float(current_budget), step=100.0)
        if st.form_submit_button("Save budget"):
            set_budget(st.session_state.user['id'], float(new_budget))
            st.success("Budget saved")
            st.rerun()

    # Progress this month
    if not df.empty:
        df_all['month'] = df_all['date'].dt.to_period('M')
        this_month = df_all[df_all['month'] == pd.to_datetime('today').to_period('M')]
        spent_this_month = this_month['amount'].sum()
        if current_budget > 0:
            pct = min(1.0, spent_this_month / current_budget)
            st.write(f"Spent this month: ₹{spent_this_month:.2f} of ₹{current_budget:.2f}")
            st.progress(pct)
            if pct > 0.9:
                st.warning("You are above 90% of your monthly budget!")

    # ---------------- Analysis & Charts ----------------
    if not df.empty:
        df_for_analysis = df.copy()
        df_for_analysis['date'] = pd.to_datetime(df_for_analysis['date'])

        st.markdown("---")
        st.subheader("Spending Summary")
        summary = classify_useful_waste(df_for_analysis)
        st.write(f"Total: ₹{summary['total']:.2f}")
        st.write(f"Useful: ₹{summary['useful']:.2f}")
        st.write(f"Wasteful: ₹{summary['wasteful']:.2f}")

        # Pie chart by category
        pie_data = df_for_analysis.groupby('category')['amount'].sum().reset_index()
        st.altair_chart(
            alt.Chart(pie_data)
            .mark_arc()
            .encode(theta='amount', color='category', tooltip=['category', 'amount']),
            use_container_width=True
        )

        # Monthly bar chart
        df_for_analysis['month'] = df_for_analysis['date'].dt.to_period('M').astype(str)
        monthly = df_for_analysis.groupby('month')['amount'].sum().reset_index()
        st.altair_chart(
            alt.Chart(monthly)
            .mark_bar()
            .encode(x='month', y='amount', tooltip=['month', 'amount']),
            use_container_width=True
        )

        # Daily line chart
        daily = df_for_analysis.groupby('date')['amount'].sum().reset_index()
        st.altair_chart(
            alt.Chart(daily)
            .mark_line(point=True)
            .encode(x='date:T', y='amount', tooltip=['date', 'amount']),
            use_container_width=True
        )

        # AI Prediction (3-month average)
        st.markdown("---")
        st.subheader("AI Prediction")
        try:
            monthly_series = df_for_analysis.set_index('date').resample('M')['amount'].sum()
            if len(monthly_series) >= 2:
                predicted = float(monthly_series.tail(3).mean())
                st.write(f"Predicted spending next month: ₹{predicted:.2f} (3-month average)")
            else:
                st.info("Add more data to get predictions.")
        except Exception:
            st.info("Not enough data for prediction.")

    # ---------------- Export ----------------
    st.markdown("---")
    st.subheader("Export")
    if not df_all.empty:
        csv = df_all.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download CSV",
            data=csv,
            file_name=f"{st.session_state.user['username']}_transactions.csv",
            mime='text/csv'
        )
        towrite = io.BytesIO()
        with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
            df_all.to_excel(writer, index=False, sheet_name='Transactions')
            towrite.seek(0)
            st.download_button(
                "Download Excel",
                data=towrite,
                file_name=f"{st.session_state.user['username']}_transactions.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No data to export")

    # Footer
    st.markdown("---")
    year = datetime.now().year
    footer_html = f"<div class='footer-center'>© {year} Piyush Kumar – All Rights Reserved</div>"
    st.markdown(footer_html, unsafe_allow_html=True)

# ----------------- PROFILE -----------------
def profile_page():
    st.title("Profile")
    st.write(f"Username: {st.session_state.user['username']}")
    st.markdown("### Change password")
    old = st.text_input("Old password", type="password")
    new = st.text_input("New password", type="password")
    if st.button("Change password"):
        user = verify_user(st.session_state.user['username'], old)
        if user:
            ok = change_password(user['id'], new)
            if ok:
                st.success("Password changed. Log in again.")
                st.session_state.user = None
                st.rerun()
            else:
                st.error("Failed to change password.")
        else:
            st.error("Old password incorrect.")

# ----------------- MAIN -----------------
def main():
    if st.session_state.user is None:
        login_page()
    else:
        page = st.sidebar.radio("Go to", ["Dashboard", "Profile"])
        if page == "Dashboard":
            dashboard_page()
        else:
            profile_page()

if __name__ == "__main__":
    main()