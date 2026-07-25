"""farm.ui — HTMLテンプレート（f-string。Jinjaは使わない既存流儀）。
Module A が担当する画面: ホーム、注文フォーム、注文確認・ステータス表示。
"""


def _css() -> str:
    return """
    body { font-family: sans-serif; max-width: 640px; margin: 40px auto; color: #222; }
    h1 { border-bottom: 2px solid #3a7; padding-bottom: 8px; }
    h2 { color: #555; font-size: 1.1em; }
    .card { background: #f9f9f9; border: 1px solid #ddd; border-radius: 6px; padding: 16px; margin: 12px 0; }
    .btn { display: inline-block; padding: 8px 20px; background: #3a7; color: #fff; text-decoration: none; border-radius: 4px; border: none; cursor: pointer; font-size: 1em; }
    .btn:hover { background: #2c5; }
    .btn:disabled { background: #aaa; cursor: default; }
    table { width: 100%; border-collapse: collapse; margin: 8px 0; }
    th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #eee; }
    th { background: #f2f2f2; font-size: 0.9em; }
    .status { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.85em; }
    .status-provisional { background: #ffe0b2; }
    .status-set_requested { background: #bbdefb; }
    .status-set_composed { background: #c8e6c9; }
    .status-customer_confirm { background: #fff9c4; }
    .status-confirmed { background: #a5d6a7; }
    .status-paid { background: #81c784; color: #fff; }
    .status-shipped { background: #90caf9; }
    .status-cancelled { background: #ef9a9a; }
    label { display: block; margin: 8px 0 2px; font-weight: bold; font-size: 0.9em; }
    input, select { width: 100%; padding: 6px 8px; border: 1px solid #ccc; border-radius: 3px; box-sizing: border-box; }
    .hidden { display: none; }
    a { color: #3a7; }
    .success { color: #2c5; font-weight: bold; }
    .error { color: #c44; }
    """


def home() -> str:
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><title>淡路ベジ便</title>
<style>{_css()}</style></head><body>
<h1>淡路ベジ便</h1>
<p>淡路島の畑から、その日採れた野菜セットを全国へ。</p>
<div class="card">
  <a href="/farm/order" class="btn">注文する</a>
</div>
<p><small>M0 稼働中。次: モジュールA=/farm/order / モジュールB=/farm/admin</small></p>
</body></html>"""


def order_form() -> str:
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><title>注文 — 淡路ベジ便</title>
<style>{_css()}</style>
<script>
function togglePlan() {{
  var planDiv = document.getElementById('planSection');
  planDiv.classList.toggle('hidden', document.getElementById('order_type').value !== 'subscription');
}}
</script></head><body>
<h1>注文フォーム</h1>
<form method="post" action="/farm/order">
  <label>お名前 *</label>
  <input name="name" required placeholder="三井 太郎">

  <label>SNSハンドル</label>
  <input name="sns_handle" placeholder="@taro_miwa">

  <label>LINE ID（任意）</label>
  <input name="line_user_id" placeholder="Uxxxxxxxxxxxx">

  <label>販売形態 *</label>
  <select id="order_type" name="order_type" onchange="togglePlan()">
    <option value="spot">スポット（1回）</option>
    <option value="subscription">サブスク（定期）</option>
  </select>

  <div id="planSection" class="hidden">
    <label>プラン</label>
    <select name="plan">
      <option value="weekly_small">週1回・小サイズ（2,000円）</option>
      <option value="weekly_medium">週1回・中サイズ（3,500円）</option>
      <option value="weekly_large">週1回・大サイズ（5,000円）</option>
    </select>
  </div>

  <br>
  <button type="submit" class="btn">注文する</button>
</form>
<p><a href="/farm">&larr; ホームに戻る</a></p>
</body></html>"""


