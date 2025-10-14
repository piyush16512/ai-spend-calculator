# utils.py
"""
Utility helpers for AI Spend Calculator.

Provides:
- Categories/constants
- DataFrame conversion helpers
- Classification (useful vs wasteful)
- Insights generation
- Simple AI category suggestion (rule-based + optional OpenAI fallback)
- Summaries (daily/weekly/monthly)
- Recurring-transaction date helper
- Export helpers (CSV / Excel bytes)
- Budget & savings helpers
- Category analytics helpers
"""

from typing import List, Dict, Optional, Tuple
import pandas as pd
import io
import os
from collections import Counter
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

# -------------------------
# 1) Constants / categories
# -------------------------
CATEGORIES = [
    "Rent",
    "Groceries",
    "Utilities",
    "Transport",
    "Food & Dining",
    "Entertainment",
    "Shopping",
    "Health",
    "Education",
    "Travel",
    "Savings",
    "Investments",
    "Other",
]

USEFUL = {"Rent", "Groceries", "Utilities", "Health", "Education", "Savings", "Investments"}
WASTEFUL = {"Entertainment", "Shopping", "Food & Dining", "Travel"}

# Keyword map for basic category suggestion
KEYWORD_MAP = {
    "rent": "Rent",
    "salary": "Savings",
    "atm": "Other",
    "uber": "Transport",
    "ola": "Transport",
    "flipkart": "Shopping",
    "amazon": "Shopping",
    "grocery": "Groceries",
    "grocer": "Groceries",
    "netflix": "Entertainment",
    "spotify": "Entertainment",
    "restaurant": "Food & Dining",
    "food": "Food & Dining",
    "cafe": "Food & Dining",
    "coffee": "Food & Dining",
    "doctor": "Health",
    "medicine": "Health",
    "flight": "Travel",
    "ticket": "Travel",
    "taxi": "Transport",
    "bus": "Transport",
    "train": "Transport",
}

# -------------------------
# 2) Basic helpers
# -------------------------
def to_df(tx_list: List[dict]) -> pd.DataFrame:
    """
    Convert list-of-dicts (DB rows) into a pandas DataFrame.
    Ensures 'date' column is datetime and columns exist.
    """
    cols = ["id", "user_id", "date", "category", "amount", "note"]
    if not tx_list:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(tx_list)
    # normalize column names if different keys used (some code used 'description' earlier)
    if "description" in df.columns and "note" not in df.columns:
        df = df.rename(columns={"description": "note"})
    # ensure columns exist
    for c in cols:
        if c not in df.columns:
            df[c] = None
    # convert date
    try:
        df["date"] = pd.to_datetime(df["date"])
    except Exception:
        # if conversion fails leave as-is and try better conversion row-wise
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[cols]  # enforce column order
    return df

def classify_useful_waste(df: pd.DataFrame) -> Dict[str, float]:
    """
    Return totals: total, useful, wasteful, other
    """
    if df.empty:
        return {"total": 0.0, "useful": 0.0, "wasteful": 0.0, "other": 0.0}
    total = float(df["amount"].sum())
    useful = float(df[df["category"].isin(USEFUL)]["amount"].sum())
    wasteful = float(df[df["category"].isin(WASTEFUL)]["amount"].sum())
    other = total - useful - wasteful
    return {"total": total, "useful": useful, "wasteful": wasteful, "other": other}

# -------------------------
# 3) Insights & AI helpers
# -------------------------
def generate_insights(df: pd.DataFrame) -> List[str]:
    """
    Generate simple, human-friendly insights from transactions DataFrame.
    """
    insights = []
    if df.empty:
        insights.append("No transactions yet — add some to get insights.")
        return insights

    summary = classify_useful_waste(df)

    # Top category
    try:
        top_cat = df.groupby("category")["amount"].sum().idxmax()
        top_amt = df.groupby("category")["amount"].sum().max()
        insights.append(f"💰 Highest spending category: {top_cat} (₹{top_amt:.2f})")
    except Exception:
        pass

    # Wasteful percentage
    total = summary["total"] or 1.0
    waste_pct = summary["wasteful"] / total * 100
    if waste_pct > 30:
        insights.append(f"⚠️ Wasteful spending is high: {waste_pct:.0f}% of total. Consider cutting non-essential expenses.")
    else:
        insights.append(f"✅ Wasteful spending: {waste_pct:.0f}% of total.")

    # Useful vs useful percent
    useful_pct = summary["useful"] / total * 100
    insights.append(f"📊 Useful spending: {useful_pct:.0f}% of total.")

    # Monthly trend: check increasing/decreasing over last 3 months
    try:
        monthly = df.set_index("date").resample("M")["amount"].sum()
        if len(monthly) >= 3:
            last = monthly.iloc[-3:]
            if last.is_monotonic_increasing:
                insights.append("🔺 Spending has been increasing over the last months.")
            elif last.is_monotonic_decreasing:
                insights.append("🔻 Spending has been decreasing — good job!")
            else:
                insights.append("🔁 Spending trend: mixed in the recent months.")
    except Exception:
        pass

    # Suggest top two categories to trim if wasteful is high
    if waste_pct > 20:
        waste_df = df[df["category"].isin(WASTEFUL)]
        by_cat = waste_df.groupby("category")["amount"].sum().sort_values(ascending=False)
        top = by_cat.head(2).to_dict()
        for cat, amt in top.items():
            insights.append(f"💡 Consider reducing {cat}: ₹{amt:.2f} total recently.")

    # final fallback
    if not insights:
        insights.append("✅ Your spending looks balanced!")

    return insights

