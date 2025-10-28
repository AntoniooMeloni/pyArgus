#Tela de Login e Cadastro

# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import re
import os

import config
import utils

class LoginApp(tk.Tk):
    def __init__(self, launch_callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.launch_callback = launch_callback
        self.title("Login Deep")
        self.config(bg=config.BACKGROUND_COLOR)
        
        # Variáveis de controle
        self.show_login_password_var = tk.BooleanVar()
        self.show_reg_password_var = tk.BooleanVar()
        self.show_reg_confirm_password_var = tk.BooleanVar()
        self.selected_language = tk.StringVar(value=config.DEFAULT_LANGUAGE)
        
        self._configure_styles()
        
        # Frames principais
        self.login_frame = ttk.Frame(self, padding="20", style="TFrame")
        self.register_frame = ttk.Frame(self, padding="15", style="TFrame")
        
        self._setup_login_frame()
        self._setup_register_frame()
        
        self._show_login_frame()

    def _configure_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure("TFrame", background=config.BACKGROUND_COLOR)
        self.style.configure("TLabel", foreground=config.TEXT_COLOR, background=config.BACKGROUND_COLOR, padding=5, font=('Helvetica', 10))
        self.style.configure("Header.TLabel", foreground=config.TEXT_COLOR, background=config.BACKGROUND_COLOR, font=('Helvetica', 14, 'bold'))
        self.style.configure("Small.TLabel", foreground=config.TEXT_COLOR, background=config.BACKGROUND_COLOR, font=('Helvetica', 8))
        self.style.configure("Error.TLabel", foreground=config.TEXT_ERROR_COLOR, background=config.BACKGROUND_COLOR, font=('Helvetica', 8, 'bold'))
        self.style.configure("Purple.TButton", foreground=config.TEXT_COLOR, background=config.BUTTON_BG_COLOR, bordercolor=config.TEXT_COLOR, font=('Helvetica', 10, 'bold'), padding=8)
        self.style.map("Purple.TButton", background=[('active', config.ENTRY_BG_COLOR)], foreground=[('active', config.BUTTON_BG_COLOR)])
        self.style.configure("Purple.TCheckbutton", foreground=config.TEXT_COLOR, background=config.BACKGROUND_COLOR, indicatorcolor=config.TEXT_COLOR, font=('Helvetica', 9))
        self.style.map("Purple.TCheckbutton", indicatorcolor=[('selected', config.TEXT_COLOR)], background=[('active', config.BACKGROUND_COLOR)])
        self.style.configure("TCombobox", fieldbackground=config.ENTRY_BG_COLOR, background=config.ENTRY_BG_COLOR, foreground=config.TEXT_COLOR, arrowcolor=config.TEXT_COLOR, selectbackground=config.ENTRY_BG_COLOR, selectforeground=config.TEXT_COLOR)

    def _set_entry_style(self, entry_widget, style_type="default"):
        # Simplificado para focar na estrutura
        if style_type == "error":
            entry_widget.config(bg="pink")
        else:
            entry_widget.config(bg=config.ENTRY_BG_COLOR)

    def _show_login_frame(self):
        self.register_frame.pack_forget()
        self.login_frame.pack(expand=True, fill=tk.BOTH)
        self.title("Login Deep")
        self.geometry("400x380")

    def _show_register_frame(self):
        self.login_frame.pack_forget()
        self.register_frame.pack(expand=True, fill=tk.BOTH)
        self.title("myDeep Account")
        self.geometry("450x750")

    def _setup_login_frame(self):
        # ... (A estrutura dos widgets é mantida, mas as chamadas são atualizadas)
        ttk.Label(self.login_frame, text="DEEP GUARD", style="Header.TLabel").pack(pady=(0, 10))
        
        ttk.Label(self.login_frame, text="Email:", style="TLabel").pack(fill=tk.X)
        self.login_email_entry = tk.Entry(self.login_frame, width=40, font=('Helvetica', 10), bg=config.ENTRY_BG_COLOR, fg=config.TEXT_COLOR, insertbackground=config.TEXT_COLOR)
        self.login_email_entry.pack(fill=tk.X, pady=(0,10), ipady=4)
        
        ttk.Label(self.login_frame, text="Senha:", style="TLabel").pack(fill=tk.X)
        self.login_password_entry = tk.Entry(self.login_frame, show="*", width=40, font=('Helvetica', 10), bg=config.ENTRY_BG_COLOR, fg=config.TEXT_COLOR, insertbackground=config.TEXT_COLOR)
        self.login_password_entry.pack(fill=tk.X, pady=(0,5), ipady=4)
        
        ttk.Checkbutton(self.login_frame, text="Mostrar Senha", variable=self.show_login_password_var, command=lambda: self.login_password_entry.config(show="" if self.show_login_password_var.get() else "*"), style="Purple.TCheckbutton").pack(anchor=tk.W)
        
        ttk.Button(self.login_frame, text="Login", command=self._handle_login, style="Purple.TButton").pack(fill=tk.X, pady=5)
        ttk.Button(self.login_frame, text="Criar nova conta", command=self._show_register_frame, style="Purple.TButton").pack(fill=tk.X, pady=5)

    def _setup_register_frame(self):
        # ... (A estrutura dos widgets é mantida)
        top_reg = ttk.Frame(self.register_frame, style="TFrame")
        top_reg.pack(fill=tk.X, pady=(0,5))
        ttk.Label(top_reg, text="myDEEP Account", style="Header.TLabel").pack(side=tk.LEFT, expand=True, anchor="center")
        ttk.Button(top_reg, text="Voltar", command=self._show_login_frame, style="Purple.TButton", width=8).pack(side=tk.RIGHT)

        # Campos de entrada
        self.reg_fields = {}
        field_labels = ["Nome Completo:", "Empresa:", "Cargo:", "Email:", "Data de Nascimento (DD/MM/AAAA):", "Senha:", "Confirmar Senha:"]
        for label_text in field_labels:
            ttk.Label(self.register_frame, text=label_text, style="TLabel").pack(fill=tk.X, anchor='w')
            entry = tk.Entry(self.register_frame, width=38, font=('Helvetica', 10), bg=config.ENTRY_BG_COLOR, fg=config.TEXT_COLOR, insertbackground=config.TEXT_COLOR)
            if "Senha" in label_text:
                entry.config(show="*")
            entry.pack(fill=tk.X, ipady=4, pady=(0,5))
            self.reg_fields[label_text] = entry
        
        ttk.Button(self.register_frame, text="Criar Conta", command=self._handle_register, style="Purple.TButton").pack(fill=tk.X, pady=(15,5))

    def _handle_login(self):
        email = self.login_email_entry.get().strip()
        password = self.login_password_entry.get()

        if not email or not password:
            messagebox.showerror("Erro Login", "Email e senha são obrigatórios.", parent=self)
            return

        try:
            user_data = None
            if not os.path.exists(utils.DB_FILE_PATH):
                messagebox.showerror("Erro Login", "Nenhum usuário cadastrado.", parent=self)
                return

            with open(utils.DB_FILE_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('|')
                    if len(parts) == len(config.USER_DATA_FIELDS):
                        current_user = dict(zip(config.USER_DATA_FIELDS, parts))
                        if current_user["email"] == email:
                            if utils.verify_password(current_user["hashed_password"], password):
                                user_data = current_user
                                break
                            else:
                                messagebox.showerror("Erro Login", "Email ou senha incorretos.", parent=self)
                                return
            
            if user_data:
                self.withdraw() # Esconde a janela de login
                self.launch_callback(self, user_data, self.selected_language.get())
            else:
                messagebox.showerror("Erro Login", "Email ou senha incorretos.", parent=self)

        except Exception as e:
            messagebox.showerror("Erro Login", f"Ocorreu um erro: {e}", parent=self)

    def _handle_register(self):
        # Lógica de validação e registro simplificada para focar na estrutura
        data = {k.replace(":", "").replace(" (DD/MM/AAAA)", "").replace(" ", "_").lower(): v.get().strip() for k, v in self.reg_fields.items()}
        
        # Validação básica
        if any(not v for v in data.values()):
            messagebox.showerror("Erro Cadastro", "Todos os campos são obrigatórios.", parent=self)
            return
        
        is_pw_valid, _, pw_errs = utils.validate_password_rules(data['senha'])
        if not is_pw_valid:
            messagebox.showerror("Erro Cadastro", "Senha inválida:\n" + "\n".join(pw_errs), parent=self)
            return
            
        if data['senha'] != data['confirmar_senha']:
            messagebox.showerror("Erro Cadastro", "As senhas não coincidem.", parent=self)
            return

        # Salvar no arquivo
        try:
            new_user_line = "|".join([
                data["email"], 
                utils.hash_password(data["senha"]), 
                data["nome_completo"], 
                data["empresa"], 
                data["cargo"], 
                data["data_de_nascimento"]
            ]) + "\n"
            
            with open(utils.DB_FILE_PATH, 'a', encoding='utf-8') as f:
                f.write(new_user_line)
                
            messagebox.showinfo("Cadastro Sucesso", "Conta criada com sucesso! Agora você pode fazer login.", parent=self)
            self._show_login_frame()

        except Exception as e:
            messagebox.showerror("Erro Cadastro", f"Erro ao salvar dados: {e}", parent=self)