"""farm.pay — Stripe スポット決済（Module A 所有）。
billing/routes.py のサブスク checkout が雛形。ここでは mode=payment を新規実装。

関数契約:
  create_checkout_session(order_id) → {"url": str, "session_id": str}
  handle_webhook_event(event) → None  (既存 /billing/webhook から呼ばれる)
"""

import os

_stripe = None
try:
    import stripe
    _stripe = stripe
    _stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
except ImportError:
    pass


def create_checkout_session(order_id: int, success_url: str = "", cancel_url: str = "") -> dict:
    """スポット決済の checkout セッションを作成。"""
    if not _stripe:
        return {"error": "Stripe not available"}

    from farm.store import get_order
    order = get_order(order_id)
    if not order:
        return {"error": f"Order {order_id} not found"}
    if order["status"] != "confirmed":
        return {"error": f"Cannot checkout order with status '{order['status']}' (expected 'confirmed')"}

    amount = order.get("amount", 0)
    if amount <= 0:
        return {"error": "Order amount is not set"}

    success_url = success_url or os.environ.get("STRIPE_SUCCESS_URL", "http://localhost:8000/farm/order/success")
    cancel_url = cancel_url or os.environ.get("STRIPE_CANCEL_URL", "http://localhost:8000/farm/order/cancel")

    try:
        session = _stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "jpy",
                    "unit_amount": amount,
                    "product_data": {
                        "name": f"淡路ベジ便野菜セット (注文 #{order_id})",
                    },
                },
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"farm_order_id": order_id},
        )
        # 現在のセッションIDを注文に記録
        from farm.store import transition_order_status
        transition_order_status(order_id, "confirmed", amount)
        return {"url": session.url, "session_id": session.id}
    except Exception as e:
        return {"error": str(e)}


def handle_checkout_completed(event_data: dict) -> None:
    """checkout.session.completed イベントを処理し、注文を paid に遷移（Module A 所有）。"""
    session = event_data.get("object", {})
    metadata = session.get("metadata", {})
    order_id = metadata.get("farm_order_id")
    if not order_id:
        return
    mark_paid(order_id, session.get("id", ""))


def mark_paid(order_id: int, stripe_session_id: str) -> None:
    """confirmed → paid（webhook から呼ぶ）。"""
    from farm.store import mark_paid as _mark_paid
    _mark_paid(order_id, stripe_session_id)
