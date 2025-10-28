#Telas de Configurações e Idioma

# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox

import config

class SettingsFrame(ttk.Frame):
    def __init__(self, master_container, app_controller, *args, **kwargs):
        super().__init__(master_container, *args, **kwargs)
        self.app_controller = app_controller
        self.configure(style="Background.TFrame")
        
        self.title_label = ttk.Label(self, text="Configurações", style="Header.TLabel")
        self.title_label.pack(pady=(20, 20))

        self.profile_button = ttk.Button(self, text="Perfil", command=self.app_controller.show_profile_frame, style="Purple.TButton")
        self.profile_button.pack(fill=tk.X, pady=10, padx=50)
        
        self.language_button = ttk.Button(self, text="Idioma", command=self.app_controller.show_language_frame, style="Purple.TButton")
        self.language_button.pack(fill=tk.X, pady=10, padx=50)

        self.back_button = ttk.Button(self, text="Voltar para Deep", command=self.app_controller.show_main_content_frame, style="Purple.TButton")
        self.back_button.pack(fill=tk.X, pady=(20, 10), padx=50)

    def update_texts(self, texts):
        self.title_label.config(text=texts.get("settings_title", "Configurações"))
        self.profile_button.config(text=texts.get("profile_button", "Perfil"))
        self.language_button.config(text=texts.get("language_button", "Idioma"))
        self.back_button.config(text=texts.get("back_to_deep_button", "Voltar para Deep"))


class LanguageFrame(ttk.Frame):
    def __init__(self, master_container, app_controller, *args, **kwargs):
        super().__init__(master_container, *args, **kwargs)
        self.app_controller = app_controller
        self.configure(style="Background.TFrame")

        self.title_label = ttk.Label(self, text="Selecionar Idioma", style="Header.TLabel")
        self.title_label.pack(pady=(20, 20))
        
        self.lang_combobox = ttk.Combobox(self, textvariable=self.app_controller.selected_language, values=config.LANGUAGES, state="readonly", width=25)
        self.lang_combobox.pack(pady=10)
        
        self.save_button = ttk.Button(self, text="Salvar Idioma", command=self._apply_language, style="Purple.TButton")
        self.save_button.pack(pady=10)

        self.back_button = ttk.Button(self, text="Voltar para Configurações", command=self.app_controller.show_settings_frame, style="Purple.TButton")
        self.back_button.pack(pady=(20, 10))

    def _apply_language(self):
        self.app_controller.apply_language_change()
        messagebox.showinfo("Idioma", f"Idioma '{self.app_controller.selected_language.get()}' aplicado.", parent=self)

    def update_texts(self, texts):
        self.title_label.config(text=texts.get("language_select_title", "Selecionar Idioma"))
        self.save_button.config(text=texts.get("save_language_button", "Salvar Idioma"))
        self.back_button.config(text=texts.get("back_to_settings_button", "Voltar para Configurações"))