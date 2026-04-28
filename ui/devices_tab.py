import customtkinter as ctk
import threading
import os
from core.devices import get_unique_input_devices
from core.transcriber import Transcriber
import sounddevice as sd
import numpy as np
import ollama
from huggingface_hub import snapshot_download

# Словари для отображения размера моделей
WHISPER_DISPLAY = {
    "tiny": "tiny (~75 MB)",
    "base": "base (~150 MB)",
    "small": "small (~500 MB)",
    "medium": "medium (~1.5 GB)",
    "large-v3": "large-v3 (~3 GB)"
}

OLLAMA_DISPLAY = {
    "gemma3:1b": "gemma3:1b (~1 GB)",
    "gemma3:4b": "gemma3:4b (~4 GB)",
    "qwen3.5:4b": "qwen3.5:4b (~4 GB)"
}

class DevicesTab(ctk.CTkFrame):
    def __init__(self, parent, settings, on_settings_change, on_status):
        super().__init__(parent)
        self.settings = settings
        self.on_settings_change = on_settings_change
        self.on_status = on_status
        self.create_widgets()
        self.refresh_device_lists()
        self.update_whisper_status()
        self.update_ollama_status()

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill='both', expand=True, padx=30, pady=20)

        # ----- Микрофон -----
        ctk.CTkLabel(main_frame, text="Микрофон:", font=('Inter', 14)).grid(row=0, column=0, padx=10, pady=10, sticky='w')
        self.mic_combo = ctk.CTkOptionMenu(main_frame, values=[], width=350, font=('Inter', 13))
        self.mic_combo.grid(row=0, column=1, padx=10, pady=10)
        self.test_mic_btn = ctk.CTkButton(main_frame, text="Тест", command=self.test_mic, width=100, font=('Inter', 13))
        self.test_mic_btn.grid(row=0, column=2, padx=10, pady=10)

        # ----- Системный звук -----
        ctk.CTkLabel(main_frame, text="Звук (системный):", font=('Inter', 14)).grid(row=1, column=0, padx=10, pady=10, sticky='w')
        self.sys_combo = ctk.CTkOptionMenu(main_frame, values=[], width=350, font=('Inter', 13))
        self.sys_combo.grid(row=1, column=1, padx=10, pady=10)
        self.test_sys_btn = ctk.CTkButton(main_frame, text="Тест", command=self.test_sys, width=100, font=('Inter', 13))
        self.test_sys_btn.grid(row=1, column=2, padx=10, pady=10)

        # Вес микрофона (слайдер)
        ctk.CTkLabel(main_frame, text="Вес микрофона:", font=('Inter', 14)).grid(row=2, column=0, padx=10, pady=10, sticky='w')
        mic_weight_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        mic_weight_frame.grid(row=2, column=1, columnspan=2, padx=10, pady=10, sticky='w')
        self.mic_weight_slider = ctk.CTkSlider(mic_weight_frame, from_=0.1, to=10.0, number_of_steps=100, width=200)
        self.mic_weight_slider.set(self.settings.get('mic_weight', 1.0))
        self.mic_weight_slider.pack(side='left', padx=(0, 10))
        self.mic_weight_label = ctk.CTkLabel(mic_weight_frame, text=f"{self.mic_weight_slider.get():.1f}", width=40, font=('Inter', 13))
        self.mic_weight_label.pack(side='left')
        self.mic_weight_slider.configure(command=self.update_mic_weight_label)

        # Вес звука (слайдер)
        ctk.CTkLabel(main_frame, text="Вес звука:", font=('Inter', 14)).grid(row=3, column=0, padx=10, pady=10, sticky='w')
        sys_weight_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        sys_weight_frame.grid(row=3, column=1, columnspan=2, padx=10, pady=10, sticky='w')
        self.sys_weight_slider = ctk.CTkSlider(sys_weight_frame, from_=0.1, to=10.0, number_of_steps=100, width=200)
        self.sys_weight_slider.set(self.settings.get('sys_weight', 3.0))
        self.sys_weight_slider.pack(side='left', padx=(0, 10))
        self.sys_weight_label = ctk.CTkLabel(sys_weight_frame, text=f"{self.sys_weight_slider.get():.1f}", width=40, font=('Inter', 13))
        self.sys_weight_label.pack(side='left')
        self.sys_weight_slider.configure(command=self.update_sys_weight_label)

        # Пояснение
        explanation = ctk.CTkLabel(main_frame, text="Чем выше вес, тем громче источник в миксе.\nРекомендуется: микрофон 1.0, звук - 3.0.",
                                font=('Inter', 12), justify='left', wraplength=400)
        explanation.grid(row=4, column=0, columnspan=3, padx=10, pady=(5, 15), sticky='w')

        # ----- Порог тишины -----
        ctk.CTkLabel(main_frame, text="Порог тишины (RMS):", font=('Inter', 14)).grid(row=5, column=0, padx=10, pady=10, sticky='w')
        threshold_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        threshold_frame.grid(row=5, column=1, columnspan=2, padx=10, pady=10, sticky='w')
        self.silence_threshold_slider = ctk.CTkSlider(threshold_frame, from_=0.01, to=0.05, number_of_steps=40, width=250)
        self.silence_threshold_slider.set(self.settings.get('silence_threshold', 0.01))
        self.silence_threshold_slider.pack(side='left', padx=(0, 10))
        self.silence_threshold_label = ctk.CTkLabel(threshold_frame, text=f"{self.silence_threshold_slider.get():.3f}", width=50, font=('Inter', 13))
        self.silence_threshold_label.pack(side='left')
        self.silence_threshold_slider.configure(command=self.update_threshold_label)

        # ----- Модель Whisper -----
        ctk.CTkLabel(main_frame, text="Модель Whisper:", font=('Inter', 14)).grid(row=6, column=0, padx=10, pady=10, sticky='w')
        whisper_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        whisper_frame.grid(row=6, column=1, columnspan=2, padx=10, pady=10, sticky='w')
        self.whisper_var = ctk.StringVar(value=WHISPER_DISPLAY[self.settings.get('whisper_model', 'small')])
        self.whisper_combo = ctk.CTkOptionMenu(
            whisper_frame,
            values=list(WHISPER_DISPLAY.values()),
            variable=self.whisper_var,
            width=200,
            font=('Inter', 13),
            command=self._on_whisper_changed
        )
        self.whisper_combo.pack(side='left', padx=(0, 10))

        self.download_whisper_btn = ctk.CTkButton(whisper_frame, text="Скачать", command=self.download_whisper_model, width=80, font=('Inter', 12))
        self.download_whisper_btn.pack(side='left')
        self.whisper_progress = ctk.CTkProgressBar(whisper_frame, width=100, height=8)
        self.whisper_progress.pack(side='left', padx=5)
        self.whisper_progress.set(0)
        self.whisper_progress.pack_forget()
        self.whisper_status_label = ctk.CTkLabel(whisper_frame, text="", font=('Inter', 11))
        self.whisper_status_label.pack(side='left', padx=10)

        # ----- Модель Ollama -----
        ctk.CTkLabel(main_frame, text="Модель Ollama:", font=('Inter', 14)).grid(row=7, column=0, padx=10, pady=10, sticky='w')
        ollama_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        ollama_frame.grid(row=7, column=1, columnspan=2, padx=10, pady=10, sticky='w')
        self.ollama_var = ctk.StringVar(value=OLLAMA_DISPLAY[self.settings.get('ollama_model', 'gemma3:4b')])
        self.ollama_combo = ctk.CTkOptionMenu(
            ollama_frame,
            values=list(OLLAMA_DISPLAY.values()),
            variable=self.ollama_var,
            width=200,
            font=('Inter', 13),
            command=self._on_ollama_changed
        )
        self.ollama_combo.pack(side='left', padx=(0, 10))

        self.download_ollama_btn = ctk.CTkButton(ollama_frame, text="Скачать", command=self.download_ollama_model, width=80, font=('Inter', 12))
        self.download_ollama_btn.pack(side='left')
        self.ollama_progress = ctk.CTkProgressBar(ollama_frame, width=100, height=8)
        self.ollama_progress.pack(side='left', padx=5)
        self.ollama_progress.set(0)
        self.ollama_progress.pack_forget()
        self.ollama_status_label = ctk.CTkLabel(ollama_frame, text="", font=('Inter', 11))
        self.ollama_status_label.pack(side='left', padx=10)

        # ----- Кнопка сохранения -----
        self.save_btn = ctk.CTkButton(main_frame, text="Сохранить настройки", command=self.save_settings, width=200, height=35, font=('Inter', 14))
        self.save_btn.grid(row=8, column=0, columnspan=3, pady=30)

    def update_mic_weight_label(self, value):
        self.mic_weight_label.configure(text=f"{float(value):.1f}")

    def update_sys_weight_label(self, value):
        self.sys_weight_label.configure(text=f"{float(value):.1f}")

    # ----- Обработчики выбора -----
    def _on_whisper_changed(self, choice=None):
        selected_display = self.whisper_var.get()
        for model, display in WHISPER_DISPLAY.items():
            if display == selected_display:
                self.whisper_selected = model
                self.update_whisper_status()
                break

    def _on_ollama_changed(self, choice=None):
        selected_display = self.ollama_var.get()
        for model, display in OLLAMA_DISPLAY.items():
            if display == selected_display:
                self.ollama_selected = model
                self.ollama_status_label.configure(text="⏳ проверка...", text_color="orange")
                threading.Thread(target=self._async_update_ollama_status, daemon=True).start()
                break

    # ----- Вспомогательные методы -----
    def update_threshold_label(self, value):
        self.silence_threshold_label.configure(text=f"{float(value):.3f}")

    def refresh_device_lists(self):
        devices = get_unique_input_devices()
        mic_list = [f"{idx}: {name}" for idx, name, _ in devices]
        sys_list = mic_list.copy()
        self.mic_combo.configure(values=mic_list)
        self.sys_combo.configure(values=sys_list)
        if self.settings.get('mic_device') is not None:
            for item in mic_list:
                if str(self.settings['mic_device']) in item:
                    self.mic_combo.set(item)
                    break
        if self.settings.get('sys_device') is not None:
            for item in sys_list:
                if str(self.settings['sys_device']) in item:
                    self.sys_combo.set(item)
                    break

    def update_whisper_status(self):
        model_name = getattr(self, 'whisper_selected', None) or self.settings.get('whisper_model', 'small')
        # Проверка через файловую систему
        cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
        model_folder = f"models--Systran--faster-whisper-{model_name}"
        model_path = os.path.join(cache_dir, model_folder)
        found = False
        if os.path.exists(model_path):
            for root, dirs, files in os.walk(model_path):
                if "model.bin" in files:
                    found = True
                    break
        if found:
            self.whisper_status_label.configure(text="✓ установлено", text_color="#3FCABA")
        else:
            self.whisper_status_label.configure(text="✗ не скачана", text_color="orange")
        self.whisper_status_label.update_idletasks()

    def update_ollama_status(self):
        # Вызывается из __init__ и после скачивания
        self._on_ollama_changed()

    def _async_update_ollama_status(self):
        model_name = getattr(self, 'ollama_selected', None) or self.settings.get('ollama_model', 'gemma3:4b')
        try:
            installed = [m['model'] for m in ollama.list()['models']]
            is_installed = model_name in installed
        except Exception:
            is_installed = False
        self.after(0, lambda: self._update_ollama_status_ui(is_installed))

    def _update_ollama_status_ui(self, is_installed):
        if is_installed:
            self.ollama_status_label.configure(text="✓ установлено", text_color="#3FCABA")
        else:
            self.ollama_status_label.configure(text="✗ не запущена\установлена", text_color="orange")

    # ----- Скачивание моделей -----
    def download_whisper_model(self):
        model_name = getattr(self, 'whisper_selected', None) or self.settings.get('whisper_model', 'small')
        self.download_whisper_btn.configure(state="disabled", text="Загрузка...")
        self.whisper_progress.pack(side='left', padx=5)
        self.whisper_progress.start()
        self.on_status(f"Загрузка модели Whisper {model_name}...", "active")
        threading.Thread(target=self._download_whisper_thread, args=(model_name,), daemon=True).start()

    def _download_whisper_thread(self, model_name):
        try:
            repo_id = f"Systran/faster-whisper-{model_name}"
            snapshot_download(repo_id=repo_id)
            self.after(0, lambda: self.on_status(f"Модель Whisper {model_name} успешно скачана"), "active")
            self.after(0, self.update_whisper_status)
        except Exception as e:
            self.after(0, lambda: self.on_status(f"Ошибка загрузки Whisper: {e}"), "critical")
        finally:
            self.after(0, lambda: self.download_whisper_btn.configure(state="normal", text="Скачать"))
            self.after(0, lambda: self.whisper_progress.stop())
            self.after(0, lambda: self.whisper_progress.pack_forget())

    def download_ollama_model(self):
        model_name = getattr(self, 'ollama_selected', None) or self.settings.get('ollama_model', 'gemma3:4b')
        self.download_ollama_btn.configure(state="disabled", text="Загрузка...")
        self.ollama_progress.pack(side='left', padx=5)
        self.ollama_progress.start()
        self.on_status(f"Загрузка модели Ollama {model_name}...", "active")
        threading.Thread(target=self._download_ollama_thread, args=(model_name,), daemon=True).start()

    def _download_ollama_thread(self, model_name):
        try:
            ollama.pull(model_name)
            self.after(0, lambda: self.on_status(f"Модель Ollama {model_name} успешно установлена"), "active")
            self.after(0, self.update_ollama_status)
        except Exception as e:
            self.after(0, lambda: self.on_status(f"Ошибка загрузки Ollama: {e}"), "critical")
        finally:
            self.after(0, lambda: self.download_ollama_btn.configure(state="normal", text="Скачать"))
            self.after(0, lambda: self.ollama_progress.stop())
            self.after(0, lambda: self.ollama_progress.pack_forget())

    # ----- Тест устройств -----
    def test_mic(self):
        self.test_device(self.mic_combo.get(), "микрофон")

    def test_sys(self):
        self.test_device(self.sys_combo.get(), "системный звук")

    def test_device(self, device_str, name):
        try:
            dev_id = int(device_str.split(':')[0])
        except:
            self.on_status("Ошибка: неверное устройство", "critical")
            return
        self.on_status(f"Тестируем {name}...", "active")
        threading.Thread(target=self._test_thread, args=(dev_id, name), daemon=True).start()

    def _test_thread(self, dev_id, name):
        duration = 3
        try:
            channels = sd.query_devices(dev_id)['max_input_channels']
            if channels > 2:
                channels = 2
            recording = sd.rec(int(duration * 16000), samplerate=16000, channels=channels, dtype='float32', device=dev_id)
            sd.wait()
            if channels == 2:
                recording = np.mean(recording, axis=1)
            else:
                recording = recording.flatten()
            max_val = np.max(np.abs(recording))
            if max_val > 0:
                recording = recording / max_val
            model = Transcriber(model_name='tiny', device='cpu')
            text = model.transcribe_chunk(recording)
            self.after(0, lambda: self.on_status(f"Тест {name} распознал: {text[:100]}"), "active")
        except Exception as e:
            self.after(0, lambda: self.on_status(f"Ошибка теста {name}: {e}"), "critical")

    # ----- Сохранение настроек -----
    def save_settings(self):
        try:
            mic_str = self.mic_combo.get()
            sys_str = self.sys_combo.get()
            mic_id = int(mic_str.split(':')[0]) if mic_str else None
            sys_id = int(sys_str.split(':')[0]) if sys_str else None
            self.settings.update({
                'mic_device': mic_id,
                'sys_device': sys_id,
                'mic_weight': float(self.mic_weight_slider.get()),
                'sys_weight': float(self.sys_weight_slider.get()),
                'silence_threshold': float(self.silence_threshold_slider.get()),
                'whisper_model': getattr(self, 'whisper_selected', None) or self.settings.get('whisper_model', 'small'),
                'ollama_model': getattr(self, 'ollama_selected', None) or self.settings.get('ollama_model', 'gemma3:4b')
            })
            self.on_settings_change(self.settings)
            self.on_status("Настройки сохранены", "active")
        except Exception as e:
            self.on_status(f"Ошибка сохранения: {e}", "critical")