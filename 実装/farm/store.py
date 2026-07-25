"""farm.store — データ層。core.db.conn() を使う。DDLは既存NICOテーブルに倣う。
重要: スキーマ文字列に行コメント(--)を書かない（本番PGでCREATE TABLEが飛ぶ地雷）。
"""

import json
import time
from core.db import conn

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS farm_farmers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        region TEXT NOT NULL DEFAULT '淡路島',
        line_user_id TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        created_at REAL NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS farm_shipments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id INTEGER,
        veg_name TEXT NOT NULL,
        qty REAL,
        unit TEXT,
        shipped_on TEXT,
        created_at REAL NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS farm_polls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        region TEXT,
        question TEXT,
        status TEXT NOT NULL DEFAULT 'open',
        created_at REAL NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS farm_availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        poll_id INTEGER,
        farmer_id INTEGER,
        veg_name TEXT,
        qty REAL,
        raw_text TEXT,
        status TEXT,
        replied_at REAL
    )""",
    """CREATE TABLE IF NOT EXISTS farm_vegsets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        variety_count INTEGER,
        items_json TEXT,
        status TEXT NOT NULL DEFAULT 'draft',
        composed_at REAL
    )""",
    """CREATE TABLE IF NOT EXISTS farm_customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nico_customer_id INTEGER,
        name TEXT,
        sns_handle TEXT,
        line_user_id TEXT,
        created_at REAL NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS farm_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        order_type TEXT NOT NULL DEFAULT 'spot',
        plan TEXT,
        status TEXT NOT NULL DEFAULT 'provisional',
        vegset_id INTEGER,
        amount INTEGER,
        stripe_session_id TEXT,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS farm_subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        plan TEXT,
        stripe_subscription_id TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        next_delivery_on TEXT,
        created_at REAL NOT NULL
    )""",
]


def init_farm() -> None:
    """farm_* テーブルを初期化。"""
    with conn() as c:
        for ddl in _SCHEMA:
            c.execute(ddl)


def now() -> float:
    return time.time()


# ---- farm_customers (Module A 書き込み) ----

def upsert_customer(nico_customer_id: int, name: str, sns_handle: str = "", line_user_id: str = "") -> int:
    """farm_customers を upsert。id を返す。"""
    with conn() as c:
        row = c.execute(
            "SELECT id FROM farm_customers WHERE nico_customer_id = ?", (nico_customer_id,)
        ).fetchone()
        if row:
            c.execute(
                "UPDATE farm_customers SET name=?, sns_handle=?, line_user_id=?, created_at=? WHERE id=?",
                (name, sns_handle, line_user_id, now(), row["id"]),
            )
            return row["id"]
        cur = c.execute(
            "INSERT INTO farm_customers(nico_customer_id, name, sns_handle, line_user_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (nico_customer_id, name, sns_handle, line_user_id, now()),
        )
        return cur.lastrowid


def get_customer(customer_id: int) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM farm_customers WHERE id = ?", (customer_id,)).fetchone()
        return dict(row) if row else None


# ---- farm_orders (共有・Module A 所有遷移: provisional / customer_confirm→confirmed / confirmed→paid) ----

def create_order(customer_id: int, order_type: str = "spot", plan: str = "") -> int:
    """provisional の注文を作成。id を返す（Module A が所有）。"""
    t = now()
    with conn() as c:
        cur = c.execute(
            "INSERT INTO farm_orders(customer_id, order_type, plan, status, amount, created_at, updated_at) VALUES (?, ?, ?, 'provisional', 0, ?, ?)",
            (customer_id, order_type, plan, t, t),
        )
        return cur.lastrowid


def get_order(order_id: int) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM farm_orders WHERE id = ?", (order_id,)).fetchone()
        return dict(row) if row else None


def list_orders(status: str | None = None, limit: int = 50) -> list[dict]:
    """注文一覧。status でフィルタ可。"""
    with conn() as c:
        if status:
            rows = c.execute(
                "SELECT * FROM farm_orders WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM farm_orders ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def transition_order_status(order_id: int, new_status: str, amount: int = 0) -> None:
    """status を更新（Module A が所有する遷移のみから呼ぶ）。"""
    with conn() as c:
        c.execute(
            "UPDATE farm_orders SET status = ?, amount = ?, updated_at = ? WHERE id = ?",
            (new_status, amount, now(), order_id),
        )


def mark_paid(order_id: int, stripe_session_id: str) -> None:
    """confirmed → paid（Stripe webhook から呼ぶ、Module A 所有）。"""
    with conn() as c:
        c.execute(
            "UPDATE farm_orders SET status = 'paid', stripe_session_id = ?, updated_at = ? WHERE id = ?",
            (stripe_session_id, now(), order_id),
        )


# ---- farm_vegsets (Module B 書き込み・Module A は読むだけ) ----

def get_vegset(vegset_id: int) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM farm_vegsets WHERE id = ?", (vegset_id,)).fetchone()
        if row:
            d = dict(row)
            if d.get("items_json"):
                d["items_json"] = json.loads(d["items_json"])
            return d
    return None


def get_vegset_by_order(order_id: int) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM farm_vegsets WHERE order_id = ? AND status = 'final'", (order_id,)).fetchone()
        if row:
            d = dict(row)
            if d.get("items_json"):
                d["items_json"] = json.loads(d["items_json"])
            return d
    return None


# ---- farm_subscriptions (Module A 書き込み) ----

def create_subscription(customer_id: int, plan: str, stripe_subscription_id: str, next_delivery_on: str) -> int:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO farm_subscriptions(customer_id, plan, stripe_subscription_id, status, next_delivery_on, created_at) VALUES (?, ?, ?, 'active', ?, ?)",
            (customer_id, plan, stripe_subscription_id, next_delivery_on, now()),
        )
        return cur.lastrowid


def get_active_subscriptions() -> list[dict]:
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM farm_subscriptions WHERE status = 'active' ORDER BY next_delivery_on ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_subscription(sub_id: int) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM farm_subscriptions WHERE id = ?", (sub_id,)).fetchone()
        return dict(row) if row else None
