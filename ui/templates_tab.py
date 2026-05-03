import customtkinter as ctk
import subprocess
from core.templates import load_templates, save_template, delete_template, update_template
from core.paths import TEMPLATES_DIR
from tkinter import messagebox

class TemplatesTab(ctk.CTkFrame):
    def __init__(self, parent, on_status, recording_tab):
        super().__init__(parent)
        self.on_status = on_status
        self.recording_tab = recording_tab
        self.create_widgets()
        self.refresh()

    def create_widgets(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill='x', pady=(10, 5), padx=20)
        ctk.CTkLabel(header, text="Шаблоны итогов", font=('Inter', 18, 'bold')).pack(side='left')
        self.add_btn = ctk.CTkButton(header, text="+ Новый шаблон", command=self.add_new_template,
                                     width=150, height=30, font=('Inter', 13))
        self.add_btn.pack(side='right')
        self.refresh_btn = ctk.CTkButton(header, text="🔄", width=40, height=30,
                                         command=self.refresh, font=('Inter', 16))
        self.refresh_btn.pack(side='right', padx=5)

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill='both', expand=True, padx=20, pady=10)

    def refresh(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        templates = load_templates()
        if not templates:
            no_data = ctk.CTkLabel(self.scroll_frame, text="Нет шаблонов. Создайте первый.",
                                   font=('Inter', 14))
            no_data.pack(pady=20)
        else:
            for t in templates:
                self._create_template_card(t)
        self.recording_tab.refresh_templates_list()

    def _create_template_card(self, template, is_new=False):
        card = ctk.CTkFrame(self.scroll_frame, corner_radius=10, border_width=1, border_color="#017365")
        card.pack(fill='x', pady=4, padx=5)
        card.is_new = is_new

        name = template.get('name', '')
        prompt = template.get('prompt', '')

        # Верхняя строка
        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(fill='x', padx=8, pady=(6, 4))
        name_label = ctk.CTkLabel(header_frame, text=name if name else "Новый шаблон",
                                  font=('Inter', 14, 'bold'))
        name_label.pack(side='left')
        card.name_label = name_label

        # Кнопки
        if not is_new:
            delete_btn = ctk.CTkButton(header_frame, text="❌", width=28, height=28,
                                       command=lambda n=name: self.delete_template(n),
                                       font=('Inter', 10))
            delete_btn.pack(side='right', padx=5)
            
            edit_btn = ctk.CTkButton(header_frame, text="▷", width=28, height=28,
                                     command=lambda n=name, crd=card: self.toggle_edit(n, crd),
                                     font=('Inter', 14))
            edit_btn.pack(side='right', padx=5)
            card.edit_btn = edit_btn

        # Контейнер для формы редактирования
        edit_frame = ctk.CTkFrame(card, fg_color="transparent")
        edit_frame.pack(fill='x', padx=8, pady=(0, 4))
        edit_frame.pack_forget()
        card.edit_frame = edit_frame

        ctk.CTkLabel(edit_frame, text="Название:", font=('Inter', 12)).pack(anchor='w', pady=(5,0))
        name_entry = ctk.CTkEntry(edit_frame, width=400, font=('Inter', 13))
        name_entry.insert(0, name)
        name_entry.pack(fill='x', pady=5)

        ctk.CTkLabel(edit_frame, text="Укажите ваш промпт", font=('Inter', 12)).pack(anchor='w')
        prompt_text = ctk.CTkTextbox(edit_frame, height=150, font=('Inter', 13))
        prompt_text.insert('0.0', prompt)
        prompt_text.pack(fill='x', pady=5)

        btn_frame = ctk.CTkFrame(edit_frame, fg_color="transparent")
        btn_frame.pack(fill='x', pady=5)
        save_btn = ctk.CTkButton(btn_frame, text="Сохранить", width=100,
                                 command=lambda n=name, crd=card, ne=name_entry, pt=prompt_text, new=is_new: self.save_edit(n, crd, ne, pt, new))
        save_btn.pack(side='left', padx=5)
        cancel_btn = ctk.CTkButton(btn_frame, text="Отмена", width=100,
                                   command=lambda crd=card: self.cancel_edit(crd))
        cancel_btn.pack(side='left', padx=5)

        card.name_entry = name_entry
        card.prompt_text = prompt_text
        card.editing = False

        if is_new:
            self._expand_edit(card, new_mode=True)

    def _expand_edit(self, card, new_mode=False):
        if hasattr(card, 'edit_btn'):
            card.edit_btn.configure(text="▽")
        card.edit_frame.pack(fill='x', padx=8, pady=(4, 4))
        card.editing = True
        if new_mode:
            card.name_label.configure(text="Новый шаблон")

    def toggle_edit(self, name, card):
        if card.editing:
            self.cancel_edit(card)
        else:
            self._expand_edit(card)

    def cancel_edit(self, card):
        # Если это карточка нового (не сохранённого) шаблона – удаляем её полностью
        if getattr(card, 'is_new', False):
            card.destroy()
            if len(self.scroll_frame.winfo_children()) == 0:
                no_data = ctk.CTkLabel(self.scroll_frame, text="Нет шаблонов. Создайте первый.",
                                       font=('Inter', 14))
                no_data.pack(pady=20)
            return

        card.edit_frame.pack_forget()
        if hasattr(card, 'edit_btn'):
            card.edit_btn.configure(text="▷")
        card.editing = False

    def save_edit(self, old_name, card, name_entry, prompt_text, is_new=False):
        new_name = name_entry.get().strip()
        new_prompt = prompt_text.get('0.0', 'end').strip()
        if not new_name:
            messagebox.showerror("Ошибка", "Название не может быть пустым")
            return
        if not new_prompt:
            messagebox.showerror("Ошибка", "Текст промпта не может быть пустым")
            return
        if is_new:
            # Создаём новый шаблон
            save_template({"name": new_name, "prompt": new_prompt})
            self.on_status(f"Шаблон '{new_name}' сохранён", "active")
            self.refresh()
        else:
            # Обновляем существующий
            update_template(old_name, {"name": new_name, "prompt": new_prompt})
            self.on_status(f"Шаблон '{new_name}' обновлён", "active")
            self.refresh()

    def add_new_template(self):
        self._create_template_card({"name": "", "prompt": ""}, is_new=True)
        self.scroll_frame._parent_canvas.yview_moveto(1.0)

    def delete_template(self, name):
        if messagebox.askyesno("Удаление", f"Удалить шаблон '{name}'?\n\nЕсли удаление не удаётся, откройте папку и удалите файл вручную."):
            result = delete_template(name)
            if result:
                self.refresh()
                self.on_status(f"Шаблон '{name}' удалён", "active")
            else:
                subprocess.Popen(f'explorer "{TEMPLATES_DIR}"')
                self.on_status(f"Не удалось удалить автоматически. Откройте папку и удалите файл '{name}.json' вручную.", "error")