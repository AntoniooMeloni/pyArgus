#Janela principal que gerencia as telas

# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import os

import config
import utils
from core import deepscan_logic, deepsave_logic
from gui.profile_frame import ProfileFrame
from gui.settings_frames import SettingsFrame, LanguageFrame
from services.language_service import LanguageService

# --- Tela DeepSave (movida para cá por ser um Frame da Janela Principal) ---
class DeepSaveFrame(ttk.Frame):
    def __init__(self, master_container, app_controller, *args, **kwargs):
        super().__init__(master_container, *args, **kwargs)
        self.app_controller = app_controller
        self.user_email = app_controller.user_email
        self.configure(bg=config.BACKGROUND_COLOR) # Fundo #0a0a0a

        # Estilos específicos para esta tela
        style = ttk.Style(self)
        style.configure("DeepSave.TLabel", background=config.BACKGROUND_COLOR, foreground=config.TEXT_COLOR, font=('Helvetica', 12))
        style.configure("DeepSave.Header.TLabel", background=config.BACKGROUND_COLOR, foreground=config.TEXT_COLOR, font=('Helvetica', 16, 'bold'))
        style.configure("DeepSave.TRadiobutton", background=config.BACKGROUND_COLOR, foreground=config.TEXT_COLOR)
        style.configure("DeepSave.TButton", foreground=config.BACKGROUND_COLOR, background=config.PROFILE_ENTRY_BG_COLOR, font=('Helvetica', 10, 'bold'))
        
        self.user_faces_path, self.user_info_path = utils.get_user_specific_paths(self.user_email)
        self.haar_cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
        
        self._create_widgets()
        self._reset_form()

    def _create_widgets(self):
        back_button = ttk.Button(self, text="Voltar para Deep", command=self.app_controller.show_main_content_frame, style="DeepSave.TButton")
        back_button.pack(pady=10, padx=10, anchor="nw")

        main_frame = ttk.Frame(self, padding="15", style="DeepSave.TFrame")
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        ttk.Label(main_frame, text="Deep Save - Cadastro de Rosto", style="DeepSave.Header.TLabel").pack(pady=(0, 20))
        
        ttk.Label(main_frame, text="Nome Completo:", style="DeepSave.TLabel").pack(anchor="w")
        self.fullname_entry = tk.Entry(main_frame, width=50, font=('Helvetica', 10), bg=config.PROFILE_ENTRY_BG_COLOR, fg=config.TEXT_COLOR, insertbackground=config.TEXT_COLOR)
        self.fullname_entry.pack(fill=tk.X, pady=(0,10), ipady=4)
        
        sex_frame = ttk.Frame(main_frame, style="DeepSave.TFrame")
        sex_frame.pack(fill=tk.X, pady=(0,10))
        ttk.Label(sex_frame, text="Sexo:", style="DeepSave.TLabel").pack(side=tk.LEFT, padx=(0,10))
        self.sex_var = tk.StringVar(value=None) # Inicia sem valor
        ttk.Radiobutton(sex_frame, text="Masculino", variable=self.sex_var, value="Masculino", style="DeepSave.TRadiobutton").pack(side=tk.LEFT)
        ttk.Radiobutton(sex_frame, text="Feminino", variable=self.sex_var, value="Feminino", style="DeepSave.TRadiobutton").pack(side=tk.LEFT)

        self.save_button = ttk.Button(main_frame, text="Salvar e Iniciar Captura", command=self._save_and_capture, style="DeepSave.TButton")
        self.save_button.pack(fill=tk.X, pady=10)

        self.clear_button = ttk.Button(main_frame, text="Limpar Formulário", command=self._reset_form, style="DeepSave.TButton")
        self.clear_button.pack(fill=tk.X, pady=5)

    def _reset_form(self):
        self.fullname_entry.delete(0, tk.END)
        self.sex_var.set(None) # Desseleciona os botões de rádio
        print("[DS_GUI] Formulário limpo.")

    def _save_and_capture(self):
        fullname = self.fullname_entry.get().strip()
        sex = self.sex_var.get()

        if not fullname:
            messagebox.showerror("Campo Obrigatório", "O Nome Completo é obrigatório.", parent=self)
            return
        if not sex or sex == 'None':
            messagebox.showerror("Campo Obrigatório", "A seleção de 'Sexo' é obrigatória.", parent=self)
            return

        person_id = deepsave_logic.get_next_person_id(self.user_faces_path)
        
        if not deepsave_logic.add_person_info(person_id, fullname, sex, self.user_info_path):
            messagebox.showerror("Erro ao Salvar", "Não foi possível salvar as informações textuais.", parent=self)
            return

        messagebox.showinfo("Informações Salvas", f"Informações de '{fullname}' salvas. A câmera será aberta para a captura da primeira foto.", parent=self)

        # Captura a primeira foto
        filename = deepsave_logic.generate_photo_filename(person_id, 0)
        full_path = os.path.join(self.user_faces_path, filename)
        
        # Executa a captura em uma thread para não travar a GUI
        def capture_task():
            success, error_code = deepsave_logic.capture_and_save_face(full_path, self.haar_cascade_path)
            if success:
                self.after(0, lambda: messagebox.showinfo("Sucesso", "Foto capturada e salva com sucesso!", parent=self))
                self.after(0, self._reset_form)
            else:
                if error_code == "camera_error":
                    self.after(0, lambda: messagebox.showerror("Erro de Câmera", "Não foi possível acessar a câmera.", parent=self))
                else:
                    self.after(0, lambda: messagebox.showerror("Falha na Captura", "Não foi possível salvar a foto.", parent=self))
        
        utils.run_function_in_thread(capture_task, "deepsave_thread", "Deep Save")


