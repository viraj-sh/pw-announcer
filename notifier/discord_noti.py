import requests
import random
from datetime import datetime

def get_random_color():
    """Returns a random integer in the Discord embed color range."""
    return random.randint(0, 0xFFFFFF)


def send_discord_announcement(webhook_url, announcement):
    """
    Sends a single announcement to Discord via webhook, formatted with PW team profile and time at the top.
    """
    # Announcement text
    description = announcement.get("announcement", "New Announcement")

    # Format notification time
    try:
        dt = datetime.fromisoformat(announcement.get("scheduleTime", "")[:-1])
        notification_time = dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        notification_time = announcement.get("scheduleTime", "")

    # Image (if any)
    image_url = None
    attachment = announcement.get("attachment")
    if attachment and attachment.get("baseUrl") and attachment.get("key"):
        image_url = attachment["baseUrl"].rstrip("/") + "/" + attachment["key"].lstrip("/")

    # Build the embed
    embed = {
        "author": {
            "name": "PW team",
            "icon_url": "https://www.pw.live/study/assets/icons/logo.png"
        },
        "description": description,
         "color": get_random_color(),
        "fields": [
            {
                "name": "Notification Time",
                "value": notification_time,
                "inline": False
            }
        ]
    }
    if image_url:
        embed["image"] = {"url": image_url}

    payload = {
        "embeds": [embed]
    }

    response = requests.post(webhook_url, json=payload)
    return response.ok

def send_discord_announcements(webhook_url, announcements):
    """
    Sends multiple announcements one by one to Discord in chronological order (oldest first).
    """
    results = []
    for announcement in sorted(announcements, key=lambda x: x.get("scheduleTime", "")):
        result = send_discord_announcement(webhook_url, announcement)
        results.append(result)
    return results
