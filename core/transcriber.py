import os
import sys
import numpy as np

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

    def transcribe_chunk(self, audio_chunk, language="ru"):
        if audio_chunk is None or len(audio_chunk) == 0:
            return ""
        max_val = np.max(np.abs(audio_chunk))
        if max_val > 0:
            audio_chunk = audio_chunk / max_val
        segments, _ = self.model.transcribe(audio_chunk, language=language, beam_size=3)
        return " ".join([seg.text for seg in segments])

    def transcribe_full(self, audio, language="ru"):
        if audio is None or len(audio) == 0:
            return ""
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val
        segments, _ = self.model.transcribe(audio, language=language, beam_size=5)
        return " ".join([seg.text for seg in segments])