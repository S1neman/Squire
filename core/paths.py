import os
import sys

def get_base_dir():
    """Базовая директория для хранения пользовательских данных (config, data, templates)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_resource_dir():
    """Директория, где находятся ресурсы (иконки, темы) внутри .exe"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = get_base_dir()
RESOURCE_DIR = get_resource_dir()
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
DATA_DIR = os.path.join(BASE_DIR, 'data')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
TRANSCRIPTS_DIR = os.path.join(DATA_DIR, 'transcripts')
SUMMARIES_DIR = os.path.join(DATA_DIR, 'summaries')