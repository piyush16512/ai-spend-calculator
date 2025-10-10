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
def generate_insights(df):
    summary = classify_useful_waste(df)
    insights = []

    # Highest spending category
    if not df.empty:
        top_cat = df.groupby("category")['amount'].sum().idxmax()
        insights.append(f"💰 You spend the most on: {top_cat}")

    # Wasteful spending
    waste_percent = (summary['wasteful']/summary['total']*100) if summary['total']>0 else 0
    if waste_percent > 30:
        insights.append(f"⚠️ High wasteful spending! Consider reducing by {int(waste_percent - 30)}%")

    # Suggest saving
    if summary['useful']/summary['total']*100 < 50 and summary['total']>0:
        insights.append("💡 Try increasing your savings and investments.")

    if not insights:
        insights.append("✅ Your spending looks balanced!")
    return insights
