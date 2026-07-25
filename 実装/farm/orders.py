"""farm.orders — 受注・状態遷移ヘルパ（Module A 所有）。
B はこのモジュールを import しない。境界は farm_orders テーブルだけ。

所有するステータス遷移:
  (新規) → provisional        : create_order()
  set_composed → customer_confirm: mark_as_pending_confirmation()
  customer_confirm → confirmed: confirm_order()
  confirmed → paid            : mark_paid() ← Stripe webhook から呼ばれる
"""

import time
from farm.store import (
    create_order as _create_order,
    get_order,
    transition_order_status,
    mark_paid as _mark_paid,
)


def create_order(customer_id: int, order_type: str = "spot", plan: str = "") -> int:
    """provisional の注文を作成して id を返す（Module A 所有）。"""
    return _create_order(customer_id, order_type, plan)


def mark_paid(order_id: int, stripe_session_id: str) -> None:
    """confirmed → paid（Stripe webhook から呼ぶ、Module A 所有）。"""
    _mark_paid(order_id, stripe_session_id)


def confirm_order(order_id: int, amount: int) -> dict:
    """customer_confirm → confirmed。amount を確定。
    戻り値: 更新後の注文辞書。
    """
    order = get_order(order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found")
    current = order["status"]
    if current not in ("customer_confirm", "confirmed"):
        raise ValueError(f"Cannot confirm order with status '{current}' (expected 'customer_confirm' or 'confirmed')")
    transition_order_status(order_id, "confirmed", amount)
    return get_order(order_id)


def mark_as_pending_confirmation(order_id: int) -> dict:
    """set_composed → customer_confirm。客に提示する状態に遷移。"""
    order = get_order(order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found")
    if order["status"] != "set_composed":
        raise ValueError(f"Cannot mark as pending confirmation: status is '{order['status']}' (expected 'set_composed')")
    transition_order_status(order_id, "customer_confirm", order.get("amount", 0))
    return get_order(order_id)
