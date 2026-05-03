import ollama

def _add_markdown_formatting(text: str) -> str:
    lines = text.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and '**' not in line:
            import re
            # Список ключевых слов, которые должны размечаться
            keywords = ['Проект', 'тема', 'Основные темы', 'Ключевые идеи', 'Выводы', 'решения', 'Открытые вопросы', 'гипотезы']
            if re.match(r'^\d+\.', stripped) or any(kw in stripped for kw in keywords):
                new_lines.append(line.replace(stripped, f'**{stripped}**', 1))
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    return '\n'.join(new_lines)

def summarize_text(text, model="gemma3:4b", template_prompt=None):
    if not text.strip():
        return "Нет текста для итогов."
    if template_prompt is None:
        template_prompt = (
            "Ты — AI-ассистент. Сделай краткое структурированное саммари на русском языке, строго следуя по шаблону и разметки в нём (учитывая звёздочки).\n"
            "Правила для генерации ответа: Не упоминай в итогах части изначального запроса в промпте. Отвечай сразу по сути.\n"
            "Шаблон:\n"
            "**#callreport**\n"
            "**1. Основные темы**\n"
            "• тема1\n"
            "• тема2\n"
            "**2. Ключевые идеи**\n"
            "• идея1\n"
            "• идея2\n"
            "**3. Главные выводы и решения**\n\n"
            "• вывод1\n"
            "• вывод2\n"
            "Текст обсуждения:\n{text}"
        )
    else:
        if "{text}" in template_prompt:
            template_prompt = template_prompt.replace("{text}", text)
        else:
            template_prompt = template_prompt + "\n\nТекст:\n" + text
    response = ollama.chat(model=model, messages=[{"role": "user", "content": template_prompt}])
    summary = response["message"]["content"]
    formatted_summary = _add_markdown_formatting(summary)
    return formatted_summary

def is_ollama_model_available(model_name):
    try:
        models = ollama.list()['models']
        return any(m['model'] == model_name for m in models)
    except Exception:
        return False