def order_success(order_id: int) -> str:
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><title>注文完了 — 淡路ベジ便</title>
<style>{_css()}</style></head><body>
<h1>仮受注を受け付けました</h1>
<p class="success">受付番号: <strong>#{order_id}</strong></p>
<div class="card">
  <p>内容が確定次第、お知らせします。<br>
  お手数ですが、<a href="/farm/order/{order_id}">注文状況ページ</a>で確認してください。</p>
</div>
<p><a href="/farm">&larr; ホームに戻る</a></p>
</body></html>"""


def order_status(order: dict, vegset: dict | None) -> str:
    status_class = f"status-{order['status']}" if order.get('status') else ''
    items_html = ""
    if vegset and vegset.get("items_json"):
        items_html = "<table><tr><th>野菜</th><th>数量</th><th>単位</th></tr>"
        for item in vegset["items_json"]:
            items_html += f"<tr><td>{item['veg']}</td><td>{item['qty']}</td><td>{item.get('unit', '個')}</td></tr>"
        items_html += "</table>"

    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><title>注文状況 #{order['id']} — 淡路ベジ便</title>
<style>{_css()}</style></head><body>
<h1>注文状況 #<span id="orderId">{order['id']}</span></h1>
<p><span class="status {status_class}">{order['status']}</span></p>
<div class="card">
  <p><strong>販売形態:</strong> {order['order_type']} {f'({order.get("plan", "")})' if order.get('plan') else ''}</p>
  <p><strong>金額:</strong> {order.get('amount', '未定')}円</p>
</div>

{f'<div class="card"><h2>野菜セット内容</h2>{items_html}</div>' if vegset else '<div class="card"><p>セット内容はまだ確定していません。</p></div>'}

{f'<form method="post" action="/farm/order/{order["id"]}/confirm"><button type="submit" class="btn">この内容で確定する</button></form>' if order['status'] == 'set_composed' else ''}
{f'<form method="post" action="/farm/order/{order["id"]}/pay"><button type="submit" class="btn">決済に進む</button></form>' if order['status'] == 'confirmed' else ''}

<p><a href="/farm">&larr; ホームに戻る</a> | <a href="/farm/admin/orders">管理一覧</a></p>
</body></html>"""


def admin_orders(orders: list[dict]) -> str:
    rows = ""
    for o in orders:
        status_class = f"status-{o['status']}" if o.get('status') else ''
        rows += f"<tr><td>{o['id']}</td><td>{o.get('customer_id', '')}</td><td>{o['order_type']}</td>"
        rows += f"<td><span class='status {status_class}'>{o['status']}</span></td>"
        rows += f"<td>{o.get('amount', 0)}円</td><td>{o.get('stripe_session_id', '')}</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><title>管理 — 注文一覧 — 淡路ベジ便</title>
<style>{_css()}</style></head><body>
<h1>注文一覧（管理コンソール）</h1>
<p><a href="/farm">&larr; ホームに戻る</a></p>
<table>
<tr><th>ID</th><th>顧客ID</th><th>形態</th><th>ステータス</th><th>金額</th><th>Stripe</th></tr>
{rows if rows else '<tr><td colspan="6">注文なし</td></tr>'}
</table>
</body></html>"""


def admin_trigger_recurring() -> str:
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><title>定期ジョブ — 淡路ベジ便</title>
<style>{_css()}</style></head><body>
<h1>定期注文生成ジョブ</h1>
<p><a href="/farm/admin/orders">&larr; 注文一覧に戻る</a></p>
<form method="post" action="/farm/admin/trigger-recurring">
  <button type="submit" class="btn">手動で定期注文を生成する</button>
</form>
</body></html>"""


def recurring_result(orders: list[int]) -> str:
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><title>定期ジョブ結果 — 淡路ベジ便</title>
<style>{_css()}</style></head><body>
<h1>定期注文生成結果</h1>
<p class="success">生成した注文: {orders}</p>
<p><a href="/farm/admin/trigger-recurring">&larr; ジョブ画面に戻る</a></p>
</body></html>"""
