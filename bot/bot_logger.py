import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOG_DIR = "/logs"
LOG_FILE = "bots.log"
LOG_PATH = os.path.join(LOG_DIR, LOG_FILE)

os.makedirs(LOG_DIR, exist_ok=True)

# Создаём логгер
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Формат сообщений
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
)

# Обработчик для файла (ротация по размеру до 5 файлов по 1MB)
file_handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=5)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 👇 Обработчик для консоли (stdout)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
