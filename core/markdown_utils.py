import markdown
import re

def markdown_to_plain(text: str) -> str:
    """Преобразует Markdown в обычный текст (без видимой разметки)."""
    if not text:
        return ""
    # Удаляем заголовки
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # Жирный **text** -> text
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    # Курсив *text* -> text
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    # Маркеры списков -> •
    text = re.sub(r'^[-\*+]\s+', '• ', text, flags=re.MULTILINE)
    # Ссылки [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Изображения ![alt](url) -> alt
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
    # Код `code` -> code
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Горизонтальные линии
    text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)
    # Сжимаем пустые строки
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

def markdown_to_html(text: str) -> str:
    if not text:
        return ""
    return markdown.markdown(text, extensions=['extra', 'nl2br'])