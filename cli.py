""# cli.py

import os
import json
from core.announcer import (
    send_otp,
    get_token,
    verify_token,
    get_purchased_batches,
    get_announcements
)
from dotenv import load_dotenv

ENV_PATH = "data/.env"

# Ensure data folder exists
os.makedirs("data", exist_ok=True)

if not os.path.exists(ENV_PATH):
    with open(ENV_PATH, "w") as f:
        f.write("TOKEN=\n")
        
# Load token from .env
load_dotenv(dotenv_path=ENV_PATH)
TOKEN = os.getenv("TOKEN")

def save_token_to_env(token: str):
    from dotenv import set_key
    set_key(ENV_PATH, "TOKEN", token)
    print("[INFO] Token saved to .env successfully.")

def load_seen_ids(batch_slug):
    path = f"data/announcements_{batch_slug}.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    return set(a["announcement"] for a in data)  # legacy format
                return set(data.get("seen_ids", []))
            except json.JSONDecodeError:
                return set()
    return set()

def save_seen_ids(batch_slug: str, seen_ids: set):
    path = f"data/announcements_{batch_slug}.json"
    with open(path, "w") as f:
        json.dump({"seen_ids": list(seen_ids)}, f, indent=2)
    print(f"[DEBUG] Saved {len(seen_ids)} seen announcement IDs.")

def prompt_user_input():
    phone = input("Enter phone number: ").strip()
    code = input("Enter country code (e.g. +91): ").strip()
    success, msg = send_otp(phone, code)
    if not success:
        print(f"[ERROR] {msg['message']}")
        return None, None, None
    print("[INFO] OTP sent successfully.")
    otp = input("Enter OTP: ").strip()
    return phone, code, otp

def prompt_for_token():
    print("[INFO] Please ensure your token is pasted in 'data/.env' as TOKEN=<your_token> before continuing.")
    input("Press Enter after updating the .env file...")
    load_dotenv(dotenv_path=ENV_PATH)
    token = os.getenv("TOKEN")
    if not token:
        print("[ERROR] TOKEN not found in .env file. Aborting.")
        return False
    return True

def select_batch(batches):
    print("\n[INFO] Available Batches:")
    for idx, batch in enumerate(batches):
        print(f"{idx + 1}. {batch['name']} (slug: {batch['slug']})")
    while True:
        try:
            index = int(input("\nSelect a batch number: ")) - 1
            if 0 <= index < len(batches):
                return batches[index]
            else:
                print("[ERROR] Invalid batch selection.")
        except ValueError:
            print("[ERROR] Please enter a valid number.")

def show_announcements(announcements, label="All"):
    if not announcements:
        print("[INFO] No announcements to show.")
        return

    print(f"\n[INFO] Displaying {label} announcements:\n")
    for ann in announcements:
        print(f"- {ann['announcement']}")
        if att := ann.get("attachment"):
            print(f"  [Attachment] {att['baseUrl']}{att['key']}")
        print()

def main():
    print("=== PW Announcer CLI ===")

    load_dotenv(dotenv_path=ENV_PATH)
    token = os.getenv("TOKEN")

    if token:
        is_valid, msg = verify_token()
        if is_valid:
            print("[INFO] Token verified successfully.")
        else:
            print("[WARNING] Existing token is invalid or expired.")
            print("\n[INFO] Select authentication mode:")
            print("1. Use phone number and OTP")
            print("2. Update token manually in .env")
            mode = input("Enter 1 or 2: ").strip()

            if mode == "1":
                phone, code, otp = prompt_user_input()
                if not all([phone, code, otp]):
                    return

                success, result = get_token(phone, otp)
                if not success:
                    print(f"[ERROR] {result['message']}")
                    return

                save_token_to_env(result["access_token"])

            elif mode == "2":
                if not prompt_for_token():
                    return
                is_valid, msg = verify_token()
                if not is_valid:
                    print(f"[ERROR] Token Verification Failed: {msg['message']}")
                    return
                print("[INFO] Token verified successfully.")
            else:
                print("[ERROR] Invalid selection.")
                return
    else:
        print("\n[INFO] Select authentication mode:")
        print("1. Use phone number and OTP")
        print("2. Paste token manually in .env")
        mode = input("Enter 1 or 2: ").strip()

        if mode == "1":
            phone, code, otp = prompt_user_input()
            if not all([phone, code, otp]):
                return

            success, result = get_token(phone, otp)
            if not success:
                print(f"[ERROR] {result['message']}")
                return

            save_token_to_env(result["access_token"])

        elif mode == "2":
            if not prompt_for_token():
                return
            is_valid, msg = verify_token()
            if not is_valid:
                print(f"[ERROR] Token Verification Failed: {msg['message']}")
                return
            print("[INFO] Token verified successfully.")
        else:
            print("[ERROR] Invalid selection.")
            return

    batches = get_purchased_batches()
    if isinstance(batches, dict) and "message" in batches:
        print(f"[ERROR] {batches['message']}")
        return

    selected_batch = select_batch(batches)
    batch_id = selected_batch["id"]
    batch_slug = selected_batch["slug"]

    print(f"[INFO] Fetching announcements for batch: {selected_batch['name']}")
    seen_ids = load_seen_ids(batch_slug)
    announcements = get_announcements(batch_id)

    if isinstance(announcements, dict) and "message" in announcements:
        print(f"[ERROR] {announcements['message']}")
        return

    fresh = [a for a in announcements if a['announcement'] not in seen_ids]
    all_ann_ids = seen_ids.union(a['announcement'] for a in announcements)
    save_seen_ids(batch_slug, all_ann_ids)

    while True:
        print("\n[INFO] What do you want to see?")
        print("1. All announcements")
        print("2. Only fresh announcements")
        print("3. Latest (most recent) announcement")
        print("4. Exit")

        choice = input("Enter 1, 2, 3 or 4: ").strip()
        if choice == "1":
            show_announcements(announcements, label="All")
        elif choice == "2":
            show_announcements(fresh, label="Fresh")
        elif choice == "3":
            if announcements:
                show_announcements([announcements[0]], label="Latest")
            else:
                print("[INFO] No announcements available.")
        elif choice == "4":
            print("[INFO] Exiting CLI.")
            break
        else:
            print("[ERROR] Invalid choice. Please enter 1, 2, 3 or 4.")

if __name__ == "__main__":
    main()
