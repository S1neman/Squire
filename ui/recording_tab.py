import customtkinter as ctk
import threading
import time
import numpy as np
import os
import ollama
from core.audio_capture import AudioCapture
from core.transcriber import Transcriber
from core.history import save_session, update_session_transcript, update_session_summary, save_transcript_to_file, save_summary_to_file

class RecordingTab(ctk.CTkFrame):
    def __init__(self, parent, settings, on_status_update, on_transcript_update, on_summary_update, on_settings_change, history_tab):
        super().__init__(parent)
        self.settings = settings
        self.on_status = on_status_update
        self.on_transcript = on_transcript_update
        self.on_summary = on_summary_update
        self.on_settings_change = on_settings_change
        self.history_tab = history_tab
        self.is_recording = False
        self.capture = None
        self.transcriber = None
        self.current_session_id = None
        self.live_text = ""
        self.status_animation_running = False
        self.status_animation_message = ""
        self.status_anim_index = 0
        self.create_widgets()
        self._update_whisper_status_label()
        self._update_ollama_status_label()

    # ---- Анимация статуса ----
    def _start_status_animation(self, message):
        self.status_animation_running = True
        self.status_animation_message = message
        self.status_anim_index = 0
        self._animate_status_text()

    def _animate_status_text(self):
        if not self.status_animation_running:
            return
        symbols = ["◐", "◓", "◑", "◒"]
        self.status_anim_index = (self.status_anim_index + 1) % len(symbols)
        symbol = symbols[self.status_anim_index]
        self.on_status(f"{symbol} {self.status_animation_message}", "active")
        self.after(500, self._animate_status_text)

    def _stop_status_animation(self, final_message=None):
        self.status_animation_running = False
        if final_message is not None:
            self.on_status(final_message)
    
    def refresh_templates_list(self):
        from core.templates import load_templates
        templates = load_templates()
        template_names = [t['name'] for t in templates]
        # Обновляем выпадающий список
        self.template_combo.configure(values=template_names)
        # Если текущий выбранный шаблон не существует, выбираем первый
        current = self.template_var.get()
        if current not in template_names and template_names:
            self.template_var.set(template_names[0])
            self._on_template_change(None)
        # Принудительно обновляем интерфейс
        self.update_idletasks()

    # ---- Создание виджетов ----
    def create_widgets(self):
        control_frame = ctk.CTkFrame(self)
        control_frame.pack(pady=15, padx=20, fill='x')
        
        self.record_btn = ctk.CTkButton(
            control_frame,
            text="Начать запись",
            command=self.toggle_recording,
            fg_color="#CACACA",
            hover_color="#DFDFDF",
            text_color="#141414",
            height=40,
            width=150,
            font=("Inter", 16, "bold")
        )
        self.record_btn.pack(side='left', padx=(0, 20))

        self.mode_var = ctk.StringVar(value=self.settings.get('mode', 'mix'))

        mode_mix = ctk.CTkRadioButton(control_frame, text="Мик. и Звук", variable=self.mode_var, value="mix",
                                    font=("Inter", 13), width=100)
        mode_mix.pack(side='left', padx=5)

        mode_mic = ctk.CTkRadioButton(control_frame, text="Микрофон", variable=self.mode_var, value="mic",
                                    font=("Inter", 13), width=100)
        mode_mic.pack(side='left', padx=5)

        mode_sys = ctk.CTkRadioButton(control_frame, text="Звук", variable=self.mode_var, value="system",
                                    font=("Inter", 13), width=100)
        mode_sys.pack(side='left', padx=5)

        # Фрейм для автогенерации и выбора шаблона
        auto_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        auto_frame.pack(side='right', padx=(0))

        self.auto_gen_var = ctk.BooleanVar(value=self.settings.get('auto_generate', False))
        self.auto_gen_check = ctk.CTkCheckBox(auto_frame, text="Автогенерация итогов", variable=self.auto_gen_var,
                                            font=("Inter", 13))
        self.auto_gen_check.pack(side='left', padx=5)

        self.template_var = ctk.StringVar(value=self.settings.get('template_name', 'Стандартный'))
        self.template_combo = ctk.CTkOptionMenu(auto_frame, values=self._get_template_names(),
                                                variable=self.template_var, width=150, font=("Inter", 13))
        self.template_combo.pack(side='left', padx=0)

        self.auto_gen_check.configure(command=self._on_auto_gen_change)
        self.template_combo.configure(command=self._on_template_change)

        # Контейнер для двух равных областей
        middle_frame = ctk.CTkFrame(self, fg_color="transparent")
        middle_frame.pack(pady=10, padx=20, fill='both', expand=True)
        middle_frame.grid_columnconfigure(0, weight=1, uniform='col')
        middle_frame.grid_columnconfigure(1, weight=1, uniform='col')
        middle_frame.grid_rowconfigure(0, weight=1)

        # Левая половина: расшифровка
        left_frame = ctk.CTkFrame(middle_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        transcript_header = ctk.CTkFrame(left_frame, fg_color="transparent")
        transcript_header.pack(fill='x', pady=(0, 5))
        ctk.CTkLabel(transcript_header, text="Расшифровка:", font=('Inter', 16, 'bold')).pack(side='left')
        self.copy_transcript_btn = ctk.CTkButton(transcript_header, text="❐", width=32, height=32,
                                                command=self.copy_transcript, font=("Inter", 14))
        self.copy_transcript_btn.pack(side='right', padx=0)
        
        self.text_area = ctk.CTkTextbox(left_frame, wrap='word', font=('Inter', 13))
        self.text_area.pack(fill='both', expand=True)
        
        # Правая половина: итоги
        right_frame = ctk.CTkFrame(middle_frame, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        summary_header = ctk.CTkFrame(right_frame, fg_color="transparent")
        summary_header.pack(fill='x', pady=(0, 5))
        ctk.CTkLabel(summary_header, text="✨ Итоги:", font=('Inter', 16, 'bold')).pack(side='left')
        self.copy_summary_btn = ctk.CTkButton(summary_header, text="❐", width=32, height=32,
                                            command=self.copy_summary, font=("Inter", 14))
        self.copy_summary_btn.pack(side='right', padx=0)
        self.summary_btn = ctk.CTkButton(summary_header, text="Сделать итоги", command=self.make_summary,
                                        width=120, height=32, font=("Inter", 13))
        self.summary_btn.pack(side='right', padx=10)
        
        self.summary_box = ctk.CTkTextbox(right_frame, wrap='word', font=('Inter', 13))
        self.summary_box.pack(fill='both', expand=True)
        self.summary_box.insert('0.0', "Начните запись...")
        self.summary_box.configure(state='disabled')

        # Статусы моделей
        self.whisper_status_label = ctk.CTkLabel(left_frame, text="", font=('Inter', 11))
        self.whisper_status_label.pack(anchor='w', padx=8, pady=(5, 10))
        self.ollama_status_label = ctk.CTkLabel(right_frame, text="", font=('Inter', 11))
        self.ollama_status_label.pack(anchor='w', padx=8, pady=(5, 10))

    def _get_template_names(self):
        from core.templates import load_templates
        templates = load_templates()
        return [t['name'] for t in templates]
    
    def _on_auto_gen_change(self):
        self.settings['auto_generate'] = self.auto_gen_var.get()
        self.on_settings_change(self.settings)
        self._update_ollama_status_label()

    def _on_template_change(self, choice):
        self.settings['template_name'] = self.template_var.get()
        self.on_settings_change(self.settings)

    # ---- Управление записью ----
    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        mic_id = self.settings.get('mic_device')
        sys_id = self.settings.get('sys_device')
        if mic_id is None:
            self.on_status("Ошибка: не выбран микрофон", "error")
            return
        mode = self.mode_var.get()
        if mode in ('system', 'mix') and sys_id is None:
            self.on_status("Ошибка: не выбран системный звук", "error")
            return

        self.is_recording = True
        # Очищаем текст перед записью
        self.text_area.configure(state="normal")
        self.text_area.delete('0.0', 'end')
        self.text_area.configure(state="disabled")
        self.live_text = ""
        self.summary_box.configure(state='normal')
        self.summary_box.delete('0.0', 'end')
        self.summary_box.insert('0.0', "Идёт запись")
        self.summary_box.configure(state='disabled')
        self.record_btn.configure(
            fg_color="#7a0000",
            hover_color="#871919",
            text_color="#ffffff",
            text="⏹️ Остановить"
        )

        self.capture = AudioCapture(mic_id, sys_id, mode,
                                    mic_weight=self.settings.get('mic_weight', 1.0),
                                    sys_weight=self.settings.get('sys_weight', 3.0))
        print("[DEBUG] capture created")
        self.capture.start()
        self.transcriber = Transcriber(model_name=self.settings.get('whisper_model', 'small'), device='cpu')
        print("[DEBUG] transcriber created")

        # Запускаем анимацию записи
        self._start_status_animation(f"Запись ({mode})")

        save_session(mode, str(mic_id), str(sys_id), "", "", 0)
        from core.history import get_all_sessions
        sessions = get_all_sessions()
        if sessions:
            self.current_session_id = sessions[0][0]

        print("[DEBUG] about to start live_thread")
        self.live_thread = threading.Thread(target=self.live_transcribe_loop, daemon=True)
        self.live_thread.start()
        print("[DEBUG] live_thread started, is_alive:", self.live_thread.is_alive())

        # Обновляем статусы моделей
        self._update_whisper_status_label()
        self._update_ollama_status_label()

    def live_transcribe_loop(self):
        print("[DEBUG] live_transcribe_loop ENTERED")
        silence_threshold = self.settings.get('silence_threshold', 0.01)
        while self.is_recording:
            time.sleep(self.settings.get('block_duration', 2.0))
            if not self.is_recording:
                break
            print("[DEBUG] before get_next_block, is_recording =", self.is_recording)
            block = self.capture.get_next_block(self.settings.get('block_duration', 2.0))
            print("[DEBUG] block =", block is not None)
            if block is not None:
                rms = np.sqrt(np.mean(block**2))
                print(f"[DEBUG] RMS = {rms:.5f}, threshold = {silence_threshold}")
                if rms < silence_threshold:
                    print("  -> skip (below threshold)")
                    continue
                text = self.transcriber.transcribe_chunk(block)
                if text:
                    print(f"[DEBUG] live_transcribe_loop: text='{text[:50]}...'")
                    self.after(0, lambda t=text: self.append_transcript(t))

    def append_transcript(self, new_text):
        print(f"[DEBUG] append_transcript called, text='{new_text[:50]}...'")
        self.text_area.configure(state="normal")
        self.text_area.insert('end', new_text)
        self.text_area.see('end')
        self.text_area.configure(state="disabled")
        self.live_text += new_text
        print(f"[DEBUG] live_text length now: {len(self.live_text)}")
        self.on_transcript(self.live_text)
        if self.current_session_id:
            update_session_transcript(self.current_session_id, self.live_text)
            save_transcript_to_file(self.current_session_id, self.live_text)
        self.update_idletasks()

    def update_text_area_full(self):
        self.text_area.configure(state="normal")
        self.text_area.delete('0.0', 'end')
        self.text_area.insert('0.0', self.live_text)
        self.text_area.see('end')
        self.text_area.configure(state="disabled")
        self.on_transcript(self.live_text)
        if self.current_session_id:
            update_session_transcript(self.current_session_id, self.live_text)
            save_transcript_to_file(self.current_session_id, self.live_text)
        self.update_idletasks()

    def stop_recording(self):
        self.is_recording = False
        self.record_btn.configure(
            fg_color="#CACACA",
            hover_color="#DFDFDF",
            text_color="#141414",
            text="Начать запись"
        )
        # Запускаем анимацию финальной транскрипции
        self._start_status_animation("Остановлено, финальная транскрипция")
        
        if self.capture:
            self.capture.stop()
        if self.live_thread and self.live_thread.is_alive():
            self.live_thread.join(timeout=2)

        # Запускаем финальную транскрипцию в отдельном потоке
        threading.Thread(target=self._finalize_transcription, daemon=True).start()

    def _finalize_transcription(self):
        full_audio = self.capture.get_full_audio() if self.capture else None
        if full_audio is not None:
            final_text = self.transcriber.transcribe_full(full_audio)
            if final_text:
                self.live_text = final_text
                self.after(0, self.update_text_area_full)
                if self.current_session_id:
                    update_session_transcript(self.current_session_id, final_text)
                    save_transcript_to_file(self.current_session_id, final_text)
                # Обновляем историю
                if self.history_tab:
                    self.after(0, self.history_tab.refresh)
        # Автогенерация
        if self.auto_gen_var.get():
            self.after(0, self.make_summary)
        else:
            # Финальное сообщение
            self.after(0, lambda: self._stop_status_animation("Готово. Нажмите 'Сделать итоги'"))

    # ---- Генерация итогов ----
    def make_summary(self):
        if not self.live_text.strip():
            self.on_status("Нет текста для итогов", "info")
            self._stop_status_animation("Нет текста для итогов", "info")
            return
        from core.summarizer import is_ollama_model_available
        model_name = self.settings.get('ollama_model', 'gemma3:4b')
        if not is_ollama_model_available(model_name):
            self.on_status(f"Ошибка: модель Ollama '{model_name}' не установлена или сервер не запущен", "error")
            self._stop_status_animation(f"Ошибка: модель Ollama не установлена", "error")
            self._update_ollama_status_label()
            return
        from core.templates import load_templates
        templates = load_templates()
        template_prompt = None
        selected_name = self.template_var.get()
        for t in templates:
            if t['name'] == selected_name:
                template_prompt = t['prompt']
                break
        # Смена статусов
        self.status_animation_message = "Генерация итогов через Ollama..."
        if not self.status_animation_running:
            self._start_status_animation("Генерация итогов через Ollama...")
        threading.Thread(target=self._summarize_thread, args=(template_prompt,), daemon=True).start()
        # Обновляем статус модели Ollama
        self._update_ollama_status_label()

    def _summarize_thread(self, template_prompt):
        from core.summarizer import summarize_text
        try:
            summary = summarize_text(self.live_text, model=self.settings.get('ollama_model', 'gemma3:4b'),
                                    template_prompt=template_prompt)
            self.after(0, lambda: self._show_summary(summary))
            if self.current_session_id:
                update_session_summary(self.current_session_id, summary)
                save_summary_to_file(self.current_session_id, summary)
            self.after(0, lambda: self._stop_status_animation("Итоги готовы"))
        except Exception as e:
            self.after(0, lambda: self._stop_status_animation(f"Ошибка: {e}"))

    def _show_summary(self, summary):
        self.summary_box.configure(state='normal')
        self.summary_box.delete('0.0', 'end')
        self.summary_box.insert('0.0', summary)
        self.summary_box.configure(state='disabled')
        self.on_summary(summary)
        if self.history_tab:
            self.history_tab.refresh()

    # ---- Копирование ----
    def copy_transcript(self):
        text = self.text_area.get('0.0', 'end').strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.on_status("Расшифровка скопирована в буфер", "active")
        else:
            self.on_status("Нет текста для копирования", "info")

    def copy_summary(self):
        self.summary_box.configure(state='normal')
        text = self.summary_box.get('0.0', 'end').strip()
        self.summary_box.configure(state='disabled')
        if text and not text.startswith("Начните запись") and not text.startswith("Идёт запись"):
            self.clipboard_clear()
            self.clipboard_append(text)
            self.on_status("Итоги скопированы в буфер", "active")
        else:
            self.on_status("Нет итогов для копирования", "info")

    # ---- Статусы моделей ----
    def _update_whisper_status_label(self):
        model_name = self.settings.get('whisper_model', 'small')
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
        status_text = "✓ активно" if found else "✗ не запущена"
        color = "#3FCABA" if found else "orange"
        self.whisper_status_label.configure(text=f"Whisper {model_name}: {status_text}", text_color=color)

    def _update_ollama_status_label(self):
        model_name = self.settings.get('ollama_model', 'gemma3:4b')
        # Асинхронная проверка
        def check():
            try:
                installed = [m['model'] for m in ollama.list()['models']]
                is_installed = model_name in installed
            except Exception:
                is_installed = False
            self.after(0, lambda: self._set_ollama_status(model_name, is_installed))
        threading.Thread(target=check, daemon=True).start()

    def _set_ollama_status(self, model_name, is_installed):
        status_text = "✓ активно" if is_installed else "✗ не запущена"
        color = "#3FCABA" if is_installed else "orange"
        self.ollama_status_label.configure(text=f"Ollama {model_name}: {status_text}", text_color=color)