"""core.store — NICO 顧客管理。farm_customers との紐付け用。"""
import time
from core.db import conn


def get_or_create_customer(name: str, email: str = "", sns_handle: str = "", line_user_id: str = "") -> int:
    """既存顧客を名前で検索、なければ作成。id を返す。"""
    with conn() as c:
        row = c.execute(
            "SELECT id FROM customers WHERE name = ? OR email = ?", (name, email)
        ).fetchone()
        if row:
            return row["id"]
        cursor = c.execute(
            "INSERT INTO customers(name, email, line_user_id, sns_handle, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, email, line_user_id, sns_handle, time.time()),
        )
        return cursor.lastrowid
