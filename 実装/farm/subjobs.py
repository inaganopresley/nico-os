"""farm.subjobs — 定期注文生成ジョブ（Module A 所有）。
main.py の 3AM consolidation スレッドを雛形に、next_delivery_on が来たサブスクへ
provisional 注文を自動生成する。まずは手動トリガ関数＋管理ボタンで可。

関数契約:
  generate_recurring_orders() → list[int]  (生成した注文idのリスト)
"""

import datetime
from farm.store import get_active_subscriptions, upsert_customer, create_order


def _format_date(d) -> str:
    if isinstance(d, datetime.datetime):
        return d.strftime("%Y-%m-%d")
    return str(d)


def generate_recurring_orders() -> list[int]:
    """next_delivery_on が今日以降の active サブスクから provisional 注文を生成。
    戻り値: 生成した注文idのリスト。
    """
    from core.db import conn
    from core.store import get_or_create_customer as nico_get_or_create

    today = _format_date(datetime.datetime.now())
    orders_created = []

    subs = get_active_subscriptions()
    for sub in subs:
        delivery_on = sub.get("next_delivery_on", "")
        if not delivery_on or delivery_on > today:
            continue  # まだ配送日ではない

        nico_id = sub.get("nico_customer_id") or 0
        customer = upsert_customer(
            nico_customer_id=nico_id,
            name=sub.get("name", ""),
            sns_handle=sub.get("sns_handle", ""),
            line_user_id=sub.get("line_user_id", ""),
        )

        order_id = create_order(customer, order_type="subscription", plan=sub.get("plan", ""))
        orders_created.append(order_id)

        # 次の配送日を1週間後に設定（簡易）
        next_on = (datetime.datetime.now() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        with conn() as c:
            c.execute(
                "UPDATE farm_subscriptions SET next_delivery_on = ? WHERE id = ?",
                (next_on, sub["id"]),
            )

    return orders_created
