#Tela de Perfil do Usuário

# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date

import config
import utils

class ProfileFrame(ttk.Frame):
    def __init__(self, master_container, app_controller, user_data, *args, **kwargs):
        super().__init__(master_container, *args, **kwargs)
        self.app_controller = app_controller
        self.user_data = user_data
        self.configure(style="Background.TFrame")
        
        self._create_widgets()

    def _create_widgets(self):
        back_button = ttk.Button(self, text="Voltar para Configurações", command=self.app_controller.show_settings_frame, style="Purple.TButton")
        back_button.pack(pady=10, padx=10, anchor="nw")
        
        main_frame = ttk.Frame(self, padding="20", style="Background.TFrame")
        main_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(main_frame, text="Informações do Usuário", style="Header.TLabel").pack(pady=(0, 15))
        
        # Calcula a idade
        age_display = "N/A"
        dob_str = self.user_data.get("dob")
        if dob_str:
            try:
                birth_date = datetime.strptime(dob_str, "%d/%m/%Y").date()
                today = date.today()
                age_display = str(today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day)))
            except ValueError:
                age_display = "Data Inválida"

        # Exibe as informações
        info_map = {
            "Nome Completo:": self.user_data.get("fullname", "N/A"),
            "Empresa:": self.user_data.get("company", "N/A"),
            "Cargo:": self.user_data.get("position", "N/A"),
            "Email:": self.user_data.get("email", "N/A"),
            "Data de Nascimento:": dob_str,
            "Idade:": age_display
        }
        
        for label_text, value in info_map.items():
            row = ttk.Frame(main_frame, style="Background.TFrame")
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=label_text, style="TLabel", font=('Helvetica', 10, 'bold'), width=18, anchor="w").pack(side=tk.LEFT)
            ttk.Label(row, text=value, style="TLabel", font=('Helvetica', 10), wraplength=250).pack(side=tk.LEFT, expand=True, fill=tk.X)

        logout_button = ttk.Button(main_frame, text="Logout", command=self.app_controller.handle_logout, style="Purple.TButton")
        logout_button.pack(fill=tk.X, pady=(20, 5))