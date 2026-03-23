import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.collectors.historical_collector import HistoricalFlightCollector

if __name__ == "__main__":
    collector = HistoricalFlightCollector()
    collector.run()
    collector.close()
