import os
import json
import time
import logging

from core.announcer import fetch_batches, fetch_announcements
from core.tracker import (
    load_known_ids,
    save_known_ids,
    get_new_announcements,
    update_known_ids,
    
)
from notifier.discord_noti import send_discord_announcements

CONFIG_FILE = "config.json"
TEMPLATE_CONFIG = {
    "webhook_url": "YOUR_DISCORD_WEBHOOK",
    "token": "YOUR_ACCESS_TOKEN_HERE",
    "ids_file": "known_announcement_ids.json",
    "frequency_minutes": 30,
    "paused": False,
    "selected_batch_ids": [],  # Will be filled during selection
    "interactive_token_renewal": False
}

def ensure_config():
    if not os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(TEMPLATE_CONFIG, f, indent=2)
        print(
            f"\nconfig.json was not found, so a template has been created at {CONFIG_FILE}.\n"
            f"Please open it, fill in your Discord webhook URL and access token before running this script again.\n"
            f"Exiting now. Run again after updating config.json!\n"
        )
        exit(1)

def load_config():
    ensure_config()
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def log_setup():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler("announcer.log"),
            logging.StreamHandler()
        ]
    )

def select_batches(token, cfg):
    """
    Let user select which PW batches to track.
    """
    print("\nFetching your PW batches...")
    batches_resp = fetch_batches(token)
    if not batches_resp.get("success"):
        print(f"Could not fetch batches for selection: {batches_resp.get('error_message')}")
        exit(1)
    batches = batches_resp.get("batches", [])
    if not batches:
        print("No purchased batches available. Exiting.")
        exit(1)
    # Show all batches for selection
    print("\nYour Purchased Batches:")
    for idx, batch in enumerate(batches, 1):
        print(f"{idx}. {batch['name']} | ID: {batch['_id']}")
    print("\nEnter comma-separated numbers of batches you want to track (e.g. 1,3): ")
    selection = input("> ").strip()
    # Parse user input to batch indices
    indices = set()
    for tok in selection.split(","):
        tok = tok.strip()
        if tok.isdigit():
            indices.add(int(tok)-1)
    selected_ids = [batches[i]["_id"] for i in indices if 0 <= i < len(batches)]
    if not selected_ids:
        print("No valid selection. Exiting.")
        exit(1)
    cfg["selected_batch_ids"] = selected_ids
    save_config(cfg)
    print(f"\nSaved batch IDs: {selected_ids} to config.json.\nRestart the script.")
    exit(0)

def main():
    log_setup()
    cfg = load_config()
    webhook_url = cfg["webhook_url"]
    ids_file = cfg["ids_file"]
    frequency = int(cfg.get("frequency_minutes", 30)) * 60
    paused = bool(cfg.get("paused", False))
    token = cfg["token"]

    if not webhook_url or not token or token.startswith("YOUR_"):
        logging.critical(
            "config.json is not set up. Please fill in your 'webhook_url' and 'token' with actual values."
        )
        exit(1)
    # Check for batch selection - if not done, do it now
    if not cfg.get("selected_batch_ids"):
        select_batches(token, cfg)
    selected_ids = set(cfg["selected_batch_ids"])

    # Load known announcement IDs
    known_ids = load_known_ids(ids_file)

    # FIRST, test token is *actually* accepted for fetching batches
    batches_resp = fetch_batches(token)
    if not batches_resp.get("success"):
        error = batches_resp.get("error_status")
        if error in [401, 403]:
            logging.critical("Your access token was rejected by fetch_batches. Update config.json with a fresh token.")
        else:
            logging.error(f"Failed to fetch batches: {batches_resp.get('error_message')}")
        exit(1)
    purchased_batches = batches_resp.get("batches", [])
    # Filter only the selected batches
    batches_to_track = [b for b in purchased_batches if b["_id"] in selected_ids]
    if not batches_to_track:
        logging.critical("No matching batches found for your selected IDs. Reselect with a valid token.")
        # Wipe selection so user is prompted again on restart
        cfg["selected_batch_ids"] = []
        save_config(cfg)
        exit(1)

    logging.info("Notifier started. Ctrl+C to stop.")
    while True:
        cfg = load_config()
        if cfg.get("paused", False):
            logging.info("Paused - sleeping...")
            time.sleep(frequency)
            continue

        logging.info("Checking new announcements from selected batches...")

        # If batches could change, re-fetch every round:
        batches_resp = fetch_batches(token)
        if not batches_resp.get("success"):
            logging.error(f"Fetching batches failed: {batches_resp.get('error_message')}")
            if batches_resp.get("error_status") in [401, 403]:
                logging.critical("Token invalid/expired. Update config.json with fresh token.")
                exit(1)
            time.sleep(frequency)
            continue
        purchased_batches = batches_resp.get("batches", [])
        batches_to_track = [b for b in purchased_batches if b["_id"] in selected_ids]
        if not batches_to_track:
            logging.critical("None of your selected batches are found. Re-select needed. Exiting.")
            cfg["selected_batch_ids"] = []
            save_config(cfg)
            exit(1)

        all_new = []
        for batch in batches_to_track:
            bid = batch["_id"]
            bslug = batch.get("slug") or batch["name"]
            ann_resp = fetch_announcements(token, bid)
            if not ann_resp.get("success"):
                logging.warning(f"Failed to fetch announcements for {bslug}: {ann_resp.get('error_message')}")
                continue
            fetched_anns = ann_resp.get("announcements", [])
            new_anns = get_new_announcements(fetched_anns, known_ids)
            if new_anns:
                for new_ann in new_anns:
                    new_ann['batch_slug'] = bslug
                all_new.extend(new_anns)

        if all_new:
            logging.info(f"{len(all_new)} new announcement(s) found. Sending to Discord, one at a time...")
            results = []
            for ann in sorted(all_new, key=lambda x: x.get("scheduleTime", "")):
                try:
                    ok = send_discord_announcements(webhook_url, [ann])[0]  # Should be True/False
                except Exception as e:
                    logging.error(f"Discord send failed: {e}")
                    ok = False
                if not ok:
                    logging.warning("A Discord send failed (bad webhook, network, or embed error).")
                time.sleep(1)  # ADDS A DELAY TO PREVENT RATE LIMIT
                results.append(ok)
            if all(results):
                logging.info("All new announcements sent to Discord.")
            else:
                failed_count = results.count(False)
                logging.warning(f"{failed_count} announcement(s) failed to send.")
            # update known IDs
            known_ids = update_known_ids(all_new, known_ids)
            save_known_ids(known_ids, ids_file)
        else:
            logging.info("No new announcements.")

        logging.info(f"Sleeping for {cfg['frequency_minutes']} minutes...\n")
        time.sleep(frequency)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
