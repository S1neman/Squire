import sounddevice as sd
import numpy as np
import threading
import queue
from typing import Optional, List

class AudioCapture:
    def __init__(
        self,
        mic_id: int,
        sys_id: Optional[int],
        mode: str,
        mic_weight: float = 1.0,
        sys_weight: float = 3.0,
        sample_rate: int = 16000,
    ):
        self.mic_id = mic_id
        self.sys_id = sys_id
        self.mode = mode
        self.mic_weight = mic_weight
        self.sys_weight = sys_weight
        self.sample_rate = sample_rate
        self.is_recording = False

        # Безлимитные очереди
        self.mic_queue = queue.Queue()
        self.sys_queue = queue.Queue()

        self.full_mic: List[np.ndarray] = []
        self.full_system: List[np.ndarray] = []
        self.mic_thread: Optional[threading.Thread] = None
        self.sys_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.is_recording:
            return
        self.is_recording = True

        # Очищаем очереди от старых данных
        while not self.mic_queue.empty():
            try:
                self.mic_queue.get_nowait()
            except queue.Empty:
                break
        while not self.sys_queue.empty():
            try:
                self.sys_queue.get_nowait()
            except queue.Empty:
                break

        self.full_mic.clear()
        self.full_system.clear()

        if self.mode in ('mic', 'mix'):
            self.mic_thread = threading.Thread(
                target=self._record_device,
                args=(self.mic_id, self.mic_queue, self.full_mic, self.mic_weight, 'mic'),
                daemon=True,
            )
            self.mic_thread.start()

        if self.mode in ('system', 'mix') and self.sys_id is not None:
            self.sys_thread = threading.Thread(
                target=self._record_device,
                args=(self.sys_id, self.sys_queue, self.full_system, self.sys_weight, 'sys'),
                daemon=True,
            )
            self.sys_thread.start()

    def stop(self) -> None:
        self.is_recording = False
        if self.mic_thread and self.mic_thread.is_alive():
            self.mic_thread.join(timeout=2)
        if self.sys_thread and self.sys_thread.is_alive():
            self.sys_thread.join(timeout=2)

    def _record_device(
        self,
        device_id: int,
        out_queue: queue.Queue,
        full_list: List[np.ndarray],
        weight: float,
        name: str,
    ) -> None:
        try:
            channels = sd.query_devices(device_id)['max_input_channels']
            if channels > 2:
                channels = 2
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=channels,
                dtype='float32',
                device=device_id,
                callback=lambda indata, frames, time, status: self._callback(
                    indata, out_queue, full_list, weight, name, channels
                ),
            ):
                while self.is_recording:
                    sd.sleep(100)
        except Exception as e:
            print(f"Ошибка записи {name}: {e}")
            self.is_recording = False

    def _callback(
        self,
        indata: np.ndarray,
        out_queue: queue.Queue,
        full_list: List[np.ndarray],
        weight: float,
        name: str,
        channels: int,
    ) -> None:
        if channels == 1:
            chunk = indata.copy().flatten()
        else:
            chunk = np.mean(indata, axis=1).flatten()

        chunk = chunk * weight
        chunk = np.clip(chunk, -1.0, 1.0)

        out_queue.put(chunk)
        full_list.append(chunk)

    def get_next_block(self, block_duration: float = 2.0) -> Optional[np.ndarray]:
        mic_chunks = []
        sys_chunks = []

        while not self.mic_queue.empty():
            mic_chunks.append(self.mic_queue.get())
        while not self.sys_queue.empty():
            sys_chunks.append(self.sys_queue.get())

        if self.mode == 'mic':
            if not mic_chunks:
                return None
            return np.concatenate(mic_chunks)
        if self.mode == 'system':
            if not sys_chunks:
                return None
            return np.concatenate(sys_chunks)

        # mix
        if not mic_chunks or not sys_chunks:
            return None
        mic_block = np.concatenate(mic_chunks)
        sys_block = np.concatenate(sys_chunks)
        min_len = min(len(mic_block), len(sys_block))
        mic_block = mic_block[:min_len]
        sys_block = sys_block[:min_len]
        mixed = mic_block + sys_block
        max_val = np.max(np.abs(mixed))
        if max_val > 1.0:
            mixed = mixed / max_val
        return mixed

    def get_full_audio(self) -> Optional[np.ndarray]:
        if self.mode == 'mic':
            return np.concatenate(self.full_mic) if self.full_mic else None
        if self.mode == 'system':
            return np.concatenate(self.full_system) if self.full_system else None

        if not self.full_mic or not self.full_system:
            return None
        mic_full = np.concatenate(self.full_mic)
        sys_full = np.concatenate(self.full_system)
        min_len = min(len(mic_full), len(sys_full))
        mic_full = mic_full[:min_len]
        sys_full = sys_full[:min_len]
        mixed = mic_full + sys_full
        max_val = np.max(np.abs(mixed))
        if max_val > 0:
            mixed = mixed / max_val
        return mixed