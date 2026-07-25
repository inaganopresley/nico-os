"""farm.seed_dev — 開発用シード。`python -m farm.seed_dev` で投入。
A/B が相手未完成でも進めるためのダミー行もここに置く（01_インターフェース契約.md §5）。
"""

from farm import store
from farm.store import conn, now


def seed():
    store.init_farm()
    # core テーブルも初期化
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            line_user_id TEXT,
            sns_handle TEXT,
            created_at REAL NOT NULL
        )""")
        c.commit()
    print("seed: core tables done")

    with conn() as c:
        # 農家シード（Module B）
        c.execute(
            "INSERT INTO farm_farmers(name, region, line_user_id, active, created_at) VALUES (?, ?, ?, ?, ?)",
            ("淡路 太郎", "淡路島", None, 1, now()),
        )
        c.execute(
            "INSERT INTO farm_farmers(name, region, line_user_id, active, created_at) VALUES (?, ?, ?, ?, ?)",
            ("洲本 花子", "淡路島", None, 1, now()),
        )
        c.execute(
            "INSERT INTO farm_farmers(name, region, line_user_id, active, created_at) VALUES (?, ?, ?, ?, ?)",
            ("南あわじ 次郎", "淡路島", None, 1, now()),
        )

        # 出荷実績シード（Module B）
        import datetime
        for i, (veg, qty, unit, days_ago) in enumerate([
            ("玉ねぎ", 10, "kg", 1),
            ("人参", 8, "kg", 1),
            ("大根", 5, "本", 2),
            ("キャベツ", 6, "個", 2),
            ("トマト", 12, "kg", 3),
            ("きゅうり", 7, "kg", 3),
            ("ピーマン", 4, "kg", 4),
        ]):
            shipped = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")
            c.execute(
                "INSERT INTO farm_shipments(farmer_id, veg_name, qty, unit, shipped_on, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ((i % 3) + 1, veg, qty, unit, shipped, now()),
            )

        c.commit()

    print("seed: farmers + shipments done")


def seed_dummy_vegset():
    """A が B の完成を待たずに M2-A を先行開発するためのダミー vegset（01 §5）。"""
    with conn() as c:
        # ダミー顧客＋注文
        from core.store import get_or_create_customer as nico_upsert
        nico_id = nico_upsert("テスト客", sns_handle="@test")
        cid = store.upsert_customer(nico_customer_id=nico_id, name="テスト客", sns_handle="@test")
        oid = store.create_order(cid, order_type="spot")

        # ダミー vegset（final）
        items = '[{"veg":"玉ねぎ","qty":2,"unit":"kg","farmer_id":1},{"veg":"人参","qty":1.5,"unit":"kg","farmer_id":2}]'
        veg_cur = c.execute(
            "INSERT INTO farm_vegsets(order_id, variety_count, items_json, status, composed_at) VALUES (?, ?, ?, 'final', ?)",
            (oid, 2, items, now()),
        )

        # 注文を set_composed に
        c.execute(
            "UPDATE farm_orders SET status = 'set_composed', vegset_id = ?, updated_at = ? WHERE id = ?",
            (veg_cur.lastrowid, now(), oid),
        )

        c.commit()

    print("seed: dummy vegset + provisional order done (for Module A advance)")


def seed_all():
    seed()
    seed_dummy_vegset()
    print("seed_all done")


if __name__ == "__main__":
    seed_all()
