import os
import sys
import numpy as np
import re

if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ffmpeg_dir = base_dir
ffmpeg_exe = os.path.join(ffmpeg_dir, 'ffmpeg.exe')
if os.path.exists(ffmpeg_exe):
    os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')

from faster_whisper import WhisperModel

class Transcriber:
    def __init__(self, model_name="small", device="cpu"):
        self.model = WhisperModel(model_name, device=device, compute_type="float32")

    def _filter_hallucinations(self, text: str) -> str:
        if not text or len(text.strip()) < 5:
            return ""

        # Cтоп-слова
        hallucinations = [
            # ru
            "субтитры", "редактор", "спасибо за внимание", "пожалуйста", "подпишитесь",
            "лайк", "колокольчик", "видео", "канал", "нажмите", "перейдите", "поддержите",
            "пожертвовать", "оцените", "комментарии", "смех", "шум", "тишина", "спасибо",
            "здравствуйте", "до свидания", "привет", "пока", "алло", "да", "нет",
            # eng
            "subtitles", "editor", "thank you", "please", "subscribe", "like", "bell", "video", "channel",
            "click", "go to", "support", "donate", "rate", "comments", "music", "applause", "noise",
            "hello", "hi", "goodbye", "bye", "um", "uh", "so", "and", "like and subscribe",
            "testing", "test", "one two three", "check", "hello hello", "testing testing"
        ]

        text_lower = text.lower().strip()

        words = re.findall(r'\b\w+\b', text_lower)
        if words:
            all_stop = all(any(h in word for h in hallucinations) for word in words)
            if all_stop:
                return ""

        # Проверка на повторяющиеся паттерны
        if len(words) >= 2:
            first_word = words[0]
            if all(word == first_word for word in words):
                return ""

        for h in hallucinations:
            if h in text_lower:
                return ""

        if re.fullmatch(r'[\s\d\W]+', text):
            return ""

        return text

    def transcribe_chunk(self, audio_chunk, language="ru"):
        if audio_chunk is None or len(audio_chunk) == 0:
            return ""
        max_val = np.max(np.abs(audio_chunk))
        if max_val > 0:
            audio_chunk = audio_chunk / max_val
        segments, _ = self.model.transcribe(audio_chunk, language=language, beam_size=3)
        raw_text = " ".join([seg.text for seg in segments]).strip()
        return self._filter_hallucinations(raw_text)

    def transcribe_full(self, audio, language="ru"):
        if audio is None or len(audio) == 0:
            return ""
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val
        segments, _ = self.model.transcribe(audio, language=language, beam_size=5)
        return " ".join([seg.text for seg in segments])