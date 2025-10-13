# db.py
import sqlite3
import os
from typing import List, Dict, Optional
from passlib.hash import pbkdf2_sha256

# SQLite database file
DB_PATH = os.environ.get("DB_PATH", "data.db")  # change via env if needed

# Function to get DB connection
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database with tables
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );
    """)
    # Transactions table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        note TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    conn.commit()
    conn.close()

# Create a new user
def create_user(username: str, password: str) -> int:
    pw_hash = pbkdf2_sha256.hash(password)
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pw_hash))
        conn.commit()
        user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        user_id = -1  # username already exists
    conn.close()
    return user_id

# Get user by username
def get_user_by_username(username: str) -> Optional[Dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

# Verify user login
def verify_user(username: str, password: str) -> Optional[Dict]:
    user = get_user_by_username(username)
    if not user:
        return None
    if pbkdf2_sha256.verify(password, user["password_hash"]):
        return user
    return None

# Add a transaction
def add_transaction(user_id: int, date: str, category: str, amount: float, note: str = "") -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transactions (user_id, date, category, amount, note) VALUES (?, ?, ?, ?, ?)",
        (user_id, date, category, amount, note)
    )
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return tid

# Get all transactions of a user
def get_transactions_by_user(user_id: int) -> List[Dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Update a transaction
def update_transaction(tx_id: int, user_id: int, date: str, category: str, amount: float, note: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE transactions SET date=?, category=?, amount=?, note=?
        WHERE id=? AND user_id=?
    """, (date, category, amount, note, tx_id, user_id))
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed

# Delete a transaction
def delete_transaction(tx_id: int, user_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (tx_id, user_id))
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok

# db.py — add at bottom (or replace simpler versions)
def update_transaction(tx_id: int, user_id: int, date: str, category: str, amount: float, note: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE transactions
        SET date = ?, category = ?, amount = ?, note = ?
        WHERE id = ? AND user_id = ?
    """, (date, category, amount, note, tx_id, user_id))
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed

def delete_transaction(tx_id: int, user_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user_id))
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok