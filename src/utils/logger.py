import logging
import sys
from pathlib import Path

def setup_logger(name: str, log_file: str = None, level: str = 'INFO'):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    log_level = getattr(logging, level.upper())
    logger.setLevel(log_level)
    fmt = '%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s'
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(console_handler)
    if log_file:
        Path('logs').mkdir(exist_ok=True)
        file_handler = logging.FileHandler(f'logs/{log_file}')
        file_handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(file_handler)
    logger.propagate = False
    return logger

def get_logger(name: str):
    return setup_logger(name)
