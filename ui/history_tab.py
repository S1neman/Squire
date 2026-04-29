import customtkinter as ctk
import os
import subprocess
from core.history import get_all_sessions, delete_session
from tkinter import messagebox
from datetime import datetime

class HistoryTab(ctk.CTkFrame):
    def __init__(self, parent, on_status):
        super().__init__(parent)
        self.on_status = on_status
        self.create_widgets()
        self.refresh()

    def create_widgets(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill='x', pady=(10, 5), padx=20)
        ctk.CTkLabel(header, text="История записей", font=('Inter', 18, 'bold')).pack(side='left')
        self.refresh_btn = ctk.CTkButton(header, text="Обновить", command=self.refresh, width=100, font=('Inter', 13))
        self.refresh_btn.pack(side='right')

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill='both', expand=True, padx=20, pady=10)

    def refresh(self):
        scroll_pos = None
        if hasattr(self.scroll_frame, '_parent_canvas'):
            scroll_pos = self.scroll_frame._parent_canvas.yview()

        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        sessions = get_all_sessions()
        if not sessions:
            no_data = ctk.CTkLabel(self.scroll_frame, text="Нет сохранённых записей", font=('Inter', 14))
            no_data.pack(pady=20)
            return

        for sess in sessions:
            sid, ts, dur, mode, transcript, summary = sess
            try:
                dt = datetime.fromisoformat(ts)
                date_str = dt.strftime("%d.%m.%Y %H:%M")
            except:
                date_str = ts[:16]

            # Если итогов нет, показываем расшифровку
            display_text = summary if summary and summary.strip() else transcript
            if not display_text:
                display_text = "(нет текста)"

            card = ctk.CTkFrame(self.scroll_frame, corner_radius=10, border_width=1, border_color="#3a3a3a")
            card.pack(fill='x', pady=4, padx=5)
            card.session_id = sid

            header_frame = ctk.CTkFrame(card, fg_color="transparent")
            header_frame.pack(fill='x', padx=8, pady=(6, 8))

            ctk.CTkLabel(header_frame, text=date_str, font=('Inter', 12, 'bold')).pack(side='left')

            # Кнопка копирования
            copy_btn = ctk.CTkButton(header_frame, text="❐", width=32, height=32,
                                     command=lambda sid=sid: self.copy_summary(sid),
                                     font=('Inter', 14))
            copy_btn.pack(side='left', padx=(10, 5))

            # Кнопка раскрытия/сворачивания
            expand_btn = ctk.CTkButton(header_frame, text="▷", width=32, height=32,
                                       command=lambda sid=sid, crd=card: self.toggle_expand(sid, crd),
                                       font=('Inter', 14))
            expand_btn.pack(side='left', padx=5)
            card.expand_btn = expand_btn

            # Кнопка удаления
            delete_btn = ctk.CTkButton(header_frame, text="❌", width=32, height=32,
                                       command=lambda sid=sid: self.delete_session(sid),
                                       font=('Inter', 14))
            delete_btn.pack(side='right', padx=5)            
            
            # Кнопка открытия папки с данными
            folder_btn = ctk.CTkButton(header_frame, text="📂", width=32, height=32,
                                       command=self.open_data_folder,
                                       font=('Inter', 14))
            folder_btn.pack(side='right', padx=5)

            # Превью (первые 100 символов)
            preview = display_text[:100] + "..." if len(display_text) > 100 else display_text
            preview_label = ctk.CTkLabel(card, text=preview, font=('Inter', 11), wraplength=600, justify='left', anchor='w')
            preview_label.pack(fill='x', padx=8, pady=(4, 4))
            card.preview_label = preview_label

            # Контейнер для развёрнутого текста
            expand_frame = ctk.CTkFrame(card, fg_color="transparent")
            expand_frame.pack(fill='x', padx=8, pady=(4, 4))
            expand_frame.pack_forget()
            card.expand_frame = expand_frame

            # Полный текст (итоги)
            full_textbox = ctk.CTkTextbox(expand_frame, wrap='word', font=('Inter', 11), height=150)
            full_textbox.pack(fill='both', expand=True)
            full_textbox.insert('0.0', display_text)
            full_textbox.configure(state='disabled')
            card.full_textbox = full_textbox
            card.expanded = False

        # Восстанавливаем позицию скролла
        if scroll_pos is not None:
            self.scroll_frame._parent_canvas.yview_moveto(scroll_pos[0])

    def toggle_expand(self, session_id, card):
        if card.expanded:
            card.expand_frame.pack_forget()
            card.preview_label.pack(fill='x', padx=8, pady=(4, 4))
            card.expand_btn.configure(text="▷")
            card.expanded = False
        else:
            card.preview_label.pack_forget()
            card.expand_frame.pack(fill='x', padx=8, pady=(4, 4))
            card.expand_btn.configure(text="▽")
            card.expanded = True
    
    # Получаем итоги
    def copy_summary(self, session_id):
        sessions = get_all_sessions()
        text = ""
        for s in sessions:
            if s[0] == session_id:
                text = s[5] if s[5] and s[5].strip() else s[4]
                break
        if text:
            root = self.winfo_toplevel()
            root.clipboard_clear()
            root.clipboard_append(text)
            self.on_status("Текст скопирован в буфер", "active")
        else:
            self.on_status("Нет текста для копирования", "info")

    def delete_session(self, session_id):
        if messagebox.askyesno("Удаление", "Удалить эту запись навсегда?"):
            delete_session(session_id)
            for card in self.scroll_frame.winfo_children():
                if hasattr(card, 'session_id') and card.session_id == session_id:
                    card.destroy()
                    break
            self.on_status("Запись удалена", "active")
            if len(self.scroll_frame.winfo_children()) == 0:
                no_data = ctk.CTkLabel(self.scroll_frame, text="Нет сохранённых записей", font=('Inter', 14))
                no_data.pack(pady=20)
    
    # Открываем папку data в проводнике
    def open_data_folder(self):
        data_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        if os.path.exists(data_folder):
            subprocess.Popen(f'explorer "{data_folder}"')
        else:
            self.on_status("Папка data не найдена", "error")