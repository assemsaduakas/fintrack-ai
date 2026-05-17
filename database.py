import os
import sqlite3
from datetime import datetime
from typing import Optional


class DatabaseManager:
    def __init__(self, db_path: str = "db/expenses.db"):
        self.db_path = db_path
        self._ensure_db_dir()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _ensure_db_dir(self) -> None:
        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def _create_tables(self) -> None:
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    date TEXT NOT NULL
                )
                """
            )

    def add_expense(
        self,
        amount: float,
        category: str,
        description: str,
        date: Optional[str] = None,
    ) -> str:
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        with self.conn:
            self.conn.execute(
                "INSERT INTO expenses (amount, category, description, date) VALUES (?, ?, ?, ?)",
                (amount, category, description, date),
            )

        return f"Logged expense ${amount:.2f} for {category} on {date}."

    def get_recent_expenses(self, limit: int = 10) -> str:
        cursor = self.conn.execute(
            "SELECT date, category, description, amount FROM expenses ORDER BY date DESC, id DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        if not rows:
            return "No expenses have been recorded yet."

        lines = ["Recent expenses:"]
        for row in rows:
            lines.append(
                f"{row['date']} | {row['category']} | ${row['amount']:.2f} | {row['description']}"
            )
        return "\n".join(lines)

    def get_summary(self, period: str = "month", category: Optional[str] = None) -> str:
        query = "SELECT category, SUM(amount) AS total, COUNT(*) AS count FROM expenses"
        params = []
        where_clauses = []

        if period.lower() in ["month", "this month"]:
            where_clauses.append("strftime('%Y-%m', date) = strftime('%Y-%m', 'now')")
        elif period.lower() in ["year", "this year"]:
            where_clauses.append("strftime('%Y', date) = strftime('%Y', 'now')")

        if category:
            where_clauses.append("category = ?")
            params.append(category)

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " GROUP BY category ORDER BY total DESC"

        cursor = self.conn.execute(query, tuple(params))
        rows = cursor.fetchall()
        if not rows:
            return f"No expenses found for {period} " + (f"and category {category}." if category else ".")

        lines = [f"Expense summary for {period}:"]
        for row in rows:
            lines.append(f"{row['category']}: ${row['total']:.2f} across {row['count']} transactions")
        return "\n".join(lines)
