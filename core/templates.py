import json
import os
import time
from core.paths import TEMPLATES_DIR

DEFAULT_TEMPLATE = {
    "name": "Стандартный",
    "prompt": "Ты — AI-ассистент. Сделай структурированные итоги на русском языке.\nВыдели в параграфы с нумерацией: 1. Основные темы  2. Ключевые идеи и планы  3. Главные выводы и приоритеты.\nТекст:\n{text}"
}

def get_default_template():
    return DEFAULT_TEMPLATE.copy()

def load_templates():
    """Загружает все шаблоны из папки templates/ в виде списка словарей"""
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    templates = []
    for fname in os.listdir(TEMPLATES_DIR):
        if fname.endswith('.json'):
            with open(os.path.join(TEMPLATES_DIR, fname), 'r', encoding='utf-8') as f:
                templates.append(json.load(f))
    if not templates:
        # Сохраняем стандартный шаблон, если нет ни одного
        save_template(get_default_template())
        return [get_default_template()]
    return templates

def save_template(template):
    """Сохраняет шаблон в файл (если нет имени, генерирует)"""
    name = template.get('name', 'Без названия')
    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
    if not safe_name:
        safe_name = "template"
    counter = 1
    base_path = os.path.join(TEMPLATES_DIR, safe_name)
    path = base_path + ".json"
    while os.path.exists(path):
        path = f"{base_path}_{counter}.json"
        counter += 1
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    return path

def delete_template(template_name):
    for fname in os.listdir(TEMPLATES_DIR):
        if fname.endswith('.json'):
            path = os.path.join(TEMPLATES_DIR, fname)
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('name') == template_name:
                    for attempt in range(5):
                        try:
                            os.remove(path)
                            return True
                        except PermissionError:
                            time.sleep(0.2)
                    return False
    return False

def update_template(old_name, new_template):
    """Заменяет шаблон с именем old_name на новый"""
    for fname in os.listdir(TEMPLATES_DIR):
        if fname.endswith('.json'):
            path = os.path.join(TEMPLATES_DIR, fname)
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('name') == old_name:
                    with open(path, 'w', encoding='utf-8') as f2:
                        json.dump(new_template, f2, ensure_ascii=False, indent=2)
                    return True
    return False