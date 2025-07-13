# core/token.py

import requests
import uuid

# --- Constants (reused across functions) ---
BASE_URL = "https://api.penpencil.co"
ORGANIZATION_ID = "5eb393ee95fab7468a79d189"
REFERER = "https://www.pw.live/"
CONTENT_TYPE = "application/json"
ACCEPT = "application/json"
CLIENT_ID = "system-admin"
CLIENT_SECRET = "KjPXuAVfC5xbmgreETNMaL7z"
GRANT_TYPE = "password"
LATITUDE = 0
LONGITUDE = 0

def _get_default_headers(random_id=None):
    """
    Returns the default headers required for all API requests.
    """
    if not random_id:
        random_id = str(uuid.uuid4())
    return {
        "Content-Type": CONTENT_TYPE,
        "Accept": ACCEPT,
        "Referer": REFERER,
        "Randomid": random_id,
    }

def send_otp(phone: str, country_code: str, random_id=None):
    """
    Sends OTP to the given phone number and country code.
    Returns a dict: {'success': True} if sent, else {'success': False, 'error_message': str, 'error_status': int}
    """
    url = f"{BASE_URL}/v1/users/get-otp?smsType=0"
    headers = _get_default_headers(random_id)
    payload = {
        "username": phone,
        "countryCode": country_code,
        "organizationId": ORGANIZATION_ID
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        data = resp.json()
        if data.get("success"):
            return {"success": True}
        else:
            error = data.get("error", {})
            return {
                "success": False,
                "error_message": error.get("message", "Unknown error"),
                "error_status": error.get("status", resp.status_code)
            }
    except Exception as e:
        return {"success": False, "error_message": str(e), "error_status": None}

def get_token(phone: str, otp: str, random_id=None):
    """
    Exchanges phone and OTP for an access token.
    Returns a dict: {'success': True, 'access_token': str, 'expires_in': int}
    Or: {'success': False, 'error_message': str, 'error_status': int}
    """
    url = f"{BASE_URL}/v3/oauth/token"
    headers = _get_default_headers(random_id)
    payload = {
        "username": phone,
        "otp": otp,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": GRANT_TYPE,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "organizationId": ORGANIZATION_ID
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        data = resp.json()
        if data.get("success") and "data" in data:
            return {
                "success": True,
                "access_token": data["data"]["access_token"],
                "expires_in": data["data"]["expires_in"]
            }
        else:
            error = data.get("error", {})
            return {
                "success": False,
                "error_message": error.get("message", data.get("message", "Unknown error")),
                "error_status": error.get("status", resp.status_code)
            }
    except Exception as e:
        return {"success": False, "error_message": str(e), "error_status": None}


