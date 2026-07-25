"""farm.routes — APIRouter（Module A: 受注・顧客・決済）。

ルート一覧:
  GET  /farm                → ホーム
  GET  /farm/order          → 注文フォーム
  POST /farm/order          → 注文受付（provisional）
  GET  /farm/order/{id}     → 注文状況・確認画面
  POST /farm/order/{id}/confirm → 注文確定（customer_confirm→confirmed）
  POST /farm/order/{id}/pay   → Stripe決済
  GET  /farm/admin/orders       → 管理：注文一覧
  GET  /farm/admin/trigger-recurring → 定期ジョブ画面
  POST /farm/admin/trigger-recurring → 定期ジョブ実行
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from farm import ui
from farm.store import (
    upsert_customer,
    get_order,
    list_orders,
    get_vegset_by_order,
)
from farm.orders import confirm_order, mark_as_pending_confirmation
from farm.pay import create_checkout_session

router = APIRouter()


# ---- M0: ホーム ----

@router.get("/farm", response_class=HTMLResponse)
def farm_home(request: Request):
    return HTMLResponse(ui.home())


# ---- M1-A: 受注フォーム ----

@router.get("/farm/order", response_class=HTMLResponse)
def order_form_page(request: Request):
    return HTMLResponse(ui.order_form())


@router.post("/farm/order")
async def order_submit(request: Request):
    form = await request.form()
    name = form.get("name", "")
    sns_handle = form.get("sns_handle", "")
    line_user_id = form.get("line_user_id", "")
    order_type = form.get("order_type", "spot")
    plan = form.get("plan", "")

    if not name:
        return HTMLResponse("<p class='error'>名前を入力してください。</p><a href='/farm/order'>戻る</a>")

    # customer_id を作成（NICO customers と farm_customers の両方を upsert）
    from core.store import get_or_create_customer as nico_upsert
    nico_id = nico_upsert(name, sns_handle=sns_handle, line_user_id=line_user_id)
    customer_id = upsert_customer(nico_customer_id=nico_id, name=name, sns_handle=sns_handle, line_user_id=line_user_id)

    # provisional 注文を作成
    from farm.store import create_order as _create_order
    order_id = _create_order(customer_id, order_type=order_type, plan=plan)

    return HTMLResponse(ui.order_success(order_id))


# ---- M2-A: 客の確認画面 ----

@router.get("/farm/order/{order_id}", response_class=HTMLResponse)
def order_status_page(request: Request, order_id: int):
    order = get_order(order_id)
    if not order:
        return HTMLResponse(f"<p class='error'>注文 #{order_id} が見つかりません。</p>")

    vegset = get_vegset_by_order(order_id)
    return HTMLResponse(ui.order_status(order, vegset))


@router.post("/farm/order/{order_id}/confirm")
async def order_confirm(request: Request, order_id: int):
    """customer_confirm → confirmed（Module A 所有）。"""
    order = get_order(order_id)
    if not order:
        return HTMLResponse("<p class='error'>注文が見つかりません。</p>")

    # set_composed なら customer_confirm に遷移
    if order["status"] == "set_composed":
        mark_as_pending_confirmation(order_id)
        order = get_order(order_id)

    amount = order.get("amount", 0)
    try:
        updated = confirm_order(order_id, amount or 3500)  # デフォルト金額
    except ValueError as e:
        return HTMLResponse(f"<p class='error'>{e}</p>")

    return RedirectResponse(url=f"/farm/order/{order_id}")


@router.post("/farm/order/{order_id}/pay")
async def order_pay(request: Request, order_id: int):
    """Stripe スポット決済（Module A 所有）。"""
    result = create_checkout_session(order_id)
    if "error" in result:
        return HTMLResponse(f"<p class='error'>{result['error']}</p>")

    # Stripe checkout へリダイレクト
    return RedirectResponse(url=result["url"])


# ---- M1-A/B 共有: 管理コンソール注文一覧 ----

@router.get("/farm/admin/orders", response_class=HTMLResponse)
def admin_orders_page(request: Request):
    orders = list_orders(limit=50)
    return HTMLResponse(ui.admin_orders(orders))


# ---- M4-A: サブスク定期ジョブ ----

@router.get("/farm/admin/trigger-recurring", response_class=HTMLResponse)
def admin_trigger_page(request: Request):
    return HTMLResponse(ui.admin_trigger_recurring())


@router.post("/farm/admin/trigger-recurring")
async def admin_trigger_recurring(request: Request):
    from farm.subjobs import generate_recurring_orders
    order_ids = generate_recurring_orders()
    return HTMLResponse(ui.recurring_result(order_ids))
