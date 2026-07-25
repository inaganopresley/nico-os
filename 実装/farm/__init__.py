"""farm — 淡路ベジ便 農産物販売モジュール（NICO-OS内）。
A=受注/顧客/決済（ゆうき）, B=供給/農家/出荷/管理（コバケン）。境界=01_インターフェース契約.md。

所有権:
  farm_customers    → A が書き込み
  farm_subscriptions→ A が書き込み
  farm_orders       → 共有（A: provisional/customer_confirm→confirmed/paid, B: set_requested/set_composed/shipped）
  farm_vegsets      → B が書き込み（A は読むだけ）
"""