# -------------------------
# 4) Category suggestion (rule-based + OpenAI optional)
# -------------------------
def suggest_category_from_note(note: str) -> Optional[str]:
    """
    Rule-based keyword matching to suggest a category from a free-text note.
    Returns a category or None.
    """
    if not note or not isinstance(note, str):
        return None
    text = note.lower()
    # direct keyword match
    for kw, cat in KEYWORD_MAP.items():
        if kw in text:
            return cat
    # token-level heuristic
    tokens = [t.strip(".,!?:;()\"'") for t in text.split()]
    for t in tokens:
        if t in KEYWORD_MAP:
            return KEYWORD_MAP[t]
    return None

def suggest_category_with_openai(note: str) -> Optional[str]:
    """
    Optional OpenAI fallback. Requires environment variable OPENAI_API_KEY.
    If OpenAI not configured or any error happens, returns None.
    """
    try:
        key = os.environ.get("OPENAI_API_KEY")
        if not key or not note:
            return None
        import openai  # optional dependency
        openai.api_key = key
        prompt = (
            f"Given this transaction note: '{note}', "
            f"suggest a single category from this list: {', '.join(CATEGORIES)}. "
            "Respond with the exact category name only."
        )
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.0,
        )
        cat = resp.choices[0].message.content.strip()
        if cat in CATEGORIES:
            return cat
    except Exception:
        return None
    return None

def auto_suggest_category(note: str) -> Optional[str]:
    """
    Try rule-based suggestion first, then optionally OpenAI fallback.
    """
    r = suggest_category_from_note(note)
    if r:
        return r
    r2 = suggest_category_with_openai(note)
    return r2

# -------------------------
# 5) Summaries: daily/weekly/monthly
# -------------------------
def get_daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns DataFrame with columns: date, total
    """
    if df.empty:
        return pd.DataFrame(columns=["date", "total"])
    d = df.set_index("date").resample("D")["amount"].sum().reset_index()
    d = d.rename(columns={"amount": "total"})
    return d

def get_weekly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["week_start", "total"])
    w = df.set_index("date").resample("W-MON")["amount"].sum().reset_index()
    w = w.rename(columns={"date": "week_start", "amount": "total"})
    return w

def get_monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["month", "total"])
    m = df.set_index("date").resample("M")["amount"].sum().reset_index()
    m["month"] = m["date"].dt.to_period("M").astype(str)
    m = m.rename(columns={"amount": "total"})
    return m[["month", "total"]]

# -------------------------
# 6) Recurring transactions helper
# -------------------------
def generate_recurring_dates(start_date: date, frequency: str, count: int = 12) -> List[date]:
    """
    Generate next 'count' recurring dates from start_date given frequency:
    frequency: 'monthly', 'weekly'
    Returns list of date objects.
    """
    res = []
    current = start_date
    for _ in range(count):
        res.append(current)
        if frequency == "monthly":
            current = current + relativedelta(months=1)
        elif frequency == "weekly":
            current = current + timedelta(weeks=1)
        else:
            # default to monthly
            current = current + relativedelta(months=1)
    return res

# -------------------------
# 7) Export helpers
# -------------------------
def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """
    Return CSV bytes suitable for st.download_button.
    """
    out = df.copy()
    # format date
    if "date" in out.columns:
        out["date"] = out["date"].astype(str)
    return out.to_csv(index=False).encode("utf-8")

def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    """
    Return Excel bytes (xlsx) suitable for st.download_button.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        out = df.copy()
        if "date" in out.columns:
            out["date"] = out["date"].astype(str)
        out.to_excel(writer, index=False, sheet_name="Transactions")
        writer.save()
    output.seek(0)
    return output.read()

