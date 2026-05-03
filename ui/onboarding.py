import customtkinter as ctk
import json
import os
import threading
from core.devices import get_unique_input_devices
import ollama
from huggingface_hub import snapshot_download
import logging
logger = logging.getLogger(__name__)

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

class OnboardingFrame(ctk.CTkFrame):
    def __init__(self, parent, settings_path, on_complete):
        super().__init__(parent)
        self.on_complete = on_complete
        self.settings_path = settings_path
        self.settings = {}
        self.create_widgets()
        self.update_whisper_status()
        self.update_ollama_status()

    def create_widgets(self):
        import webbrowser
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ctk.CTkLabel(main_frame, text="Настройка моделей", font=('Inter', 18, 'bold')).pack(pady=(0, 15))

        # ----- Whisper -----
        ctk.CTkLabel(main_frame, text="Модель Whisper (распознавание речи):", font=('Inter', 14)).pack(anchor='w', pady=(10, 5))
        whisper_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        whisper_frame.pack(fill='x', pady=5)

        self.whisper_var = ctk.StringVar()
        self.whisper_combo = ctk.CTkOptionMenu(whisper_frame, values=list(WHISPER_DISPLAY.values()),
                                             variable=self.whisper_var, width=250, font=('Inter', 13), command=self._on_whisper_changed)
        self.whisper_combo.pack(side='left', padx=(0, 10))
        default_whisper = "small"
        self.whisper_var.set(WHISPER_DISPLAY[default_whisper])
        self.whisper_selected = default_whisper

        self.download_whisper_btn = ctk.CTkButton(whisper_frame, text="Скачать", command=self.download_whisper_model,
                                                  width=80, font=('Inter', 12))
        self.download_whisper_btn.pack(side='left', padx=5)
        self.whisper_progress = ctk.CTkProgressBar(whisper_frame, width=100, height=8)
        self.whisper_progress.pack(side='left', padx=5)
        self.whisper_progress.set(0)
        self.whisper_progress.pack_forget()
        self.whisper_status_label = ctk.CTkLabel(whisper_frame, text="", font=('Inter', 11))
        self.whisper_status_label.pack(side='left', padx=10)

        # Ручная ссылка на виспер
        whisper_link = ctk.CTkButton(whisper_frame, text="Скачать модели Whisper вручную", command=lambda: webbrowser.open("https://huggingface.co/Systran/faster-whisper-small"), fg_color="transparent", text_color="#3FCABA", font=('Inter', 12))
        whisper_link.pack(side='left', padx=5)

        # ----- Ollama -----
        ctk.CTkLabel(main_frame, text="Модель Ollama (генерация итогов):", font=('Inter', 14)).pack(anchor='w', pady=(15, 5))
        ollama_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        ollama_frame.pack(fill='x', pady=5)

        self.ollama_var = ctk.StringVar()
        self.ollama_combo = ctk.CTkOptionMenu(ollama_frame, values=list(OLLAMA_DISPLAY.values()),
                                            variable=self.ollama_var, width=250, font=('Inter', 13), command=self._on_ollama_changed)
        self.ollama_combo.pack(side='left', padx=(0, 10))
        default_ollama = "gemma3:4b"
        self.ollama_var.set(OLLAMA_DISPLAY[default_ollama])
        self.ollama_selected = default_ollama

        self.download_ollama_btn = ctk.CTkButton(ollama_frame, text="Скачать", command=self.download_ollama_model,
                                                 width=80, font=('Inter', 12))
        self.download_ollama_btn.pack(side='left', padx=5)
        self.ollama_progress = ctk.CTkProgressBar(ollama_frame, width=100, height=8)
        self.ollama_progress.pack(side='left', padx=5)
        self.ollama_progress.set(0)
        self.ollama_progress.pack_forget()
        self.ollama_status_label = ctk.CTkLabel(ollama_frame, text="", font=('Inter', 11))
        self.ollama_status_label.pack(side='left', padx=10)

        # Ручная сссылка на оламу
        ollama_link = ctk.CTkButton(ollama_frame, text="Cначала скачайте сервер ollama", command=lambda: webbrowser.open("https://ollama.com/download"), fg_color="transparent", text_color="#3FCABA", font=('Inter', 12))
        ollama_link.pack(side='left', padx=5)

        # ----- Устройства -----
        devices = get_unique_input_devices()
        device_names = [name for _, name, _ in devices]
        self.device_map = {name: idx for idx, name, _ in devices}

        ctk.CTkLabel(main_frame, text="Микрофон:", font=('Inter', 13)).pack(anchor='w', pady=(10, 0))
        self.mic_combo = ctk.CTkOptionMenu(main_frame, values=device_names, font=('Inter', 13))
        self.mic_combo.pack(fill='x', pady=5)

        ctk.CTkLabel(main_frame, text="Звук (системный):", font=('Inter', 13)).pack(anchor='w')
        self.sys_combo = ctk.CTkOptionMenu(main_frame, values=device_names, font=('Inter', 13))
        self.sys_combo.pack(fill='x', pady=5)
        
        ctk.CTkLabel(main_frame, 
             text="Примечание: для захвата звука с ПК выберите 'Стерео-микшер'\n(если его нет, включите в настройках звука).",
             font=('Inter', 11), wraplength=500, justify='left').pack(pady=(5, 10), anchor='w')

        # Ставим устройства по умолчанию
        from core.devices import get_default_input_device
        # Микрофон
        def_mic_id, def_mic_name = get_default_input_device()
        if def_mic_name:
            mic_values = self.mic_combo.cget('values')
            if def_mic_name in mic_values:
                self.mic_combo.set(def_mic_name)

        # Порог тишины
        ctk.CTkLabel(main_frame, text="Порог тишины (RMS):", font=('Inter', 13)).pack(anchor='w', pady=(10, 5))
        self.threshold_slider = ctk.CTkSlider(main_frame, from_=0.01, to=0.05, number_of_steps=40)
        self.threshold_slider.set(0.01)
        self.threshold_slider.pack(fill='x', pady=5)
        self.threshold_label = ctk.CTkLabel(main_frame, text="0.010", font=('Inter', 12))
        self.threshold_label.pack(anchor='w')
        self.threshold_slider.configure(command=lambda v: self.threshold_label.configure(text=f"{float(v):.3f}"))

        ctk.CTkButton(main_frame, text="Завершить настройку", command=self.save_and_close,
                      font=('Inter', 14), height=30, width=200).pack(pady=(20, 10))

    def _on_whisper_changed(self, _=None):
        selected_display = self.whisper_var.get()
        for model, display in WHISPER_DISPLAY.items():
            if display == selected_display:
                self.whisper_selected = model
                self.update_whisper_status()
                break

    def _on_ollama_changed(self, _=None):
        selected_display = self.ollama_var.get()
        for model, display in OLLAMA_DISPLAY.items():
            if display == selected_display:
                self.ollama_selected = model
                self.update_ollama_status()
                break

    def update_whisper_status(self):
        model_name = self.whisper_selected
        if not model_name:
            return
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
            self.whisper_status_label.configure(text="✗ не установлено", text_color="orange")
        self.whisper_status_label.update_idletasks()

    def update_ollama_status(self):
        model_name = self.ollama_selected
        if not model_name:
            return
        self.ollama_status_label.configure(text="⏳ проверка...", text_color="orange")
        threading.Thread(target=self._async_update_ollama_status, daemon=True).start()

    def _async_update_ollama_status(self):
        model_name = self.ollama_selected
        if not model_name:
            return
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
            self.ollama_status_label.configure(text="✗ не установлено", text_color="orange")

    def download_whisper_model(self):
        model_name = self.whisper_selected
        if not model_name:
            return
        self.download_whisper_btn.configure(state="disabled", text="Загрузка...")
        self.whisper_progress.pack(side='left', padx=5)
        self.whisper_progress.start()
        threading.Thread(target=self._download_whisper_thread, args=(model_name,), daemon=True).start()

    def _download_whisper_thread(self, model_name):
        import traceback
        try:
            logger.info(f"Начало скачивания модели Whisper: {model_name}")
            repo_id = f"Systran/faster-whisper-{model_name}"
            snapshot_download(repo_id=repo_id, tqdm_class=None)
            logger.info(f"Модель Whisper {model_name} успешно скачана")
            self.after(0, lambda: self.whisper_status_label.configure(text="✓ установлено", text_color="#3FCABA"))
        except Exception as e:
            logger.error(f"Ошибка скачивания Whisper {model_name}: {e}\n{traceback.format_exc()}")
            self.after(0, lambda: self.whisper_status_label.configure(text="Ошибка", text_color="red"))
        finally:
            self.after(0, lambda: self.download_whisper_btn.configure(state="normal", text="Скачать"))
            self.after(0, lambda: self.whisper_progress.stop())
            self.after(0, lambda: self.whisper_progress.pack_forget())

    def download_ollama_model(self):
        model_name = self.ollama_selected
        if not model_name:
            return
        self.download_ollama_btn.configure(state="disabled", text="Загрузка...")
        self.ollama_progress.pack(side='left', padx=5)
        self.ollama_progress.start()
        threading.Thread(target=self._download_ollama_thread, args=(model_name,), daemon=True).start()

    def _download_ollama_thread(self, model_name):
        import traceback
        try:
            logger.info(f"Начало скачивания модели ollama: {model_name}")
            ollama.pull(model_name)
            self.after(0, lambda: self.ollama_status_label.configure(text="✓ установлено", text_color="#3FCABA"))
            logger.info(f"Модель ollama {model_name} успешно скачана")
        except Exception as e:
            logger.error(f"Ошибка скачивания ollama {model_name}: {e}\n{traceback.format_exc()}")
            self.after(0, lambda: self.ollama_status_label.configure(text="Ошибка", text_color="red"))
        finally:
            self.after(0, lambda: self.download_ollama_btn.configure(state="normal", text="Скачать"))
            self.after(0, lambda: self.ollama_progress.stop())
            self.after(0, lambda: self.ollama_progress.pack_forget())

    def save_and_close(self):
        try:
            mic_name = self.mic_combo.get()
            sys_name = self.sys_combo.get()
            mic_id = self.device_map.get(mic_name) if mic_name else None
            sys_id = self.device_map.get(sys_name) if sys_name else None
            self.settings = {
                'whisper_model': self.whisper_selected,
                'ollama_model': self.ollama_selected,
                'mic_device': mic_id,
                'sys_device': sys_id,
                'mic_weight': 1.0,
                'sys_weight': 5.0,
                'silence_threshold': float(self.threshold_slider.get()),
                'block_duration': 5.0,
                'mode': 'mix'
            }
            # Создаём папку config, если её нет
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
            self.on_complete(self.settings)
        except Exception as e:
            print("Ошибка сохранения настроек:", e)