# utils.py
from typing import List
import pandas as pd

# Categories of spending
CATEGORIES = [
    "Rent", "Groceries", "Utilities", "Transport", "Food & Dining",
    "Entertainment", "Shopping", "Health", "Education", "Travel", "Savings", "Investments", "Other"
]

# Define which categories are useful vs wasteful
USEFUL = {"Rent", "Groceries", "Utilities", "Health", "Education", "Savings", "Investments"}
WASTEFUL = {"Entertainment", "Shopping", "Food & Dining", "Travel"}

# Convert transaction list (from DB) to Pandas DataFrame
def to_df(tx_list: List[dict]):
    if not tx_list:
        return pd.DataFrame(columns=["id","user_id","date","category","amount","note"])
    df = pd.DataFrame(tx_list)
    df['date'] = pd.to_datetime(df['date'])
    return df

# Classify spending into useful, wasteful, and other
def classify_useful_waste(df):
    total = df['amount'].sum()
    useful = df[df['category'].isin(USEFUL)]['amount'].sum()
    wasteful = df[df['category'].isin(WASTEFUL)]['amount'].sum()
    other = total - useful - wasteful
    return {"total": total, "useful": useful, "wasteful": wasteful, "other": other}
