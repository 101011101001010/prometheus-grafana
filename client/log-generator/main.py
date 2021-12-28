from datetime import datetime
import random
import time


def generate_logs():
    time_now = datetime.now()
    timestamp = time_now.strftime("%b %d %H:%M:%S %Y")
    success_roll = random.random()
    status = "Accept" if success_roll < 0.75 else "Reject"
    user = f"user{random.randint(1, 10)}"
    domain = f"domain{random.randint(1, 10)}.com"
    source = "127.0.0.1"
    destination = "127.0.0.1"
    mac_id = "ff-ff-ff-ff-ff-ff"
    reason = ""

    log = f"{timestamp}: Access-{status} for user {user}@{domain} stationid {mac_id} from {source}{reason} to {destination} ({destination})"

    with open("logs/log.log", "a+") as f:
        f.write(log + "\n")


if __name__ == "__main__":
    while True:
        generate_logs()
        wait = random.randint(10, 10)
        print(f"Waiting {wait} seconds...")
        time.sleep(wait)
