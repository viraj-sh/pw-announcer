# announcer.py

import os
import requests
from typing import Tuple, Union, List, Dict
from dotenv import load_dotenv
import json

# Constants
ORG_ID = "5eb393ee95fab7468a79d189"
BASE_URL = "https://api.penpencil.co"
DOTENV_PATH = "data/.env"

COMMON_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Referer": "https://www.pw.live/",
    "Randomid": "a997919f-4400-4416-a447-fe172d4d9be4"
}

def _load_token() -> str:
    load_dotenv(dotenv_path=DOTENV_PATH)
    token = os.getenv("TOKEN")
    if not token:
        raise ValueError("Access token not found in .env")
    return token

def _get_auth_headers() -> dict:
    headers = COMMON_HEADERS.copy()
    headers["Authorization"] = f"Bearer {_load_token()}"
    return headers

def send_otp(username: str, country_code: str) -> Tuple[bool, Union[str, dict]]:
    url = f"{BASE_URL}/v1/users/get-otp?smsType=0"
    body = {
        "username": username,
        "countryCode": country_code,
        "organizationId": ORG_ID
    }
    try:
        response = requests.post(url, json=body, headers=COMMON_HEADERS)
        data = response.json()
        if data.get("success"):
            return True, "OTP sent successfully."
        return False, {
            "message": data.get("error", {}).get("message", "Unknown error."),
            "status": data.get("error", {}).get("status", 400)
        }
    except Exception as e:
        return False, {"message": str(e), "status": 500}

def get_token(username: str, otp: str) -> Tuple[bool, dict]:
    url = f"{BASE_URL}/v3/oauth/token"
    body = {
        "username": username,
        "otp": otp,
        "client_id": "system-admin",
        "client_secret": "KjPXuAVfC5xbmgreETNMaL7z",
        "grant_type": "password",
        "latitude": 0,
        "longitude": 0,
        "organizationId": ORG_ID
    }
    try:
        response = requests.post(url, json=body)
        data = response.json()
        if data.get("success"):
            return True, {
                "access_token": data["data"]["access_token"],
                "expires_in": data["data"]["expires_in"]
            }
        return False, {
            "message": data.get("error", {}).get("message", "Invalid OTP or Username."),
            "status": data.get("error", {}).get("status", 412)
        }
    except Exception as e:
        return False, {"message": str(e), "status": 500}

def verify_token() -> Tuple[bool, Union[str, dict]]:
    url = f"{BASE_URL}/v3/oauth/verify-token"
    try:
        response = requests.post(url, headers=_get_auth_headers())
        data = response.json()
        if data.get("success") and data.get("data", {}).get("isVerified"):
            return True, "Token is valid."
        return False, {
            "message": data.get("error", {}).get("message", "Unauthorized Access"),
            "status": data.get("error", {}).get("status", 401)
        }
    except Exception as e:
        return False, {"message": str(e), "status": 500}

def _save_to_json(name: str, data: list):
    os.makedirs("data", exist_ok=True)
    with open(f"data/{name}.json", "w") as f:
        json.dump(data, f, indent=2)

def get_purchased_batches() -> Union[List[dict], dict]:
    is_verified, msg = verify_token()
    if not is_verified:
        return {"message": "Token is invalid or expired. Please reverify or regenerate it."}

    url = f"{BASE_URL}/batch-service/v1/batches/purchased-batches?amount=paid&page=1&type=ALL"
    try:
        response = requests.get(url, headers=_get_auth_headers())
        data = response.json()
        if not response.ok or not data.get("success"):
            return {"message": "Failed to fetch purchased batches."}
        
        batches = [{
            "id": batch["_id"],
            "name": batch["name"],
            "slug": batch["slug"]
        } for batch in data["data"]]

        _save_to_json("batches", batches)
        return batches
    except Exception as e:
        return {"message": str(e)}

def get_announcements(batch_id: str) -> Union[List[dict], dict]:
    url = f"{BASE_URL}/v1/batches/{batch_id}/announcement?page=1"
    try:
        response = requests.get(url, headers=_get_auth_headers())
        data = response.json()
        if not data.get("success"):
            return {"message": "Failed to fetch announcements."}
        return data["data"]
    except Exception as e:
        return {"message": str(e)}