# -------------------------
# 8) Budget & savings helpers
# -------------------------
def calculate_budget_status(df: pd.DataFrame, monthly_budget: float) -> Dict[str, float]:
    """
    Returns dict with spent_this_month, budget, pct_used
    """
    if df.empty or monthly_budget <= 0:
        return {"spent_this_month": 0.0, "budget": float(monthly_budget), "pct_used": 0.0}
    now = pd.Timestamp.now()
    start = now.to_period("M").to_timestamp()
    df_copy = df.copy()
    df_copy["month"] = df_copy["date"].dt.to_period("M")
    spent = df_copy[df_copy["month"] == now.to_period("M")]["amount"].sum()
    pct = float(spent) / float(monthly_budget) if monthly_budget > 0 else 0.0
    return {"spent_this_month": float(spent), "budget": float(monthly_budget), "pct_used": pct}

def check_savings_goal(current_savings: float, goal_amount: float) -> Dict[str, float]:
    """
    Given current savings and a goal, return progress % and remaining amount.
    """
    if goal_amount <= 0:
        return {"progress_pct": 0.0, "remaining": 0.0}
    remaining = max(0.0, goal_amount - current_savings)
    pct = min(100.0, (current_savings / goal_amount) * 100.0)
    return {"progress_pct": pct, "remaining": remaining}

# -------------------------
# 9) Category analytics
# -------------------------
def get_category_averages(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return DataFrame with category, total, avg_per_month
    """
    if df.empty:
        return pd.DataFrame(columns=["category", "total", "avg_per_month"])
    dfc = df.copy()
    dfc["month"] = dfc["date"].dt.to_period("M")
    total_by_cat = dfc.groupby("category")["amount"].sum().reset_index().rename(columns={"amount": "total"})
    months = dfc["month"].nunique() or 1
    total_by_cat["avg_per_month"] = total_by_cat["total"] / float(months)
    return total_by_cat

def compare_category_vs_average(df: pd.DataFrame, category: str) -> Dict[str, float]:
    """
    For a given category return current_month_amount and average_month_amount and pct_diff.
    """
    if df.empty or category not in df["category"].unique():
        return {"current_month": 0.0, "avg_month": 0.0, "pct_diff": 0.0}
    now = pd.Timestamp.now().to_period("M")
    dfc = df.copy()
    dfc["month"] = dfc["date"].dt.to_period("M")
    avg = dfc[dfc["category"] == category].groupby("month")["amount"].sum().mean()
    current = dfc[(dfc["category"] == category) & (dfc["month"] == now)]["amount"].sum()
    avg = float(avg) if not pd.isna(avg) else 0.0
    pct_diff = ((current - avg) / avg * 100.0) if avg > 0 else 0.0
    return {"current_month": float(current), "avg_month": float(avg), "pct_diff": pct_diff}

# -------------------------
# 10) Waste detection & tips
# -------------------------
WASTE_TIPS = {
    "Entertainment": "Consider reducing streaming or event costs; share subscriptions or switch to cheaper plans.",
    "Shopping": "Delay non-essential purchases for 30 days; track wishlist items before buying.",
    "Food & Dining": "Cook at home more often and limit dining out to special occasions.",
    "Travel": "Look for deals, travel off-peak, or reduce short leisure trips to save.",
}

def detect_waste_risk(df: pd.DataFrame, threshold_pct: float = 0.30) -> List[str]:
    """
    Return a list of warnings/tips when wasteful spending exceeds threshold_pct of total.
    """
    tips = []
    summary = classify_useful_waste(df)
    total = summary["total"] or 1.0
    waste_pct = summary["wasteful"] / total
    if waste_pct >= threshold_pct:
        tips.append(f"High wasteful spending: {waste_pct*100:.0f}% of total.")
        # recommend categories to trim
        waste_df = df[df["category"].isin(WASTEFUL)]
        by_cat = waste_df.groupby("category")["amount"].sum().sort_values(ascending=False)
        for cat, amt in by_cat.head(3).items():
            tip = WASTE_TIPS.get(cat, "Review your expenses in this category.")
            tips.append(f"Trim {cat}: ₹{amt:.2f}. {tip}")
    return tips

# -------------------------
# 11) Small utilities
# -------------------------
def summarize_top_categories(df: pd.DataFrame, top_n: int = 3) -> List[Tuple[str, float]]:
    if df.empty:
        return []
    by_cat = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    return list(by_cat.head(top_n).items())

def safe_float(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0
