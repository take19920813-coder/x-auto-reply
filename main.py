import os
import time
import requests

BEARER_TOKEN = os.environ["X_BEARER_TOKEN"]
TARGET_USER = "hirox246"

headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}"
}

def check_posts():
    print(f"Checking posts from @{TARGET_USER}...")

while True:
    try:
        check_posts()
        time.sleep(60)
    except Exception as e:
        print("Error:", e)
        time.sleep(60)
