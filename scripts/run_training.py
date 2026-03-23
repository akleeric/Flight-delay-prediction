import sys
import os
import logging

logging.basicConfig(level=logging.INFO)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.ml.training import train_model

if __name__ == "__main__":
    train_model()
