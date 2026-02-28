import logging

import requests
from django.conf import settings

from .models import NotificationLog

logger = logging.getLogger(__name__)


def get_zoom_access_token() -> str | None:
    """Zoom Server-to-Server OAuth2 でアクセストークンを取得"""
    if not all([settings.ZOOM_ACCOUNT_ID, settings.ZOOM_CLIENT_ID, settings.ZOOM_CLIENT_SECRET]):
        logger.warning("Zoom API credentials not configured")
        return None

    try:
        resp = requests.post(
            "https://zoom.us/oauth/token",
            params={
                "grant_type": "account_credentials",
                "account_id": settings.ZOOM_ACCOUNT_ID,
            },
            auth=(settings.ZOOM_CLIENT_ID, settings.ZOOM_CLIENT_SECRET),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]
    except requests.RequestException:
        logger.exception("Failed to obtain Zoom access token")
        return None


def send_zoom_message(to_contact: str, message: str, trigger: str) -> NotificationLog:
    """Zoom Chat APIでメッセージを送信

    Args:
        to_contact: 送信先Zoomメールアドレス（店舗またはSVアカウント）
        message: 通知内容
        trigger: 通知トリガー種別

    Returns:
        NotificationLog record
    """
    log = NotificationLog(
        trigger=trigger,
        recipient_zoom_account=to_contact,
        message=message,
    )

    token = get_zoom_access_token()
    if not token:
        log.error_message = "Zoom access token取得失敗"
        log.save()
        return log

    try:
        resp = requests.post(
            "https://api.zoom.us/v2/chat/users/me/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "message": message,
                "to_contact": to_contact,
            },
            timeout=10,
        )
        resp.raise_for_status()
        log.is_sent = True
    except requests.RequestException as e:
        log.error_message = str(e)
        logger.exception("Failed to send Zoom message to %s", to_contact)

    log.save()
    return log


def notify_store(store, message: str, trigger: str) -> NotificationLog | None:
    """店舗のZoomアカウントに通知"""
    if not store.zoom_account:
        logger.warning("Store %s has no Zoom account configured", store.name)
        return None
    return send_zoom_message(store.zoom_account, message, trigger)
