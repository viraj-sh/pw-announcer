# notifier/telegram_noti.py

import requests
from datetime import datetime
import random

def format_announcement_message(announcement):
    """
    Formats the announcement for Telegram using Markdown.
    Shows PW Team as sender, notification time, and announcement text.
    """
    description = announcement.get("announcement", "New Announcement")

    # Format notification time
    try:
        dt = datetime.fromisoformat(announcement.get("scheduleTime", "")[:-1])
        notification_time = dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        notification_time = announcement.get("scheduleTime", "")

    # PW Team header with logo
    pw_logo = "https://www.pw.live/study/assets/icons/logo.png"
    header = f"<b>PW team</b>\nNotification time: <i>{notification_time}</i>\n"

    # Main message body
    message = f"{header}\n<b>{description}</b>"

    return message, pw_logo

def send_telegram_announcement(bot_token, chat_id, announcement):
    """
    Sends a single announcement to Telegram using sendPhoto (if image) or sendMessage.
    :param bot_token: Telegram bot token (string)
    :param chat_id: Telegram chat ID (int or string)
    :param announcement: dict with keys: 'announcement', 'scheduleTime', 'attachment' (dict or None)
    """
    message, pw_logo = format_announcement_message(announcement)

    # Prepare image URL if available
    image_url = None
    attachment = announcement.get("attachment")
    if attachment and attachment.get("baseUrl") and attachment.get("key"):
        image_url = attachment["baseUrl"].rstrip("/") + "/" + attachment["key"].lstrip("/")
    else:
        image_url = pw_logo  # Always show PW logo as image if no attachment

    # Telegram API endpoint
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

    # Use sendPhoto to show image and caption together (with HTML formatting)
    payload = {
        "chat_id": chat_id,
        "photo": image_url,
        "caption": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=payload)
    return response.ok

def send_telegram_announcements(bot_token, chat_id, announcements):
    """
    Sends multiple announcements one by one to Telegram in chronological order (oldest first).
    """
    results = []
    # Sort by scheduleTime so oldest is first, latest is last
    for announcement in sorted(announcements, key=lambda x: x.get("scheduleTime", "")):
        result = send_telegram_announcement(bot_token, chat_id, announcement)
        results.append(result)
    return results
