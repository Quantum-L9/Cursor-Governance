import csv
import datetime
import os

SOURCE = "environment/n8n-env-variable-audit.csv"
TARGET = ".env"
LOG = "environment/logs/env_sync.log"


def load_env():
    os.makedirs("environment/logs", exist_ok=True)
    if not os.path.exists(SOURCE):
        raise FileNotFoundError(f"Source CSV not found: {SOURCE}")
    with open(SOURCE, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        env_lines = [f"{row['key']}={row['value']}" for row in reader]
    with open(TARGET, "w") as f:
        f.write("\n".join(env_lines))
    with open(LOG, "a") as log:
        log.write(f"[{datetime.datetime.utcnow()} UTC] Environment synced from {SOURCE}\n")


if __name__ == "__main__":
    load_env()
