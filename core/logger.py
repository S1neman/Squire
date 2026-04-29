import logging
import os
import sys
from datetime import datetime
from core.paths import BASE_DIR
import platform

def setup_logger():
    log_dir = os.path.join(BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'squire_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

    # Корневой логгер
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Обработчик для файла (все уровни)
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Обработчик для консоли (INFO и выше)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    logger.info(f"OS: {platform.system()} {platform.release()}")
    logger.info(f"Python: {sys.version}")

    logger.info("=== Логирование инициализировано ===")
    return logger