# --- Tela Principal (Conteúdo) ---
class MainContentFrame(ttk.Frame):
    def __init__(self, master_container, app_controller, *args, **kwargs):
        super().__init__(master_container, *args, **kwargs)
        self.app_controller = app_controller
        self.user_data = app_controller.user_data
        self.configure(style="Background.TFrame")
        
        top_bar = ttk.Frame(self, style="Background.TFrame")
        top_bar.pack(fill=tk.X, pady=(5,0), padx=10)
        
        self.welcome_label = ttk.Label(top_bar, text=f"Bem-vindo, {self.user_data.get('fullname', 'Usuário')}!", style="TLabel", font=('Helvetica', 12, 'italic'))
        self.welcome_label.pack(side=tk.LEFT, padx=10)
        
        self.settings_button = ttk.Button(top_bar, text="Configurações", command=self.app_controller.show_settings_frame, style="Purple.TButton")
        self.settings_button.pack(side=tk.RIGHT, padx=10)
        
        buttons_frame = ttk.Frame(self, padding="20", style="Background.TFrame")
        buttons_frame.pack(expand=True, fill=tk.BOTH)
        
        ttk.Button(buttons_frame, text="Deep Save", command=self.app_controller.show_deepsave_frame, style="Purple.TButton").pack(pady=10, fill=tk.X)
        ttk.Button(buttons_frame, text="Deep Scan", command=self.app_controller.start_deepscan, style="Purple.TButton").pack(pady=10, fill=tk.X)

# --- Janela Principal ---
class DeepMainWindow(tk.Tk):
    def __init__(self, login_app_instance, user_data, initial_language, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_app_instance = login_app_instance
        self.user_data = user_data
        self.user_email = self.user_data.get("email")
        
        # API e Idioma
        # COLOQUE SUA CHAVE DE API AQUI
        self.api_key = "AIzaSyBTBErMdy3ppMyVWpi7zmifbKh3c9OegjY" 
        self.language_service = LanguageService(self.api_key)
        self.selected_language = tk.StringVar(value=initial_language)
        self.ui_texts = config.UI_TEXTS.copy() # Carrega textos padrão

        self.title("Deep")
        self.config(bg=config.BACKGROUND_COLOR)
        self.protocol("WM_DELETE_WINDOW", self.handle_logout)
        
        self.container = ttk.Frame(self, style="Background.TFrame")
        self.container.pack(expand=True, fill=tk.BOTH)
        
        self.frames = {}
        self._create_frames()
        
        self.show_main_content_frame()

    def _create_frames(self):
        for F in (MainContentFrame, DeepSaveFrame, SettingsFrame, LanguageFrame, ProfileFrame):
            page_name = F.__name__
            if page_name == "ProfileFrame":
                frame = F(self.container, self, self.user_data)
            else:
                frame = F(self.container, self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

    def _show_frame(self, page_name, geometry):
        self.geometry(geometry)
        frame = self.frames[page_name]
        # Atualiza textos se o frame tiver o método update_texts
        if hasattr(frame, 'update_texts'):
            frame.update_texts(self.ui_texts)
        frame.tkraise()

    def show_main_content_frame(self): self._show_frame("MainContentFrame", "400x300")
    def show_deepsave_frame(self): self._show_frame("DeepSaveFrame", "500x450")
    def show_settings_frame(self): self._show_frame("SettingsFrame", "400x300")
    def show_language_frame(self): self._show_frame("LanguageFrame", "400x300")
    def show_profile_frame(self): self._show_frame("ProfileFrame", "450x480")

    def start_deepscan(self):
        if not self.user_email:
            messagebox.showerror("Erro", "Email do usuário não encontrado.", parent=self)
            return
        messagebox.showinfo("Deep Scan", "Iniciando reconhecimento.\nUma nova janela será aberta.", parent=self)
        utils.run_function_in_thread(deepscan_logic.execute_recognition_session, "deepscan_thread", "Deep Scan", args_tuple=(self.user_email,))

    def apply_language_change(self):
        lang_name = self.selected_language.get()
        if lang_name == "Português":
            self.ui_texts = config.UI_TEXTS.copy()
        else:
            lang_code = config.LANGUAGE_MAP.get(lang_name)
            if lang_code and self.language_service.is_configured:
                translated = self.language_service.translate_ui_texts(config.UI_TEXTS, lang_code)
                if translated:
                    self.ui_texts = translated
        
        # Atualiza o frame visível no momento
        for frame in self.frames.values():
            if frame.winfo_ismapped():
                if hasattr(frame, 'update_texts'):
                    frame.update_texts(self.ui_texts)
                break

    def handle_logout(self):
        if messagebox.askokcancel("Sair", "Deseja fechar e fazer logout?", parent=self):
            self.destroy()
            if self.login_app_instance:
                try:
                    self.login_app_instance.deiconify()
                except tk.TclError:
                    pass