#Funções auxiliares genéricas

# -*- coding: utf-8 -*-
import os
import sys
import re
import hashlib
import threading
from tkinter import messagebox

import config

# --- Funções de Caminho e Diretório ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()
DB_FILE_PATH = os.path.join(BASE_PATH, config.DB_FILENAME)

def get_resource_path(relative_path):
    return os.path.join(BASE_PATH, relative_path)

def ensure_core_directories_and_files_exist():
    print("[SETUP] Verificando diretórios e arquivos...")
    os.makedirs(os.path.join(BASE_PATH, config.USER_DATA_ROOT_FOLDER), exist_ok=True)
    os.makedirs(get_resource_path(config.DSC_SUBFOLDER_FONTS), exist_ok=True)
    if not os.path.exists(DB_FILE_PATH):
        try:
            with open(DB_FILE_PATH, 'w', encoding='utf-8') as f:
                pass
            print(f"[SETUP_INFO] '{config.DB_FILENAME}' criado.")
        except IOError as e:
            print(f"[SETUP_ERRO CRÍTICO] Não foi possível criar '{config.DB_FILENAME}': {e}")

def sanitize_username_for_path(username_email):
    if not username_email:
        return "default_user"
    return re.sub(r'[^\w.\-]', '_', username_email)

def get_user_specific_paths(user_email):
    sanitized_email = sanitize_username_for_path(user_email)
    user_data_dir = os.path.join(BASE_PATH, config.USER_DATA_ROOT_FOLDER, sanitized_email)
    user_faces_path = os.path.join(user_data_dir, config.DS_SUBFOLDER_FACES)
    user_info_file_path = os.path.join(user_data_dir, config.DS_INFO_FILENAME)
    
    os.makedirs(user_faces_path, exist_ok=True)
    
    if not os.path.exists(user_info_file_path):
        try:
            with open(user_info_file_path, 'w', encoding='utf-8') as f:
                f.write("# ID:Nome Completo,Sexo\n")
            print(f"[SETUP_INFO] Arquivo '{config.DS_INFO_FILENAME}' criado para '{sanitized_email}'.")
        except Exception as e:
            print(f"[SETUP_ERRO] Não foi possível criar '{config.DS_INFO_FILENAME}': {e}")
            
    return user_faces_path, user_info_file_path

# --- Funções de Senha ---
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(stored_password_hash, provided_password):
    return stored_password_hash == hash_password(provided_password)

def validate_password_rules(password_str):
    rules = {
        "length": 6 <= len(password_str) <= 16,
        "upper": bool(re.search(r"[A-Z]", password_str)),
        "lower": bool(re.search(r"[a-z]", password_str)),
        "digit": bool(re.search(r"[0-9]", password_str)),
        "special": bool(re.search(r"[@#$*!]", password_str))
    }
    all_met = all(rules.values())
    error_messages = []
    if not rules["length"]: error_messages.append("Senha: 6-16 caracteres.")
    if not rules["upper"]: error_messages.append("Senha: Letra maiúscula.")
    if not rules["lower"]: error_messages.append("Senha: Letra minúscula.")
    if not rules["digit"]: error_messages.append("Senha: Número.")
    if not rules["special"]: error_messages.append("Senha: Especial (@#$*!).")
    return all_met, rules, error_messages

# --- Funções de Thread ---
# Variáveis globais para controlar as threads
deepscan_thread = None

def run_function_in_thread(target_function, thread_var_name, func_name_msg, args_tuple=()):
    global deepscan_thread
    
    thread_obj = None
    if thread_var_name == "deepscan_thread":
        thread_obj = deepscan_thread

    if thread_obj and thread_obj.is_alive():
        messagebox.showwarning("Em Execução", f"'{func_name_msg}' já está em execução.")
        return

    new_thread = threading.Thread(target=target_function, args=args_tuple, daemon=True)
    
    if thread_var_name == "deepscan_thread":
        deepscan_thread = new_thread
        
    new_thread.start()