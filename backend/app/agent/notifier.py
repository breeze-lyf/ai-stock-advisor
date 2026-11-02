"""Pluggable push channels for agent briefs: DingTalk custom robot, generic webhook, Telegram (optional)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
import urllib.parse
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

KINDS = ("dingtalk", "webhook", "telegram")


def dingtalk_signed_url(url: str, secret: Optional[str], ts_ms: Optional[int] = None) -> str:
    """DingTalk 自定义机器人「加签」: sign = urlencode(base64(hmac_sha256(secret, f"{ts}\\n{secret}")))."""
    if not secret:
        return url
    ts = str(ts_ms or int(time.time() * 1000))
    digest = hmac.new(secret.encode(), f"{ts}\n{secret}".encode(), hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(digest).decode())
    return f"{url}{'&' if '?' in url else '?'}timestamp={ts}&sign={sign}"


def build_request(kind: str, url: str, secret: Optional[str], title: str, markdown: str) -> tuple[str, dict]:
    if kind == "dingtalk":
        # DingTalk markdown max ~20k chars; keyword-type robots need the keyword in text — title includes 简报
        return dingtalk_signed_url(url, secret), {"msgtype": "markdown", "markdown": {"title": title, "text": f"## {title}\n\n{markdown[:18000]}"}}
    if kind == "telegram":
        # url = chat_id, secret = bot token
        return f"https://api.telegram.org/bot{secret}/sendMessage", {"chat_id": url, "text": f"{title}\n\n{markdown[:3800]}"}
    return url, {"title": title, "text": markdown, "source": "ai-stock-advisor", "type": "daily_brief"}


def validate(kind: str, url: str, secret: Optional[str]) -> Optional[str]:
    if kind not in KINDS:
        return "不支持的推送类型"
    if kind == "telegram":
        return None if (url and secret) else "Telegram 需要 chat_id 与 bot token"
    if not url.startswith("https://"):
        return "Webhook 地址必须以 https:// 开头"
    if kind == "dingtalk" and "oapi.dingtalk.com/robot/send" not in url:
        return "钉钉机器人地址应为 https://oapi.dingtalk.com/robot/send?access_token=..."
    return None


async def send(kind: str, url: str, secret: Optional[str], title: str, markdown: str, client: Optional[httpx.AsyncClient] = None) -> tuple[bool, str]:
    target, payload = build_request(kind, url, secret, title, markdown)
    try:
        if client is None:
            async with httpx.AsyncClient(timeout=15) as c:
                resp = await c.post(target, json=payload)
        else:
            resp = await client.post(target, json=payload)
    except httpx.HTTPError as e:
        return False, f"网络错误 {e.__class__.__name__}"
    if resp.status_code >= 400:
        return False, f"HTTP {resp.status_code}"
    if kind == "dingtalk":
        try:
            body = resp.json()
            if body.get("errcode", 0) != 0:
                return False, f"钉钉返回 {body.get('errcode')}: {str(body.get('errmsg'))[:80]}"
        except Exception:
            pass
    return True, "ok"
