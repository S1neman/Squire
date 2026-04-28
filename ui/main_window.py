import customtkinter as ctk
import json
import os
import threading
from PIL import Image
import pystray
from ui.onboarding import OnboardingFrame
from ui.recording_tab import RecordingTab
from ui.devices_tab import DevicesTab
from ui.history_tab import HistoryTab
from core.history import init_db
from core.model_manager import ensure_ollama_running
from ui.templates_tab import TemplatesTab
from core.paths import CONFIG_DIR, BASE_DIR, RESOURCE_DIR


SETTINGS_FILE = os.path.join(CONFIG_DIR, 'settings.json')

class SquireApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Squire")
        self.geometry("920x600")
        self.minsize(920, 600)

        # Центрирование окна
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 1000) // 2
        y = (screen_height - 700) // 2
        self.geometry(f"920x600+{x}+{y}")

        # Иконка в заголовке окна
        icon_path = os.path.join(RESOURCE_DIR, "assets", "icons", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                print(f"Не удалось загрузить иконку окна: {e}")

        # Иконка в системном трее
        icon_path = os.path.join(RESOURCE_DIR, "assets", "icons", "app_icon.ico")

        # Создаём папку config, если её нет
        os.makedirs(CONFIG_DIR, exist_ok=True)

        self.settings = None
        self.init_ui()

    def setup_tray_icon(self):
        icon_path = os.path.join(BASE_DIR, "assets", "icons", "app_icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(BASE_DIR, "assets", "icons", "app_icon.png")
        if not os.path.exists(icon_path):
            print("Иконка для трея не найдена")
            return
        try:
            image = Image.open(icon_path)

            def show_window():
                self.deiconify()
                self.lift()
                self.focus_force()
                self.state('normal')

            def quit_app(icon, item):
                icon.stop()
                self.after(0, self.quit)

            def on_click(icon, button):
                print(f"DEBUG: Button clicked: {button}")
                if button == pystray.Button.DOUBLE_LEFT:
                    self.after(0, show_window)

            menu = pystray.Menu(
                pystray.MenuItem("Показать", lambda: self.after(0, show_window)),
                pystray.MenuItem("Выход", quit_app)
            )

            self.tray_icon = pystray.Icon(
                "squire_app",
                image,
                "Squire",
                menu,
                on_click=on_click
            )
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            print(f"Не удалось запустить иконку трея: {e}")

    def init_ui(self):
        self.settings = self.load_settings()
        if not self.settings:
            self._show_onboarding()
        else:
            # Проверяем и запускаем Ollama в фоне
            def on_ollama_started(success):
                if not success:
                    self.update_status("Не удалось запустить Ollama. Установите и запустите вручную.", "critical")
            threading.Thread(target=lambda: ensure_ollama_running(on_ollama_started), daemon=True).start()
            self._show_main_ui()

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def save_settings(self, new_settings):
        self.settings = new_settings
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4)

    def _show_onboarding(self):
        self.onboarding_frame = OnboardingFrame(self, SETTINGS_FILE, self._on_onboarding_complete)
        self.onboarding_frame.pack(fill='both', expand=True)

    def _on_onboarding_complete(self, settings):
        self.settings = settings
        self.onboarding_frame.destroy()
        self._show_main_ui()

    def _show_main_ui(self):
        init_db()
        # Создаём контейнер
        container = ctk.CTkFrame(self, corner_radius=6, fg_color="#252525")  # цвет вашего фона
        container.pack(pady=(15, 15), padx=15, fill='both', expand=True)

        # Внутри контейнера размещаем tabview
        self.tabview = ctk.CTkTabview(container)
        self.tabview.pack(fill='both', expand=True)
        self.tabview._segmented_button.configure(font=("Inter", 14, "bold"), height=50)

        self.tab_recording = self.tabview.add("Запись")
        self.tab_devices = self.tabview.add("Настройки")
        self.tab_templates = self.tabview.add("Шаблоны")
        self.tab_history = self.tabview.add("История")

        for button in self.tabview._segmented_button._buttons_dict.values():
            button.configure(width=120, height=40)
        
        #Статус-бар
        status_frame = ctk.CTkFrame(container, corner_radius=10, fg_color="#333333", height=40)
        status_frame.pack(side='bottom', fill='x', padx=10, pady=(0, 10))
        self.status_label = ctk.CTkLabel(status_frame, text="● Готов", font=('Inter', 13, 'bold'))
        self.status_label.pack(expand=True)

        self.history_tab = HistoryTab(self.tab_history, self.update_status)
        self.history_tab.pack(fill='both', expand=True)

        self.recording_tab = RecordingTab(
            self.tab_recording,
            self.settings,
            self.update_status,
            self.on_transcript_update,
            self.on_summary_update,
            self.save_settings,
            self.history_tab
        )
        self.recording_tab.pack(fill='both', expand=True)

        self.devices_tab = DevicesTab(
            self.tab_devices,
            self.settings,
            self.save_settings,
            self.update_status
        )
        self.devices_tab.pack(fill='both', expand=True)

        self.templates_tab = TemplatesTab(self.tab_templates, self.update_status, self.recording_tab)
        self.templates_tab.pack(fill='both', expand=True)

    def update_status(self, msg, status_type="info"):
        colors = {
            "critical": "#FF5555",
            "error": "#FFA500",
            "active": "#3FCABA",
            "info": "#ffffff"
        }
        color = colors.get(status_type, "#ffffff")
        self.status_label.configure(text=f"{msg}", text_color=color)

    def on_transcript_update(self, text):
        pass

    def on_summary_update(self, summary):
        pass