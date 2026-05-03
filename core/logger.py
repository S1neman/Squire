import logging
import os
from core.paths import BASE_DIR

def setup_logger():
    log_dir = os.path.join(BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'squire.log')   # один файл

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Файловый обработчик (перезаписывает? лучше дописывать)
    fh = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Консольный обработчик (при желании)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    logger.info("=== Логирование инициализировано ===")
    return logger