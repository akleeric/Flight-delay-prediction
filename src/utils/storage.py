import json
import os

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

def save_raw(name, data):
    """Écrase un fichier JSON brut dans data/raw/"""
    path = os.path.join(RAW_DIR, f"{name}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
    return path

def save_processed(name, data):
    """Écrase un fichier JSON transformé dans data/processed/"""
    path = os.path.join(PROCESSED_DIR, f"{name}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
    return path
