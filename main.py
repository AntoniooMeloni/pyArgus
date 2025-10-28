#Ponto de entrada principal da aplicação

# -*- coding: utf-8 -*-
import tkinter as tk
from gui.login_window import LoginApp
from gui.main_window import DeepMainWindow
import utils

# Função de callback que a janela de login chama quando o login é bem-sucedido
def launch_deep_main_window(login_app_instance, user_data, selected_language):
    # Esconde a janela de login em vez de destruí-la, para poder reabri-la no logout
    login_app_instance.withdraw()
    
    # Cria e executa a janela principal da aplicação
    deep_app = DeepMainWindow(login_app_instance, user_data, selected_language)
    deep_app.mainloop()

# Ponto de entrada do script
if __name__ == "__main__":
    # 1. Garante que as pastas e arquivos essenciais existam
    utils.ensure_core_directories_and_files_exist()
    
    # 2. Cria e inicia a janela de login, passando a função de callback
    login_app = LoginApp(launch_callback=launch_deep_main_window)
    
    # 3. Inicia o loop principal do Tkinter para a janela de login
    login_app.mainloop()