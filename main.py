import sys
import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
import customtkinter as ctk
from core.logger import setup_logger
logger = setup_logger()

sys.path.insert(0, os.path.dirname(__file__))

from core.paths import RESOURCE_DIR

# 1. Загрузка цветовой темы из ресурсов
theme_path = os.path.join(RESOURCE_DIR, "assets", "squire_theme.json")
if os.path.exists(theme_path):
    ctk.set_default_color_theme(theme_path)
else:
    print("Файл темы не найден, используется стандартная тема")

# 2. Загрузка шрифта Inter (переменный файл)
inter_font = os.path.join(RESOURCE_DIR, "assets", "fonts", "Inter-VariableFont_opsz,wght.ttf")
if os.path.exists(inter_font):
    ctk.FontManager.load_font(inter_font)
    print("Шрифт Inter загружен")
else:
    print("Файл шрифта Inter не найден, будет использован системный шрифт")

from ui.main_window import SquireApp
from core.history import ensure_dirs

if __name__ == "__main__":
    ensure_dirs()
    app = SquireApp()
    app.mainloop()