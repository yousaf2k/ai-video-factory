import requests
import time
import config

def wait_until_idle():

    while True:
        r = requests.get(f"{config.COMFY_URL}/queue")
        q = r.json()

        if q["queue_running"] == []:
            break

        time.sleep(2)