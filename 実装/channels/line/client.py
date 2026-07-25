"""channels.line.client — LINE push 送信。
FASTAPI アプリ外から呼ぶことも想定し、モジュール関数として公開する。"""

import os

_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")


def push(user_id: str, text: str) -> dict:
    """LINE ユーザーにメッセージを push する（テスト時は stdout に出力）。"""
    if not _CHANNEL_ACCESS_TOKEN:
        print(f"[LINE stub] push to {user_id}: {text}")
        return {"status": "stubbed"}
    # Actual LINE API call would go here.
    import requests
    resp = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {_CHANNEL_ACCESS_TOKEN}"},
        json={"to": user_id, "messages": [{"type": "text", "text": text}]},
    )
    return resp.json()


def push_messages(user_id: str, messages: list) -> dict:
    """複数メッセージを push。"""
    if not _CHANNEL_ACCESS_TOKEN:
        print(f"[LINE stub] push_messages to {user_id}: {messages}")
        return {"status": "stubbed"}
    import requests
    resp = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {_CHANNEL_ACCESS_TOKEN}"},
        json={"to": user_id, "messages": messages},
    )
    return resp.json()
