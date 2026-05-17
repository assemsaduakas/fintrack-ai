#!/usr/bin/env python3
"""Seed the FinTrack AI SQLite database with deterministic test data.

Usage: python scripts/seed_test_data.py --count 50 --db db/expenses.db
"""
import argparse
import random
from datetime import datetime, timedelta
from database import DatabaseManager


def generate_entries(count: int):
    categories = ["Groceries", "Food & Drink", "Transport", "Entertainment", "Utilities", "Health"]
    descriptions = {
        "Groceries": ["Weekly grocery shopping", "Supermarket purchase", "Grocery essentials"],
        "Food & Drink": ["Coffee", "Lunch", "Takeout"],
        "Transport": ["Bus fare", "Taxi", "Gasoline"],
        "Entertainment": ["Movie", "Streaming subscription", "Concert"],
        "Utilities": ["Electricity bill", "Internet", "Water bill"],
        "Health": ["Pharmacy", "Doctor visit", "Vitamins"],
    }

    today = datetime.utcnow().date()
    entries = []
    for i in range(count):
        cat = random.choice(categories)
        desc = random.choice(descriptions[cat])
        # spread dates over the last 90 days
        days_ago = random.randint(0, 89)
        date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        # amounts vary by category ranges
        if cat == "Groceries":
            amount = round(random.uniform(5, 120), 2)
        elif cat == "Food & Drink":
            amount = round(random.uniform(2, 40), 2)
        elif cat == "Transport":
            amount = round(random.uniform(1, 60), 2)
        elif cat == "Entertainment":
            amount = round(random.uniform(5, 150), 2)
        elif cat == "Utilities":
            amount = round(random.uniform(20, 300), 2)
        else:
            amount = round(random.uniform(3, 200), 2)

        entries.append((amount, cat, desc, date))

    return entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=50, help="Number of entries to insert")
    parser.add_argument("--db", type=str, default="db/expenses.db", help="Path to SQLite DB")
    parser.add_argument("--clear", action="store_true", help="Clear existing expenses before inserting")
    args = parser.parse_args()

    db = DatabaseManager(db_path=args.db)

    if args.clear:
        with db.conn:
            db.conn.execute("DELETE FROM expenses")
        print(f"Cleared existing expenses in {args.db}")

    entries = generate_entries(args.count)
    for amt, cat, desc, date in entries:
        db.add_expense(amount=amt, category=cat, description=desc, date=date)

    cursor = db.conn.execute("SELECT COUNT(*) as c FROM expenses")
    total = cursor.fetchone()[0]
    print(f"Inserted {len(entries)} entries. Total rows in DB: {total}")

    # show recent 5 rows
    print("\nRecent 5 expenses:")
    cursor = db.conn.execute(
        "SELECT date, category, description, amount FROM expenses ORDER BY date DESC, id DESC LIMIT 5"
    )
    for row in cursor.fetchall():
        print(f"{row['date']} | {row['category']} | ${row['amount']:.2f} | {row['description']}")


if __name__ == "__main__":
    main()
