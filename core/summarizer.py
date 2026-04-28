import ollama

def summarize_text(text, model="gemma3:4b", template_prompt=None):
    if not text.strip():
        return "Нет текста для итогов."
    if template_prompt is None:
        template_prompt = (
            "Ты — AI-ассистент. Сделай краткое структурированное саммари на русском языке.\n"
            "Выдели: 1. Основные темы  2. Ключевые идеи  3. Главные выводы\n\n"
            f"Текст:\n{text}"
        )
    else:
        # Подставляем текст в шаблон
        if "{text}" in template_prompt:
            template_prompt = template_prompt.replace("{text}", text)
        else:
            template_prompt = template_prompt + "\n\nТекст:\n" + text
    response = ollama.chat(model=model, messages=[{"role": "user", "content": template_prompt}])
    return response["message"]["content"]

def is_ollama_model_available(model_name):
    """Проверяет, установлена ли модель ollama и доступен ли сервер."""
    try:
        models = ollama.list()['models']
        return any(m['model'] == model_name for m in models)
    except Exception:
        return False