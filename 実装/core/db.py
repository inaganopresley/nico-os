"""core.db — DB connection layer. PG (本番) / SQLite (ローカル) 両対応。
conn() は context manager として使い、トランザクションを自動管理する。
重要: スキーマ文字列に行コメント(--)を書かない（本番PGでCREATE TABLEが飛ぶ）。"""

import os
import sqlite3
from contextlib import contextmanager

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app.db")
_PG_URL = os.environ.get("DATABASE_URL")  # Railway Postgres


def _is_pg() -> bool:
    return bool(_PG_URL)


@contextmanager
def conn():
    """DB接続を返すコンテキストマネージャ。PG用は未実装（ローカルSQLiteのみ）。
    SQLite は close 時に自動コミットする。"""
    if _is_pg():
        import psycopg2
        with psycopg2.connect(_PG_URL) as conn:
            yield conn
    else:
        db = sqlite3.connect(_DB_PATH)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


def init_core():
    """core テーブルの初期化（customers など）。"""
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            line_user_id TEXT,
            sns_handle TEXT,
            created_at REAL NOT NULL
        )""")
