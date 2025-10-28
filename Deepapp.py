# -*- coding: utf-8 -*-
import cv2
import os
import time
import re
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import threading
import subprocess
import shutil
import hashlib
import tkinter.font as tkFont
from datetime import datetime, date

# Tenta importar DeepFace e PIL
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False
    print("[AVISO GLOBAL] DeepFace não está instalado. Funcionalidades do DeepScan serão limitadas.")
    class DeepFacePlaceholder:
        def build_model(self, *args, **kwargs): pass
        def represent(self, *args, **kwargs): return []
        def extract_faces(self, *args, **kwargs): return []
        def verify(self, *args, **kwargs): return {'distance': float('inf')}
    DeepFace = DeepFacePlaceholder()


PIL_AVAILABLE = False
PIL_Image = None
PIL_ImageDraw = None
PIL_ImageFont = None
PIL_ImageTk = None
try:
    from PIL import Image as PIL_Image_Import, ImageDraw as PIL_ImageDraw_Import, ImageFont as PIL_ImageFont_Import, ImageTk as PIL_ImageTk_Import
    PIL_AVAILABLE = True
    PIL_Image = PIL_Image_Import
    PIL_ImageDraw = PIL_ImageDraw_Import
    PIL_ImageFont = PIL_ImageFont_Import
    PIL_ImageTk = PIL_ImageTk_Import
    print("[INFO GLOBAL] Pillow (PIL) está instalada.")
except ImportError:
    print("[AVISO GLOBAL] Pillow (PIL) não está instalada. Suporte a caracteres especiais (acentos) no DeepScan pode ser limitado.")

# --- Funções Auxiliares Globais ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()

def get_resource_path(relative_path):
    return os.path.join(BASE_PATH, relative_path)

# --- Constantes de Cores ---
BACKGROUND_COLOR = "#0A0A0A"
TEXT_COLOR = "#6600EB"
ENTRY_BG_COLOR = "#181818" # Usado no Login/Registro
BUTTON_BG_COLOR = "#FFFFFF"
PROFILE_ENTRY_BG_COLOR = "#FAFAFA" # Nova cor para caixas de texto em Perfil
PROFILE_ENTRY_FG_COLOR = "#181818" # Cor do texto para caixas de texto em Perfil

# --- Constantes para o sistema de Login ---
DB_FILENAME = "cadastros.txt"
DB_FILE_PATH = os.path.join(BASE_PATH, DB_FILENAME)
USER_DATA_FIELDS = ["email", "hashed_password", "fullname", "company", "position", "dob"]

# --- Constantes Globais de Pastas e Nomes de Arquivo Base ---
USER_DATA_ROOT_FOLDER = "UserData"
DS_NOME_SUBPASTA_ROSTOS = "Rostos"
DSC_SUBPASTA_FONTES = "Fontes"
DS_PATH_ARQUIVO_INFOS_NOME = 'inforos.txt'


# --- Variáveis de controle de thread ---
deepsave_thread = None
deepscan_thread = None

# --- Constantes de Idioma ---
LANGUAGES = sorted(["Português", "Inglês", "Alemão", "Espanhol", "Francês", "Italiano", "Holandês"])
DEFAULT_LANGUAGE = "Português"

#===============================================================================
# INÍCIO DAS FUNÇÕES AUXILIARES PARA DADOS DE USUÁRIO
#===============================================================================
def sanitize_username_for_path(username_email):
    if not username_email:
        return "default_user"
    sanitized = re.sub(r'[^\w.\-]', '_', username_email)
    return sanitized

def get_user_specific_paths(user_email):
    sanitized_email_for_folder = sanitize_username_for_path(user_email)
    user_data_dir = os.path.join(BASE_PATH, USER_DATA_ROOT_FOLDER, sanitized_email_for_folder)
    user_rostos_path = os.path.join(user_data_dir, DS_NOME_SUBPASTA_ROSTOS)
    user_inforos_path = os.path.join(user_data_dir, DS_PATH_ARQUIVO_INFOS_NOME)
    os.makedirs(user_rostos_path, exist_ok=True)
    if not os.path.exists(user_inforos_path):
        try:
            with open(user_inforos_path, 'w', encoding='utf-8') as f:
                f.write("# ID:Nome Completo,Sexo\n")
            print(f"[SETUP_INFO] Arquivo '{DS_PATH_ARQUIVO_INFOS_NOME}' criado para usuário '{sanitized_email_for_folder}'.")
        except Exception as e:
            print(f"[SETUP_ERRO] Não foi possível criar '{DS_PATH_ARQUIVO_INFOS_NOME}' para '{sanitized_email_for_folder}': {e}")
    return user_rostos_path, user_inforos_path
#===============================================================================
# FIM DAS FUNÇÕES AUXILIARES PARA DADOS DE USUÁRIO
#===============================================================================

#===============================================================================
# INÍCIO DAS FUNÇÕES AUXILIARES PARA LOGIN E SENHA
#===============================================================================
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(stored_password_hash, provided_password):
    return stored_password_hash == hash_password(provided_password)

def validate_password_rules_static(password_str):
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
#===============================================================================
# FIM DAS FUNÇÕES AUXILIARES PARA LOGIN E SENHA
#===============================================================================

#===============================================================================
# INÍCIO DO CÓDIGO DO DEEPSAVE.PY (Funções Core)
#===============================================================================
DS_FONTE_TEXTO = cv2.FONT_HERSHEY_SIMPLEX
DS_COR_TEXTO_INFO = (0, 255, 0)
DS_COR_TEXTO_ALERTA = (0, 0, 255)
DS_COR_TEXTO_CONTADOR = (0, 165, 255)
DS_COR_TEXTO_SAIR_MSG = (255, 255, 255)
DS_COR_RETANGULO_CAPTURA = (102, 0, 235)
DS_NOME_JANELA_CAPTURA = "Deep Save"
DS_MAX_FOTOS_POR_PESSOA = 5
DS_ESCALA_FONTE_SAIR_MSG = 0.4
DS_ESPESSURA_TEXTO_SAIR_MSG = 1

def ds_obter_proximo_id_pessoa_base_interno(path_rostos_conhecidos_usuario):
    if not os.path.exists(path_rostos_conhecidos_usuario):
        os.makedirs(path_rostos_conhecidos_usuario, exist_ok=True)
        return "001"
    arquivos_jpg = [f for f in os.listdir(path_rostos_conhecidos_usuario) if f.lower().endswith((".jpg", ".jpeg"))]
    if not arquivos_jpg: return "001"
    pattern = re.compile(r"^(\d{3})")
    ids_numericos = set()
    for nome_arquivo in arquivos_jpg:
        match = pattern.match(nome_arquivo)
        if match and re.fullmatch(r"\d{3}(?: \(\d+\))?\.jpe?g$", nome_arquivo, re.IGNORECASE):
            ids_numericos.add(int(match.group(1)))
    if not ids_numericos: return "001"
    return f"{max(ids_numericos) + 1:03d}"

def ds_gerar_nome_arquivo_foto_interno(id_pessoa_base, indice_foto):
    return f"{id_pessoa_base}.jpg" if indice_foto == 0 else f"{id_pessoa_base} ({indice_foto}).jpg"

def ds_capturar_e_salvar_rosto_individual_interno(caminho_completo_imagem_a_salvar, haar_cascade_path_full):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[DS_ERRO] Nao foi possivel abrir a camera.")
        return False
    face_cascade = cv2.CascadeClassifier(haar_cascade_path_full)
    inicio_tempo_deteccao = None
    rosto_salvo = False
    print(f"[DS] Preparando para salvar em: {os.path.basename(caminho_completo_imagem_a_salvar)}")
    cv2.namedWindow(DS_NOME_JANELA_CAPTURA)
    while True:
        ret, frame = cap.read()
        if not ret: print("[DS_ERRO] Nao foi possivel ler o frame da camera."); break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rostos = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
        frame_display = frame.copy()
        cv2.putText(frame_display, "Q/E para Sair", (10, 20), DS_FONTE_TEXTO, DS_ESCALA_FONTE_SAIR_MSG, DS_COR_TEXTO_SAIR_MSG, DS_ESPESSURA_TEXTO_SAIR_MSG, cv2.LINE_AA)
        if len(rostos) > 0:
            x, y, w, h = rostos[0]
            cv2.rectangle(frame_display, (x, y), (x + w, y + h), DS_COR_RETANGULO_CAPTURA, 2)
            if inicio_tempo_deteccao is None:
                inicio_tempo_deteccao = time.time()
                cv2.putText(frame_display, "Rosto detectado!", (x, y - 10), DS_FONTE_TEXTO, 0.7, DS_COR_TEXTO_INFO, 2)
            tempo_decorrido = time.time() - inicio_tempo_deteccao
            if tempo_decorrido <= 3:
                cv2.putText(frame_display, f"Capturando em {3 - int(tempo_decorrido)}s...", (20, frame_display.shape[0] - 20), DS_FONTE_TEXTO, 0.7, DS_COR_TEXTO_CONTADOR, 2)
            else:
                try:
                    cv2.imwrite(caminho_completo_imagem_a_salvar, frame[y:y + h, x:x + w])
                    rosto_salvo = True; print(f"[DS_OK] Rosto salvo: {os.path.basename(caminho_completo_imagem_a_salvar)}"); break
                except Exception as e:
                    print(f"[DS_ERRO] Nao foi possivel salvar a imagem em {os.path.basename(caminho_completo_imagem_a_salvar)}: {e}")
                    inicio_tempo_deteccao = None
        else:
            inicio_tempo_deteccao = None
            cv2.putText(frame_display, "Procurando rosto...", (20, 50), DS_FONTE_TEXTO, 0.7, DS_COR_TEXTO_ALERTA, 2)
        cv2.imshow(DS_NOME_JANELA_CAPTURA, frame_display)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('e'): print("[DS] Captura cancelada pelo usuario."); break
        try:
            if cv2.getWindowProperty(DS_NOME_JANELA_CAPTURA, cv2.WND_PROP_VISIBLE) < 1: print("[DS] Janela de captura fechada pelo usuario (X)."); break
        except cv2.error: print("[DS] Janela de captura nao encontrada, encerrando captura."); break
    cap.release(); cv2.destroyAllWindows(); [cv2.waitKey(1) for _ in range(5)]
    return rosto_salvo

def ds_adicionar_informacao_pessoa_interno(id_pessoa_base, nome_completo, sexo, path_arquivo_infos_usuario):
    linha = f"{id_pessoa_base}:{nome_completo},{sexo}\n"
    try:
        with open(path_arquivo_infos_usuario, 'a', encoding='utf-8') as f: f.write(linha)
        print(f"[DS_INFO] Informacoes de '{nome_completo}' (ID: {id_pessoa_base}, Sexo: {sexo}) salvas em {os.path.basename(path_arquivo_infos_usuario)}.")
        return True
    except Exception as e:
        print(f"[DS_ERRO] Nao foi possivel salvar as informacoes no arquivo '{os.path.basename(path_arquivo_infos_usuario)}': {e}")
        return False
#===============================================================================
# FIM DO CÓDIGO DO DEEPSAVE.PY (Funções Core)
#===============================================================================

#===============================================================================
# INÍCIO DA CLASSE DEEPSAVEFRAME
#===============================================================================
class DeepSaveFrame(ttk.Frame):
    def __init__(self, master_container, app_controller, user_email, *args, **kwargs):
        super().__init__(master_container, *args, **kwargs)
        self.app_controller = app_controller
        self.user_email = user_email
        self.style = ttk.Style(self) # Herda estilos do app_controller/LoginApp
        self.configure(style="DS.TFrame") # Aplica estilo de fundo
        self.user_rostos_path, self.user_inforos_path = get_user_specific_paths(self.user_email)
        self.current_person_id = None
        self.photos_taken_count = 0
        self.haar_cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
        if not os.path.exists(self.haar_cascade_path):
            messagebox.showerror("Erro Crítico", f"Arquivo Haar Cascade não encontrado:\n{self.haar_cascade_path}\nA captura de fotos não funcionará.", parent=self)
            self.app_controller._show_main_content_frame()
            return
        self._create_widgets()
        self._reset_form_state()

    def _create_widgets(self):
        back_button = ttk.Button(self, text="Voltar para Deep", command=self.app_controller._show_main_content_frame, style="DS.TButton")
        back_button.pack(pady=10, padx=10, anchor="nw")
        main_frame = ttk.Frame(self, padding="15", style="DS.TFrame")
        main_frame.pack(expand=True, fill=tk.BOTH)
        ttk.Label(main_frame, text="Cadastro de Nova Pessoa", style="DS.Header.TLabel").pack(pady=(0, 15))
        ttk.Label(main_frame, text="Nome Completo:", style="DS.TLabel").pack(anchor="w")
        self.fullname_entry = tk.Entry(main_frame, width=50, font=('Helvetica', 10), relief=tk.FLAT, borderwidth=2, bg=ENTRY_BG_COLOR, fg=TEXT_COLOR, insertbackground=TEXT_COLOR)
        self.fullname_entry.pack(fill=tk.X, pady=(0,10), ipady=4)
        sex_frame = ttk.Frame(main_frame, style="DS.TFrame")
        sex_frame.pack(fill=tk.X, pady=(0,10))
        ttk.Label(sex_frame, text="Sexo:", style="DS.TLabel").pack(side=tk.LEFT, padx=(0,10))
        self.sex_var = tk.StringVar(value="Masculino")
        ttk.Radiobutton(sex_frame, text="Masculino", variable=self.sex_var, value="Masculino", style="DS.TRadiobutton").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(sex_frame, text="Feminino", variable=self.sex_var, value="Feminino", style="DS.TRadiobutton").pack(side=tk.LEFT, padx=5)
        self.save_info_button = ttk.Button(main_frame, text="Salvar Informações", command=self._handle_save_info_and_start_photos, style="DS.TButton")
        self.save_info_button.pack(fill=tk.X, pady=5)
        photo_capture_frame = ttk.Frame(main_frame, style="DS.TFrame")
        photo_capture_frame.pack(fill=tk.X, pady=(10,5))
        self.take_photo_button = ttk.Button(photo_capture_frame, text=f"Tirar Foto ({self.photos_taken_count}/{DS_MAX_FOTOS_POR_PESSOA})", command=self._handle_take_photo, style="DS.TButton")
        self.take_photo_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,5))
        self.finish_person_button = ttk.Button(photo_capture_frame, text="Concluir Cadastro da Pessoa", command=self._handle_finish_person, style="DS.TButton")
        self.finish_person_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5,0))
        self.cancel_button = ttk.Button(main_frame, text="Limpar Formulário", command=self._reset_form_state, style="DS.TButton")
        self.cancel_button.pack(fill=tk.X, pady=(10,0))

    def _reset_form_state(self):
        self.current_person_id = None; self.photos_taken_count = 0
        self.fullname_entry.delete(0, tk.END); self.sex_var.set("Masculino")
        self.fullname_entry.config(state=tk.NORMAL)
        self.save_info_button.config(state=tk.NORMAL)
        self.take_photo_button.config(state=tk.DISABLED, text=f"Tirar Foto ({self.photos_taken_count}/{DS_MAX_FOTOS_POR_PESSOA})")
        self.finish_person_button.config(state=tk.DISABLED)
        print("[DS_GUI] Formulário resetado.")

    def _handle_save_info_and_start_photos(self):
        fullname = self.fullname_entry.get().strip(); sex = self.sex_var.get()
        if not fullname: messagebox.showerror("Campo Obrigatório", "Nome Completo é obrigatório.", parent=self); return
        self.current_person_id = ds_obter_proximo_id_pessoa_base_interno(self.user_rostos_path)
        if ds_adicionar_informacao_pessoa_interno(self.current_person_id, fullname, sex, self.user_inforos_path):
            messagebox.showinfo("Informações Salvas", f"Informações de '{fullname}' (ID: {self.current_person_id}) salvas.\nAgora você pode tirar as fotos.", parent=self)
            self.photos_taken_count = 0
            self.take_photo_button.config(state=tk.NORMAL, text=f"Tirar Foto ({self.photos_taken_count}/{DS_MAX_FOTOS_POR_PESSOA})")
            self.finish_person_button.config(state=tk.NORMAL)
            self.save_info_button.config(state=tk.DISABLED)
            self.fullname_entry.config(state=tk.DISABLED)
        else:
            messagebox.showerror("Erro ao Salvar", "Não foi possível salvar as informações textuais.", parent=self)
            self.current_person_id = None

    def _photo_capture_thread_target(self):
        if not self.current_person_id: self.after(0, lambda: messagebox.showerror("Erro Interno", "ID da pessoa não definido.", parent=self)); return
        if self.photos_taken_count >= DS_MAX_FOTOS_POR_PESSOA:
            self.after(0, lambda: messagebox.showinfo("Limite Atingido", f"Limite de {DS_MAX_FOTOS_POR_PESSOA} fotos atingido.", parent=self))
            self.after(0, lambda: self.take_photo_button.config(state=tk.DISABLED)); return
        nome_arquivo_img = ds_gerar_nome_arquivo_foto_interno(self.current_person_id, self.photos_taken_count)
        caminho_completo_img = os.path.join(self.user_rostos_path, nome_arquivo_img)
        if os.path.exists(caminho_completo_img): self.after(0, lambda: messagebox.showwarning("Arquivo Existente", f"O arquivo {nome_arquivo_img} já existe.", parent=self)); return
        self.after(0, lambda: messagebox.showinfo("Captura de Foto", "A câmera será aberta. Pressione Q/E para cancelar.", parent=self))
        success = ds_capturar_e_salvar_rosto_individual_interno(caminho_completo_img, self.haar_cascade_path)
        if not success and not cv2.VideoCapture(0).isOpened(): self.after(0, lambda: messagebox.showerror("Erro de Câmera", "Não foi possível abrir a câmera.", parent=self))
        self.after(0, self._update_gui_after_photo_capture, success)

    def _update_gui_after_photo_capture(self, photo_saved_successfully):
        if photo_saved_successfully:
            self.photos_taken_count += 1
            messagebox.showinfo("Foto Salva", f"Foto {self.photos_taken_count} salva!", parent=self)
        elif cv2.VideoCapture(0).isOpened(): messagebox.showerror("Falha na Captura", "Não foi possível salvar a foto.", parent=self)
        self.take_photo_button.config(text=f"Tirar Foto ({self.photos_taken_count}/{DS_MAX_FOTOS_POR_PESSOA})")
        if self.photos_taken_count >= DS_MAX_FOTOS_POR_PESSOA:
            self.take_photo_button.config(state=tk.DISABLED)
            messagebox.showinfo("Limite Atingido", "Todas as fotos foram capturadas.", parent=self)

    def _handle_take_photo(self):
        if not self.current_person_id: messagebox.showerror("Erro", "Salve as informações antes de tirar fotos.", parent=self); return
        cap_test = cv2.VideoCapture(0)
        if not cap_test.isOpened(): messagebox.showerror("Erro de Câmera", "Não foi possível acessar a câmera.", parent=self); cap_test.release(); return
        cap_test.release()
        threading.Thread(target=self._photo_capture_thread_target, daemon=True).start()

    def _handle_finish_person(self):
        messagebox.showinfo("Cadastro Concluído", f"Cadastro para ID {self.current_person_id} finalizado com {self.photos_taken_count} foto(s).", parent=self)
        self._reset_form_state()
#===============================================================================
# FIM DA CLASSE DEEPSAVEFRAME
#===============================================================================

#===============================================================================
# INÍCIO DO CÓDIGO DO DEEPSCAN.PY
#===============================================================================
DSC_MODELO_DETECCAO = 'opencv'; DSC_MODELO_RECONHECIMENTO = 'Facenet512'; DSC_LIMIAR_SIMILARIDADE = 0.40
DSC_COR_VERDE = (0, 255, 0); DSC_COR_AZUL = (255, 0, 0); DSC_COR_VERMELHO = (0, 0, 255)
DSC_COR_HITBOX_CONHECIDO_COM_EMPRESA = DSC_COR_VERDE; DSC_COR_TEXTO_NOME_CONHECIDO = DSC_COR_VERDE
DSC_COR_TEXTO_EMPRESA_CONHECIDO = DSC_COR_VERDE; DSC_COR_HITBOX_CONHECIDO_SEM_EMPRESA = DSC_COR_AZUL
DSC_COR_HITBOX_DESCONHECIDO = DSC_COR_VERMELHO; DSC_COR_TEXTO_LABEL_DESCONHECIDO = DSC_COR_VERMELHO
DSC_FONTE_TEXTO_CV2 = cv2.FONT_HERSHEY_SIMPLEX; DSC_ESCALA_FONTE_CV2 = 0.55; DSC_ESPESSURA_LINHA = 2
DSC_ESPESSURA_TEXTO_CV2 = 1; DSC_TAMANHO_FONTE_PILLOW = 18; DSC_TEXT_PADDING = 5
DSC_PATH_FONTE_TTF_NOME = "arial.ttf"; DSC_NOME_JANELA_APP = "Deep Scan"
DSC_LARGURA_JANELA_DESEJADA = 1280; DSC_ALTURA_JANELA_DESEJADA = int(DSC_LARGURA_JANELA_DESEJADA * 9 / 16)
DSC_CACHE_EMBEDDINGS_CONHECIDOS = []; DSC_CACHE_INFO_PESSOAS = {}; DSC_FONTE_PILLOW_OBJ = None; DSC_DEEPFACE_MODELS_LOADED = False

def dsc_carregar_informacoes_pessoas_interno(caminho_arquivo_infos_usuario_full, force_reload=False):
    if not force_reload and DSC_CACHE_INFO_PESSOAS: return DSC_CACHE_INFO_PESSOAS
    informacoes = {}
    try:
        with open(caminho_arquivo_infos_usuario_full, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if not linha or ':' not in linha or linha.startswith("#"): continue
                chave, dados_str = linha.split(':', 1); dados = [d.strip() for d in dados_str.split(',')]
                if len(dados) >= 1: informacoes[chave.upper().strip()] = (dados[0].strip(), "N/A")
        DSC_CACHE_INFO_PESSOAS = informacoes # Atualiza cache global da sessão
    except FileNotFoundError: print(f"[DSC_ERRO] Arquivo '{os.path.basename(caminho_arquivo_infos_usuario_full)}' não encontrado.")
    except Exception as e: print(f"[DSC_ERRO] Ao ler '{os.path.basename(caminho_arquivo_infos_usuario_full)}': {e}")
    return DSC_CACHE_INFO_PESSOAS

def dsc_carregar_rostos_conhecidos_interno(DeepFace_instance_local, pasta_contendo_imagens_rostos_usuario_full, informacoes_pessoas, modelo_deteccao, modelo_reconhecimento, force_reload=False):
    # Cache global DSC_CACHE_EMBEDDINGS_CONHECIDOS é usado
    if DSC_CACHE_EMBEDDINGS_CONHECIDOS and not force_reload: return DSC_CACHE_EMBEDDINGS_CONHECIDOS
    rostos_conhecidos_data_temp = []
    if not os.path.exists(pasta_contendo_imagens_rostos_usuario_full):
        print(f"[DSC_ERRO] Pasta '{os.path.basename(pasta_contendo_imagens_rostos_usuario_full)}' não encontrada."); return []
    imagens_por_id_base = {}
    for nome_arquivo in os.listdir(pasta_contendo_imagens_rostos_usuario_full):
        caminho_completo = os.path.join(pasta_contendo_imagens_rostos_usuario_full, nome_arquivo)
        if os.path.isfile(caminho_completo) and nome_arquivo.lower().endswith(('.jpg', '.jpeg', '.png')):
            match_id = re.match(r"(\d{3})", os.path.splitext(nome_arquivo)[0])
            if not match_id: continue
            nome_id_base_str = match_id.group(1).upper()
            if nome_id_base_str not in informacoes_pessoas: continue
            if nome_id_base_str not in imagens_por_id_base or not re.search(r" \(\d+\)$", os.path.splitext(imagens_por_id_base[nome_id_base_str]['nome_arquivo'])[0]):
                imagens_por_id_base[nome_id_base_str] = {'caminho': caminho_completo, 'nome_arquivo': nome_arquivo}
    if not imagens_por_id_base: return []
    for nome_id, img_data in imagens_por_id_base.items():
        try:
            rep_list = DeepFace_instance_local.represent(img_path=img_data['caminho'], model_name=modelo_reconhecimento, detector_backend=modelo_deteccao, enforce_detection=True, align=True)
            if rep_list and 'embedding' in rep_list[0]:
                rostos_conhecidos_data_temp.append({"nome_id": nome_id, "embedding": rep_list[0]['embedding'], "dados_pessoa": informacoes_pessoas[nome_id]})
        except Exception as e: print(f"[DSC_ERRO] Processando '{img_data['nome_arquivo']}' (ID: {nome_id}): {e}")
    DSC_CACHE_EMBEDDINGS_CONHECIDOS = rostos_conhecidos_data_temp
    if DSC_CACHE_EMBEDDINGS_CONHECIDOS: print(f"[DSC_INFO] {len(DSC_CACHE_EMBEDDINGS_CONHECIDOS)} embeddings carregados.")
    return DSC_CACHE_EMBEDDINGS_CONHECIDOS

def dsc_desenhar_informacoes_interno(frame, rosto_info, x, y, w, h, identificado=True, nome_arquivo_fonte_ttf=None, fonte_pillow_obj_local=None):
    nome_display = "Desconhecido"; cor_hitbox = DSC_COR_HITBOX_DESCONHECIDO; cor_texto_nome = DSC_COR_TEXTO_LABEL_DESCONHECIDO
    if identificado and rosto_info and "dados_pessoa" in rosto_info:
        try:
            nome_completo, _ = rosto_info["dados_pessoa"]
            nome_display = nome_completo.strip(); cor_texto_nome = DSC_COR_TEXTO_NOME_CONHECIDO
            cor_hitbox = DSC_COR_HITBOX_CONHECIDO_SEM_EMPRESA # Empresa não é mais um fator para cor
        except: nome_display = "Erro Dados"; cor_hitbox = DSC_COR_HITBOX_DESCONHECIDO; cor_texto_nome = DSC_COR_TEXTO_LABEL_DESCONHECIDO
    cv2.rectangle(frame, (x, y), (x + w, y + h), cor_hitbox, DSC_ESPESSURA_LINHA)
    global DSC_FONTE_PILLOW_OBJ # Usa o cache global para a fonte Pillow
    if PIL_AVAILABLE and DSC_FONTE_PILLOW_OBJ is None and nome_arquivo_fonte_ttf and PIL_ImageFont:
        path_fonte_ttf_full = get_resource_path(os.path.join(DSC_SUBPASTA_FONTES, nome_arquivo_fonte_ttf))
        if os.path.exists(path_fonte_ttf_full):
            try: DSC_FONTE_PILLOW_OBJ = PIL_ImageFont.truetype(path_fonte_ttf_full, DSC_TAMANHO_FONTE_PILLOW)
            except Exception as e: print(f"[DSC_AVISO] Falha ao carregar fonte TTF: {e}. Pillow usará padrão."); DSC_FONTE_PILLOW_OBJ = "error_load"
        else: print(f"[DSC_AVISO] Fonte TTF não encontrada. Pillow usará padrão."); DSC_FONTE_PILLOW_OBJ = "error_not_found"
    pillow_ok = False
    if PIL_AVAILABLE and isinstance(DSC_FONTE_PILLOW_OBJ, PIL_ImageFont.FreeTypeFont) and PIL_Image and PIL_ImageDraw:
        try:
            pil_img = PIL_Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)); draw = PIL_ImageDraw.Draw(pil_img)
            try: text_bbox = draw.textbbox((0,0), nome_display, font=DSC_FONTE_PILLOW_OBJ)
            except AttributeError: text_bbox = (0,0) + draw.textsize(nome_display, font=DSC_FONTE_PILLOW_OBJ)
            y_text = y - (text_bbox[3] - text_bbox[1]) - DSC_TEXT_PADDING if y - (text_bbox[3] - text_bbox[1]) - DSC_TEXT_PADDING > DSC_TEXT_PADDING else y + h + DSC_TEXT_PADDING
            draw.text((x, y_text), nome_display, font=DSC_FONTE_PILLOW_OBJ, fill=(cor_texto_nome[2], cor_texto_nome[1], cor_texto_nome[0]))
            frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR); pillow_ok = True
        except Exception as e: print(f"[DSC_AVISO] Erro ao desenhar com Pillow: {e}")
    if not pillow_ok:
        (tw, th), _ = cv2.getTextSize(nome_display, DSC_FONTE_TEXTO_CV2, DSC_ESCALA_FONTE_CV2, DSC_ESPESSURA_TEXTO_CV2)
        y_cv2 = y - DSC_TEXT_PADDING if y - th - DSC_TEXT_PADDING > 0 else y + h + th + DSC_TEXT_PADDING
        cv2.putText(frame, nome_display, (x, y_cv2), DSC_FONTE_TEXTO_CV2, DSC_ESCALA_FONTE_CV2, cor_texto_nome, DSC_ESPESSURA_TEXTO_CV2, cv2.LINE_AA)
    return DSC_FONTE_PILLOW_OBJ # Retorna para possível reutilização (embora global)

def ds_identificar_arquivos_nao_atribuidos_geral(path_rostos, path_infos): # Simplificado
    ids_em_inforos = set()
    try:
        with open(path_infos, 'r', encoding='utf-8') as f:
            for linha in f:
                if ':' in linha and not linha.startswith("#"): ids_em_inforos.add(linha.split(':',1)[0].strip())
    except FileNotFoundError: return []
    if not os.path.exists(path_rostos): return []
    nao_atribuidos = []
    for f_name in os.listdir(path_rostos):
        if f_name.lower().endswith((".jpg", ".jpeg")):
            match = re.match(r"(\d{3})", f_name)
            if not match or match.group(1) not in ids_em_inforos or not re.fullmatch(r"\d{3}(?: \(\d+\))?\.jpe?g$", f_name, re.IGNORECASE):
                nao_atribuidos.append(f_name)
    return sorted(list(set(nao_atribuidos)))

def dsc_atribuir_fotos_pendentes_automaticamente(path_rostos, path_infos):
    print(f"[DSC_AUTO] Verificando pendentes em '{os.path.basename(os.path.dirname(path_rostos))}'...")
    ids_em_inforos = set()
    try:
        with open(path_infos, 'r', encoding='utf-8') as f:
            for linha in f:
                if ':' in linha and not linha.startswith("#"): ids_em_inforos.add(linha.split(':',1)[0].strip())
    except FileNotFoundError: print(f"[DSC_AUTO] '{os.path.basename(path_infos)}' não encontrado."); return
    if not ids_em_inforos: print("[DSC_AUTO] Nenhum ID em info."); return
    ids_com_fotos_formatadas = set()
    if os.path.exists(path_rostos):
        for f_name in os.listdir(path_rostos):
            match = re.match(r"(\d{3})(?: \(\d+\))?\.jpe?g$", f_name, re.IGNORECASE)
            if match: ids_com_fotos_formatadas.add(match.group(1))
    else: print(f"[DSC_AUTO] Pasta '{os.path.basename(path_rostos)}' não encontrada."); return
    ids_sem_fotos = sorted(list(ids_em_inforos - ids_com_fotos_formatadas), key=int, reverse=True)
    nao_atribuidos = ds_identificar_arquivos_nao_atribuidos_geral(path_rostos, path_infos)
    if not nao_atribuidos and not ids_sem_fotos: print("[DSC_AUTO] Nenhuma foto pendente."); return
    if nao_atribuidos: print(f"[DSC_AUTO] Não atribuídos: {nao_atribuidos}")
    if ids_sem_fotos: print(f"[DSC_AUTO] IDs sem fotos formatadas: {ids_sem_fotos}")
    usados = set()
    for id_alvo in ids_sem_fotos:
        atribuidas_id = sum(1 for f_exist in os.listdir(path_rostos) if re.fullmatch(rf"{id_alvo}(?: \(\d+\))?\.jpe?g$", f_exist, re.IGNORECASE))
        for f_origem in list(nao_atribuidos):
            if f_origem in usados or atribuidas_id >= DS_MAX_FOTOS_POR_PESSOA: break
            orig_path = os.path.join(path_rostos, f_origem)
            dest_nome = ds_gerar_nome_arquivo_foto_interno(id_alvo, atribuidas_id)
            dest_path = os.path.join(path_rostos, dest_nome)
            if os.path.abspath(orig_path) == os.path.abspath(dest_path):
                atribuidas_id += 1; nao_atribuidos.remove(f_origem); usados.add(f_origem); usados.add(dest_nome); continue
            if os.path.exists(dest_path): print(f"[DSC_AUTO_AVISO] Destino '{dest_nome}' já existe."); continue
            try:
                os.rename(orig_path, dest_path); print(f"[DSC_AUTO_OK] '{f_origem}' -> '{dest_nome}' (ID {id_alvo}).")
                atribuidas_id += 1; nao_atribuidos.remove(f_origem); usados.add(f_origem); usados.add(dest_nome)
            except Exception as e: print(f"[DSC_AUTO_ERRO] Renomeando '{f_origem}': {e}")
        if not nao_atribuidos: break
    print("[DSC_AUTO] Verificação finalizada.")

def executar_reconhecimento_deep_scan(user_email):
    global DSC_DEEPFACE_MODELS_LOADED, DSC_CACHE_EMBEDDINGS_CONHECIDOS, DSC_CACHE_INFO_PESSOAS, DSC_FONTE_PILLOW_OBJ
    if not DEEPFACE_AVAILABLE: messagebox.showerror("DeepScan - Erro", "DeepFace não instalado."); return
    if not user_email: messagebox.showerror("DeepScan - Erro", "Email do usuário não fornecido."); return
    path_rostos, path_infos = get_user_specific_paths(user_email)
    print(f"[DeepScan] Iniciando para: {user_email}, Rostos: {path_rostos}, Infos: {path_infos}")
    dsc_atribuir_fotos_pendentes_automaticamente(path_rostos, path_infos)
    if not DSC_DEEPFACE_MODELS_LOADED:
        try:
            print("[DSC_INFO] Pré-carregando modelos DeepFace..."); DeepFace.build_model(DSC_MODELO_RECONHECIMENTO)
            DSC_DEEPFACE_MODELS_LOADED = True; print(f"[DSC_INFO] Modelo '{DSC_MODELO_RECONHECIMENTO}' pré-carregado.")
        except Exception as e: messagebox.showerror("DeepScan - Erro", f"Erro ao carregar modelos: {e}"); return
    DSC_CACHE_INFO_PESSOAS.clear(); DSC_CACHE_EMBEDDINGS_CONHECIDOS.clear(); DSC_FONTE_PILLOW_OBJ = None # Reset caches por sessão
    infos_pessoas = dsc_carregar_informacoes_pessoas_interno(path_infos, force_reload=True)
    embeddings_conhecidos = dsc_carregar_rostos_conhecidos_interno(DeepFace, path_rostos, infos_pessoas, DSC_MODELO_DETECCAO, DSC_MODELO_RECONHECIMENTO, force_reload=True)
    if not embeddings_conhecidos:
        msg = "Nenhum rosto conhecido carregado." + ("\nNenhuma info de pessoa encontrada." if not infos_pessoas else "\nTodos serão 'Desconhecido'.")
        if not infos_pessoas: messagebox.showwarning("DeepScan - Sem Dados", msg); print(f"[DSC_CRÍTICO] {msg}"); return
        else: messagebox.showinfo("DeepScan - Atenção", msg); print(f"[DSC_AVISO] {msg}")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened(): messagebox.showerror("DeepScan - Erro", "Não foi possível abrir a webcam."); return
    cv2.namedWindow(DSC_NOME_JANELA_APP, cv2.WINDOW_NORMAL)
    try: cv2.resizeWindow(DSC_NOME_JANELA_APP, DSC_LARGURA_JANELA_DESEJADA, DSC_ALTURA_JANELA_DESEJADA)
    except: pass
    print(f"\n[DSC_INFO] Iniciando reconhecimento para '{user_email}'... Q/E para sair.")
    frame_count = 0; process_every_n = 2; rostos_desenhar_cache = []; running = True
    while running:
        ret, frame_orig = cap.read();
        if not ret: break
        h_orig, w_orig = frame_orig.shape[:2]; ratio_orig = w_orig/h_orig if h_orig > 0 else 1.0
        ratio_janela = DSC_LARGURA_JANELA_DESEJADA/DSC_ALTURA_JANELA_DESEJADA if DSC_ALTURA_JANELA_DESEJADA > 0 else 1.0
        frame_display = np.zeros((DSC_ALTURA_JANELA_DESEJADA, DSC_LARGURA_JANELA_DESEJADA, 3), dtype=np.uint8)
        off_x, off_y = 0,0
        if abs(ratio_orig - ratio_janela) < 0.01: frame_proc = cv2.resize(frame_orig, (DSC_LARGURA_JANELA_DESEJADA, DSC_ALTURA_JANELA_DESEJADA))
        elif ratio_orig > ratio_janela: new_h = int(DSC_LARGURA_JANELA_DESEJADA/ratio_orig); frame_proc = cv2.resize(frame_orig, (DSC_LARGURA_JANELA_DESEJADA, new_h)); off_y = (DSC_ALTURA_JANELA_DESEJADA - new_h)//2
        else: new_w = int(DSC_ALTURA_JANELA_DESEJADA*ratio_orig); frame_proc = cv2.resize(frame_orig, (new_w, DSC_ALTURA_JANELA_DESEJADA)); off_x = (DSC_LARGURA_JANELA_DESEJADA - new_w)//2
        
        frame_para_desenhar = frame_proc.copy() # Desenha sobre a cópia do frame redimensionado

        frame_count +=1
        if frame_count % process_every_n == 0:
            rostos_desenhar_cache.clear()
            try:
                faces_info = DeepFace.extract_faces(img_path=frame_proc, detector_backend=DSC_MODELO_DETECCAO, enforce_detection=False, align=True)
                for face_info in faces_info:
                    if face_info['confidence'] < 0.5: continue
                    x,y,w,h_ = face_info['facial_area']['x'], face_info['facial_area']['y'], face_info['facial_area']['w'], face_info['facial_area']['h']
                    rosto_crop = face_info['face']
                    if rosto_crop.size == 0 or w == 0 or h_ == 0: rostos_desenhar_cache.append({'info':{},'x':x,'y':y,'w':w,'h':h_,'id':False}); continue
                    if not embeddings_conhecidos: rostos_desenhar_cache.append({'info':{},'x':x,'y':y,'w':w,'h':h_,'id':False}); continue
                    try:
                        emb_atual_list = DeepFace.represent(img_path=rosto_crop, model_name=DSC_MODELO_RECONHECIMENTO, detector_backend='skip', enforce_detection=False, align=False)
                        if not emb_atual_list or not emb_atual_list[0].get('embedding'): rostos_desenhar_cache.append({'info':{},'x':x,'y':y,'w':w,'h':h_,'id':False}); continue
                        emb_atual = emb_atual_list[0]['embedding']; menor_dist = float('inf'); melhor_match = None; id_ok = False
                        for emb_conhecido_data in embeddings_conhecidos:
                            res = DeepFace.verify(img1_path=emb_atual, img2_path=emb_conhecido_data["embedding"], model_name=DSC_MODELO_RECONHECIMENTO, distance_metric='cosine', detector_backend='skip', align=False, enforce_detection=False)
                            dist = res['distance']
                            if dist < menor_dist and dist < DSC_LIMIAR_SIMILARIDADE: menor_dist=dist; melhor_match=emb_conhecido_data; id_ok=True
                        rostos_desenhar_cache.append({'info':melhor_match if id_ok else {},'x':x,'y':y,'w':w,'h':h_,'id':id_ok})
                    except Exception as e_rep: print(f"[DSC_ERRO_REP] {e_rep}"); rostos_desenhar_cache.append({'info':{},'x':x,'y':y,'w':w,'h':h_,'id':False})
            except Exception as e_ext: print(f"[DSC_ERRO_EXTRACT] {e_ext}")
        
        for r_draw in rostos_desenhar_cache:
            DSC_FONTE_PILLOW_OBJ = dsc_desenhar_informacoes_interno(frame_para_desenhar, r_draw['info'], r_draw['x'],r_draw['y'],r_draw['w'],r_draw['h'], r_draw['id'], DSC_PATH_FONTE_TTF_NOME, DSC_FONTE_PILLOW_OBJ)
        
        # Coloca o frame processado (com desenhos) de volta no frame_display (com barras pretas se necessário)
        if abs(ratio_orig - ratio_janela) < 0.01: frame_display = frame_para_desenhar
        else: frame_display[off_y : off_y+frame_para_desenhar.shape[0], off_x : off_x+frame_para_desenhar.shape[1]] = frame_para_desenhar

        cv2.imshow(DSC_NOME_JANELA_APP, frame_display)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('e'): running=False; break
        try:
            if cv2.getWindowProperty(DSC_NOME_JANELA_APP, cv2.WND_PROP_VISIBLE) < 1: running=False; break
        except cv2.error: running=False; break
    cap.release(); cv2.destroyAllWindows(); [cv2.waitKey(1) for _ in range(5)]
    print(f"[DSC_INFO] Recursos DeepScan liberados para '{user_email}'.")
#===============================================================================
# FIM DO CÓDIGO DO DEEPSCAN.PY
#===============================================================================

#===============================================================================
# INÍCIO DA CLASSE PROFILEFRAME
#===============================================================================
class ProfileFrame(ttk.Frame):
    def __init__(self, master_container, app_controller, user_data, login_app_instance, *args, **kwargs):
        super().__init__(master_container, *args, **kwargs)
        self.app_controller = app_controller
        self.user_data = user_data
        self.login_app_instance = login_app_instance
        self.configure(style="Background.TFrame") # Cor de fundo #0a0a0a
        self.show_current_password_var = tk.BooleanVar()
        self.show_new_password_var = tk.BooleanVar()
        self.show_confirm_new_password_var = tk.BooleanVar()
        self.error_color = "pink"; self.success_color = "lightgreen"
        self.text_error_color = "red"; self.text_success_color = "green"
        
        self.password_reset_widgets_visible = False
        self._create_widgets()
        self._create_password_reset_widgets() # Cria mas não mostra
        self._toggle_password_reset_section(show=False) # Esconde inicialmente

    def _create_widgets(self):
        back_button = ttk.Button(self, text="Voltar para Deep", command=self.app_controller._show_main_content_frame, style="Purple.TButton")
        back_button.pack(pady=(10,0), padx=10, anchor="nw")
        
        self.main_profile_frame = ttk.Frame(self, padding="20", style="Background.TFrame")
        self.main_profile_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(self.main_profile_frame, text="Informações do Usuário", style="Header.TLabel").pack(pady=(0, 15)) # Texto #6600eb
        age_display = "N/A"
        dob_str = self.user_data.get("dob")
        if dob_str:
            try:
                birth_date = datetime.strptime(dob_str, "%d/%m/%Y").date(); today = date.today()
                age_display = str(today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day)))
            except ValueError: age_display = "Inválida"
        info_map = {"Nome Completo:": self.user_data.get("fullname", "N/A"), "Empresa:": self.user_data.get("company", "N/A"),
                    "Cargo:": self.user_data.get("position", "N/A"), "Email:": self.user_data.get("email", "N/A"),
                    "Data de Nascimento:": self.user_data.get("dob", "N/A"), "Idade:": age_display}
        for label_text, value in info_map.items():
            row = ttk.Frame(self.main_profile_frame, style="Background.TFrame")
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=label_text, style="TLabel", font=('Helvetica', 10, 'bold'), width=18, anchor="w").pack(side=tk.LEFT) # Texto #6600eb
            ttk.Label(row, text=value, style="TLabel", font=('Helvetica', 10), wraplength=250).pack(side=tk.LEFT, expand=True, fill=tk.X) # Texto #6600eb

        self.show_reset_button = ttk.Button(self.main_profile_frame, text="Alterar Senha", command=lambda: self._toggle_password_reset_section(show=True), style="Purple.TButton")
        self.show_reset_button.pack(fill=tk.X, pady=(20,5))
        
        logout_button = ttk.Button(self.main_profile_frame, text="Logout", command=self._logout, style="Purple.TButton")
        logout_button.pack(fill=tk.X, pady=(10,5))

    def _create_password_reset_widgets(self):
        self.password_reset_frame = ttk.Frame(self.main_profile_frame, style="Background.TFrame")
        # Não fazer .pack() aqui, será feito em _toggle_password_reset_section

        ttk.Label(self.password_reset_frame, text="Redefinir Senha", style="Header.TLabel").pack(pady=(10,10)) # Texto #6600eb
        
        entry_common_options = {'width': 40, 'font': ('Helvetica', 10), 'relief': tk.FLAT, 'borderwidth': 2,
                                'bg': PROFILE_ENTRY_BG_COLOR, 'fg': PROFILE_ENTRY_FG_COLOR, # Cores para Entry
                                'insertbackground': TEXT_COLOR} # Cor do cursor

        ttk.Label(self.password_reset_frame, text="Senha Atual:", style="TLabel").pack(fill=tk.X) # Texto #6600eb
        self.current_password_entry = tk.Entry(self.password_reset_frame, show="*", **entry_common_options)
        self.current_password_entry.pack(fill=tk.X, pady=(0,2), ipady=4)
        self._set_entry_style_profile(self.current_password_entry)
        ttk.Checkbutton(self.password_reset_frame, text="Mostrar", variable=self.show_current_password_var, command=self._toggle_current_password_visibility, style="Purple.TCheckbutton").pack(anchor=tk.W, pady=(0,5))

        ttk.Label(self.password_reset_frame, text="Nova Senha:", style="TLabel").pack(fill=tk.X, pady=(5,0)) # Texto #6600eb
        self.new_password_entry = tk.Entry(self.password_reset_frame, show="*", **entry_common_options)
        self.new_password_entry.pack(fill=tk.X, pady=(0,2), ipady=4)
        self._set_entry_style_profile(self.new_password_entry)
        self.new_password_entry.bind("<KeyRelease>", self._validate_new_password_realtime_profile)
        self._setup_password_requirements_labels_profile(self.password_reset_frame)
        ttk.Checkbutton(self.password_reset_frame, text="Mostrar", variable=self.show_new_password_var, command=self._toggle_new_password_visibility, style="Purple.TCheckbutton").pack(anchor=tk.W, pady=(0,5))

        ttk.Label(self.password_reset_frame, text="Confirmar Nova Senha:", style="TLabel").pack(fill=tk.X, pady=(5,0)) # Texto #6600eb
        self.confirm_new_password_entry = tk.Entry(self.password_reset_frame, show="*", **entry_common_options)
        self.confirm_new_password_entry.pack(fill=tk.X, pady=(0,2), ipady=4)
        self._set_entry_style_profile(self.confirm_new_password_entry)
        self.confirm_new_password_entry.bind("<KeyRelease>", self._validate_confirm_new_password_realtime_profile)
        self.confirm_password_feedback_label = ttk.Label(self.password_reset_frame, text="", style="Error.TLabel") # Texto #6600eb (se erro)
        self.confirm_password_feedback_label.pack(fill=tk.X, anchor='w')
        ttk.Checkbutton(self.password_reset_frame, text="Mostrar", variable=self.show_confirm_new_password_var, command=self._toggle_confirm_new_password_visibility, style="Purple.TCheckbutton").pack(anchor=tk.W, pady=(0,10))

        self.reset_password_button = ttk.Button(self.password_reset_frame, text="Confirmar Redefinição", command=self._handle_redefinir_senha, style="Purple.TButton")
        self.reset_password_button.pack(fill=tk.X, pady=5)
        self.cancel_reset_button = ttk.Button(self.password_reset_frame, text="Cancelar Alteração", command=lambda: self._toggle_password_reset_section(show=False), style="Purple.TButton")
        self.cancel_reset_button.pack(fill=tk.X, pady=5)

    def _toggle_password_reset_section(self, show: bool):
        if show:
            self.show_reset_button.pack_forget()
            self.password_reset_frame.pack(fill=tk.X, pady=(10,0), before=self.main_profile_frame.winfo_children()[-1]) # Antes do logout
            self.password_reset_widgets_visible = True
            self.app_controller.geometry("450x820") # Aumentar janela
        else:
            self.password_reset_frame.pack_forget()
            self.show_reset_button.pack(fill=tk.X, pady=(20,5), before=self.main_profile_frame.winfo_children()[-1]) # Re-pack antes do logout
            self.password_reset_widgets_visible = False
            self.app_controller.geometry("450x480") # Diminuir janela

            # Limpar campos e resetar estilos ao esconder
            if hasattr(self, 'current_password_entry'): self.current_password_entry.delete(0, tk.END)
            if hasattr(self, 'new_password_entry'): self.new_password_entry.delete(0, tk.END)
            if hasattr(self, 'confirm_new_password_entry'): self.confirm_new_password_entry.delete(0, tk.END)
            if hasattr(self, 'show_current_password_var'): self.show_current_password_var.set(False); self._toggle_current_password_visibility()
            if hasattr(self, 'show_new_password_var'): self.show_new_password_var.set(False); self._toggle_new_password_visibility()
            if hasattr(self, 'show_confirm_new_password_var'): self.show_confirm_new_password_var.set(False); self._toggle_confirm_new_password_visibility()
            if hasattr(self, 'current_password_entry'): self._set_entry_style_profile(self.current_password_entry)
            if hasattr(self, 'new_password_entry'): self._validate_new_password_realtime_profile()
            if hasattr(self, 'confirm_new_password_entry'): self._validate_confirm_new_password_realtime_profile()


    def _set_entry_style_profile(self, entry_widget, style_type="default"):
        default_hl_bg = BACKGROUND_COLOR; focus_hl_color = TEXT_COLOR
        if style_type == "error": entry_widget.config(highlightbackground=self.error_color, highlightcolor=self.error_color, highlightthickness=2)
        elif style_type == "success": entry_widget.config(highlightbackground=self.success_color, highlightcolor=self.success_color, highlightthickness=2)
        else: entry_widget.config(highlightbackground=default_hl_bg, highlightcolor=focus_hl_color, highlightthickness=1)

    def _toggle_current_password_visibility(self):
        if hasattr(self, 'current_password_entry'): self.current_password_entry.config(show="" if self.show_current_password_var.get() else "*")
    def _toggle_new_password_visibility(self):
        if hasattr(self, 'new_password_entry'): self.new_password_entry.config(show="" if self.show_new_password_var.get() else "*")
    def _toggle_confirm_new_password_visibility(self):
        if hasattr(self, 'confirm_new_password_entry'): self.confirm_new_password_entry.config(show="" if self.show_confirm_new_password_var.get() else "*")

    def _setup_password_requirements_labels_profile(self, parent_frame):
        self.password_req_frame_profile = ttk.Frame(parent_frame, style="Background.TFrame")
        self.password_req_frame_profile.pack(fill=tk.X, pady=(2,5))
        self.req_labels_profile = {
            "length": ttk.Label(self.password_req_frame_profile, text="• 6-16 caracteres", style="Small.TLabel"), # Texto #6600eb
            "upper": ttk.Label(self.password_req_frame_profile, text="• Letra maiúscula (A-Z)", style="Small.TLabel"),
            "lower": ttk.Label(self.password_req_frame_profile, text="• Letra minúscula (a-z)", style="Small.TLabel"),
            "digit": ttk.Label(self.password_req_frame_profile, text="• Número (0-9)", style="Small.TLabel"),
            "special": ttk.Label(self.password_req_frame_profile, text="• Especial (@ # $ * !)", style="Small.TLabel")}
        for label in self.req_labels_profile.values(): label.pack(fill=tk.X, anchor='w')

    def _validate_new_password_realtime_profile(self, event=None):
        if not hasattr(self, 'new_password_entry'): return False
        password = self.new_password_entry.get()
        is_valid, rules_met, _ = validate_password_rules_static(password)
        for rule_name, label in self.req_labels_profile.items():
            label.config(foreground=self.text_success_color if rules_met.get(rule_name) else self.text_error_color)
        self._set_entry_style_profile(self.new_password_entry, "success" if is_valid else "error")
        self._validate_confirm_new_password_realtime_profile(); return is_valid

    def _validate_confirm_new_password_realtime_profile(self, event=None):
        if not hasattr(self, 'new_password_entry') or not hasattr(self, 'confirm_new_password_entry'): return False
        new_pw = self.new_password_entry.get(); confirm_pw = self.confirm_new_password_entry.get()
        is_main_valid, _, _ = validate_password_rules_static(new_pw)
        if not confirm_pw and new_pw: self._set_entry_style_profile(self.confirm_new_password_entry, "default"); self.confirm_password_feedback_label.config(text=""); return False
        if is_main_valid and new_pw == confirm_pw and confirm_pw: self._set_entry_style_profile(self.confirm_new_password_entry, "success"); self.confirm_password_feedback_label.config(text=""); return True
        elif confirm_pw:
            self._set_entry_style_profile(self.confirm_new_password_entry, "error")
            self.confirm_password_feedback_label.config(text="As novas senhas não coincidem" if new_pw != confirm_pw else "", style="Error.TLabel")
            return False
        else: self._set_entry_style_profile(self.confirm_new_password_entry, "default"); self.confirm_password_feedback_label.config(text=""); return False

    def _handle_redefinir_senha(self):
        current_pw = self.current_password_entry.get(); new_pw = self.new_password_entry.get(); confirm_new_pw = self.confirm_new_password_entry.get()
        self._set_entry_style_profile(self.current_password_entry, "default")
        if not current_pw: messagebox.showerror("Erro", "Senha atual é obrigatória.", parent=self); self._set_entry_style_profile(self.current_password_entry, "error"); return
        if not verify_password(self.user_data["hashed_password"], current_pw): messagebox.showerror("Erro", "Senha atual incorreta.", parent=self); self._set_entry_style_profile(self.current_password_entry, "error"); return
        self._set_entry_style_profile(self.current_password_entry, "success")
        is_new_valid, _, new_pw_errors = validate_password_rules_static(new_pw)
        if not new_pw: messagebox.showerror("Erro", "Nova senha é obrigatória.", parent=self); self._validate_new_password_realtime_profile(); return
        if not is_new_valid: messagebox.showerror("Erro", "Nova senha não atende aos requisitos:\n" + "\n".join(new_pw_errors), parent=self); self._validate_new_password_realtime_profile(); return
        if not confirm_new_pw: messagebox.showerror("Erro", "Confirmação da nova senha é obrigatória.", parent=self); self._set_entry_style_profile(self.confirm_new_password_entry, "error"); self.confirm_password_feedback_label.config(text="Confirmação é obrigatória.", style="Error.TLabel"); return
        if new_pw != confirm_new_pw: messagebox.showerror("Erro", "As novas senhas não coincidem.", parent=self); self._validate_confirm_new_password_realtime_profile(); return
        try:
            updated_lines = []; user_updated = False
            if not os.path.exists(DB_FILE_PATH): messagebox.showerror("Erro Crítico", "Arquivo de cadastros não encontrado.", parent=self); return
            with open(DB_FILE_PATH, 'r', encoding='utf-8') as f: lines = f.readlines()
            new_hashed_pw = hash_password(new_pw)
            for line in lines:
                s_line = line.strip()
                if not s_line: updated_lines.append(line); continue
                parts = s_line.split('|')
                if len(parts) == len(USER_DATA_FIELDS) and parts[USER_DATA_FIELDS.index("email")] == self.user_data["email"]:
                    parts[USER_DATA_FIELDS.index("hashed_password")] = new_hashed_pw
                    updated_lines.append("|".join(parts) + "\n"); user_updated = True
                else: updated_lines.append(line)
            if user_updated:
                with open(DB_FILE_PATH, 'w', encoding='utf-8') as f: f.writelines(updated_lines)
                self.user_data["hashed_password"] = new_hashed_pw
                messagebox.showinfo("Sucesso", "Senha redefinida com sucesso!", parent=self)
                self._toggle_password_reset_section(show=False) # Esconde e limpa
            else: messagebox.showerror("Erro Crítico", "Usuário não encontrado para atualização.", parent=self)
        except Exception as e: messagebox.showerror("Erro ao Salvar", f"Erro ao salvar nova senha: {e}", parent=self)

    def _logout(self): self.app_controller._handle_logout()
#===============================================================================
# FIM DA CLASSE PROFILEFRAME
#===============================================================================

#===============================================================================
# INÍCIO DA CLASSE LOGINAPP
#===============================================================================
class LoginApp(tk.Tk):
    def __init__(self, launch_callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.launch_callback = launch_callback
        self.title("Login Deep")
        self.config(bg=BACKGROUND_COLOR)
        self.error_color = "pink"; self.success_color = "lightgreen"; self.text_error_color = "red"; self.text_success_color = "green"
        icon_path = get_resource_path("Deeplogo.ico")
        if os.path.exists(icon_path):
            try: self.iconbitmap(icon_path)
            except tk.TclError: print(f"[LOGIN_AVISO] Ícone '{os.path.basename(icon_path)}' inválido.")
        self.protocol("WM_DELETE_WINDOW", self._on_closing_main_app)
        self.show_login_password_var = tk.BooleanVar(); self.show_reg_password_var = tk.BooleanVar(); self.show_reg_confirm_password_var = tk.BooleanVar()
        self.selected_language = tk.StringVar(value=DEFAULT_LANGUAGE) # Para Combobox de idioma
        self.style = ttk.Style(self); self.style.theme_use('clam')
        self._configure_styles()
        self.login_frame = ttk.Frame(self, padding="20", style="TFrame")
        self.register_frame = ttk.Frame(self, padding="15", style="TFrame")
        self._setup_login_frame(); self._setup_register_frame(); self._show_login_frame()

    def _configure_styles(self):
        self.style.configure("TFrame", background=BACKGROUND_COLOR)
        self.style.configure("Background.TFrame", background=BACKGROUND_COLOR)
        self.style.configure("TLabel", foreground=TEXT_COLOR, background=BACKGROUND_COLOR, padding=5, font=('Helvetica', 10))
        self.style.configure("Header.TLabel", foreground=TEXT_COLOR, background=BACKGROUND_COLOR, font=('Helvetica', 14, 'bold'))
        self.style.configure("Small.TLabel", foreground=TEXT_COLOR, background=BACKGROUND_COLOR, font=('Helvetica', 8))
        self.style.configure("Error.TLabel", foreground=self.text_error_color, background=BACKGROUND_COLOR, font=('Helvetica', 8, 'bold'))
        self.style.configure("Success.TLabel", foreground=self.text_success_color, background=BACKGROUND_COLOR, font=('Helvetica', 8))
        self.style.configure("Purple.TButton", foreground=TEXT_COLOR, background=BUTTON_BG_COLOR, bordercolor=TEXT_COLOR, lightcolor=BUTTON_BG_COLOR, darkcolor=BUTTON_BG_COLOR, font=('Helvetica', 10, 'bold'), padding=8)
        self.style.map("Purple.TButton", background=[('active', ENTRY_BG_COLOR), ('!active', BUTTON_BG_COLOR)], foreground=[('active', BUTTON_BG_COLOR), ('!active', TEXT_COLOR)])
        self.style.configure("Accent.Purple.TButton", foreground=TEXT_COLOR, background=BUTTON_BG_COLOR, font=('Helvetica', 11, 'bold'), padding=10)
        self.style.map("Accent.Purple.TButton", background=[('active', ENTRY_BG_COLOR), ('!active', BUTTON_BG_COLOR)], foreground=[('active', BUTTON_BG_COLOR), ('!active', TEXT_COLOR)])
        self.style.configure("Purple.TCheckbutton", foreground=TEXT_COLOR, background=BACKGROUND_COLOR, indicatorcolor=TEXT_COLOR, font=('Helvetica', 9))
        self.style.map("Purple.TCheckbutton", indicatorcolor=[('selected', TEXT_COLOR), ('!selected', TEXT_COLOR)], background=[('active', BACKGROUND_COLOR)], foreground=[('active', TEXT_COLOR)])
        # Estilo para Combobox (pode precisar de mais ajustes dependendo do tema)
        self.style.configure("TCombobox", fieldbackground=ENTRY_BG_COLOR, background=ENTRY_BG_COLOR, foreground=TEXT_COLOR, arrowcolor=TEXT_COLOR, selectbackground=ENTRY_BG_COLOR, selectforeground=TEXT_COLOR, insertcolor=TEXT_COLOR)
        self.style.map('TCombobox', fieldbackground=[('readonly', ENTRY_BG_COLOR)], selectbackground=[('readonly', ENTRY_BG_COLOR)], selectforeground=[('readonly', TEXT_COLOR)], foreground=[('readonly', TEXT_COLOR)])


    def _clear_login_fields(self):
        self.login_email_entry.delete(0, tk.END); self.login_password_entry.delete(0, tk.END)
        self.show_login_password_var.set(False); self._toggle_login_password_visibility()
        self._set_entry_style(self.login_email_entry, "default"); self._set_entry_style(self.login_password_entry, "default")

    def _on_closing_main_app(self):
        if messagebox.askokcancel("Sair", "Deseja fechar a aplicação?"): self.destroy()

    def _set_entry_style(self, entry_widget, style_type="default", check_label=None):
        default_hl_bg = BACKGROUND_COLOR; focus_hl_color = TEXT_COLOR
        if style_type == "error": entry_widget.config(highlightbackground=self.error_color, highlightcolor=self.error_color, highlightthickness=2)
        elif style_type == "success": entry_widget.config(highlightbackground=self.success_color, highlightcolor=self.success_color, highlightthickness=2)
        else: entry_widget.config(highlightbackground=default_hl_bg, highlightcolor=focus_hl_color, highlightthickness=1)
        if check_label: check_label.config(text="✓" if style_type=="success" else "", foreground=self.text_success_color if style_type=="success" else TEXT_COLOR, background=BACKGROUND_COLOR, font=('Helvetica', 10, 'bold') if style_type=="success" else ('Helvetica', 8))

    def _toggle_login_password_visibility(self): self.login_password_entry.config(show="" if self.show_login_password_var.get() else "*")
    def _toggle_reg_password_visibility(self): self.reg_password_entry.config(show="" if self.show_reg_password_var.get() else "*")
    def _toggle_reg_confirm_password_visibility(self): self.reg_confirm_password_entry.config(show="" if self.show_reg_confirm_password_var.get() else "*")

    def _setup_login_frame(self):
        ttk.Label(self.login_frame, text="DEEP GUARD", style="Header.TLabel").pack(pady=(0, 10))
        ttk.Label(self.login_frame, text="Email:", style="TLabel").pack(fill=tk.X)
        self.login_email_entry = tk.Entry(self.login_frame, width=40, font=('Helvetica', 10), relief=tk.FLAT, borderwidth=2, bg=ENTRY_BG_COLOR, fg=TEXT_COLOR, insertbackground=TEXT_COLOR)
        self.login_email_entry.pack(fill=tk.X, pady=(0,10), ipady=4); self._set_entry_style(self.login_email_entry)
        ttk.Label(self.login_frame, text="Senha:", style="TLabel").pack(fill=tk.X)
        self.login_password_entry = tk.Entry(self.login_frame, show="*", width=40, font=('Helvetica', 10), relief=tk.FLAT, borderwidth=2, bg=ENTRY_BG_COLOR, fg=TEXT_COLOR, insertbackground=TEXT_COLOR)
        self.login_password_entry.pack(fill=tk.X, pady=(0,5), ipady=4); self._set_entry_style(self.login_password_entry)
        ttk.Checkbutton(self.login_frame, text="Mostrar Senha", variable=self.show_login_password_var, command=self._toggle_login_password_visibility, style="Purple.TCheckbutton").pack(anchor=tk.W, pady=(0,10))
        ttk.Button(self.login_frame, text="Login", command=self._handle_login, style="Purple.TButton").pack(fill=tk.X, pady=3)
        ttk.Button(self.login_frame, text="Criar nova conta", command=self._show_register_frame, style="Purple.TButton").pack(fill=tk.X, pady=3)
        
        lang_frame = ttk.Frame(self.login_frame, style="TFrame")
        lang_frame.pack(fill=tk.X, pady=(10,0))
        ttk.Label(lang_frame, text="Idioma:", style="Small.TLabel").pack(side=tk.LEFT, padx=(0,5))
        self.login_lang_combobox = ttk.Combobox(lang_frame, textvariable=self.selected_language, values=LANGUAGES, state="readonly", width=15, style="TCombobox")
        self.login_lang_combobox.pack(side=tk.LEFT)
        self.login_lang_combobox.bind("<<ComboboxSelected>>", self._on_language_select_login)


    def _on_language_select_login(self, event=None):
        print(f"[Login] Idioma selecionado: {self.selected_language.get()}")
        # Aqui, futuramente, você chamaria a lógica para recarregar a UI com o novo idioma.

    def _format_dob_entry(self, event=None):
        # ... (código mantido, sem alterações significativas)
        current_text = self.reg_dob_entry.get(); cleaned = "".join(filter(str.isdigit, current_text))[:8]; formatted = ""
        if len(cleaned) > 0: formatted += cleaned[:2]
        if len(cleaned) > 2: formatted += "/" + cleaned[2:4]
        if len(cleaned) > 4: formatted += "/" + cleaned[4:]
        pos = self.reg_dob_entry.index(tk.INSERT)
        self.reg_dob_entry.unbind("<KeyRelease>"); self.reg_dob_entry.delete(0, tk.END); self.reg_dob_entry.insert(0, formatted)
        self.reg_dob_entry.bind("<KeyRelease>", self._format_dob_entry)
        if event and event.keysym in ('BackSpace', 'Delete'): self.reg_dob_entry.icursor(pos -1 if pos > 0 else 0)
        elif len(formatted) > len(current_text.replace("/","")): self.reg_dob_entry.icursor(tk.END)
        else: self.reg_dob_entry.icursor(pos)

    def _setup_register_frame(self):
        # ... (código mantido, sem alterações significativas na estrutura, apenas estilos)
        top_reg = ttk.Frame(self.register_frame, style="TFrame"); top_reg.pack(fill=tk.X, pady=(0,5))
        ttk.Label(top_reg, text="myDEEP Account", style="Header.TLabel").pack(side=tk.LEFT, expand=True, anchor="center")
        ttk.Button(top_reg, text="Voltar", command=self._show_login_frame, style="Purple.TButton", width=8).pack(side=tk.RIGHT, padx=5)
        self.reg_fields = {}
        fields_cfg = [("Nome Completo:", "reg_fullname_entry", {}), ("Empresa:", "reg_company_entry", {}), ("Cargo:", "reg_position_entry", {}),
                      ("Email:", "reg_email_entry", {}), ("Data de Nascimento (DD/MM/AAAA):", "reg_dob_entry", {}),
                      ("Senha:", "reg_password_entry", {"show": "*"}, "show_reg_password_var", self._toggle_reg_password_visibility, self._validate_reg_password_realtime),
                      ("Confirmar Senha:", "reg_confirm_password_entry", {"show": "*"}, "show_reg_confirm_password_var", self._toggle_reg_confirm_password_visibility, self._validate_confirm_password_realtime)]
        for cfg in fields_cfg:
            lbl_txt, entry_attr, entry_opts = cfg[0], cfg[1], cfg[2]
            ttk.Label(self.register_frame, text=lbl_txt, style="TLabel").pack(fill=tk.X, anchor='w', pady=(3,0))
            entry_chk_frm = ttk.Frame(self.register_frame, style="TFrame"); entry_chk_frm.pack(fill=tk.X)
            entry = tk.Entry(entry_chk_frm, width=38, font=('Helvetica', 10), relief=tk.FLAT, borderwidth=2, bg=ENTRY_BG_COLOR, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, **entry_opts)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, pady=(0,1)); self._set_entry_style(entry); setattr(self, entry_attr, entry)
            chk_lbl = ttk.Label(entry_chk_frm, text="", font=('Helvetica', 10, 'bold'), width=2, anchor="w", style="TLabel"); chk_lbl.pack(side=tk.LEFT, padx=(5,0))
            fb_lbl = ttk.Label(self.register_frame, text="", style="Error.TLabel"); fb_lbl.pack(fill=tk.X, anchor='w', pady=(0,1))
            self.reg_fields[entry_attr] = {"entry": entry, "feedback_label": fb_lbl, "check_label": chk_lbl}
            if entry_attr == "reg_dob_entry": entry.bind("<KeyRelease>", self._format_dob_entry)
            if entry_attr == "reg_password_entry": self._setup_password_requirements_labels(self.register_frame); entry.bind("<KeyRelease>", cfg[5])
            if entry_attr == "reg_confirm_password_entry": entry.bind("<KeyRelease>", cfg[5])
            if len(cfg) > 3 and cfg[3]: ttk.Checkbutton(self.register_frame, text="Mostrar Senha", variable=getattr(self, cfg[3]), command=cfg[4], style="Purple.TCheckbutton").pack(anchor=tk.W, pady=(0,5))
        ttk.Button(self.register_frame, text="Criar Conta", command=self._handle_register, style="Accent.Purple.TButton").pack(fill=tk.X, pady=(15,5))

    def _setup_password_requirements_labels(self, parent_frame):
        # ... (código mantido)
        self.password_req_frame = ttk.Frame(parent_frame, style="TFrame"); self.password_req_frame.pack(fill=tk.X, pady=(2,5))
        self.req_labels = {"length": ttk.Label(self.password_req_frame, text="• 6-16 caracteres", style="Small.TLabel"), "upper": ttk.Label(self.password_req_frame, text="• Letra maiúscula (A-Z)", style="Small.TLabel"),
                           "lower": ttk.Label(self.password_req_frame, text="• Letra minúscula (a-z)", style="Small.TLabel"), "digit": ttk.Label(self.password_req_frame, text="• Número (0-9)", style="Small.TLabel"),
                           "special": ttk.Label(self.password_req_frame, text="• Especial (@ # $ * !)", style="Small.TLabel")}
        for label in self.req_labels.values(): label.pack(fill=tk.X, anchor='w')

    def _show_login_frame(self): self.register_frame.pack_forget(); self.login_frame.pack(expand=True, fill=tk.BOTH); self.title("Login Deep"); self.geometry("400x380") # Ajustado para combobox
    def _show_register_frame(self): self.login_frame.pack_forget(); self.register_frame.pack(expand=True, fill=tk.BOTH); self.title("myDeep Account"); self.geometry("450x750")

    def _validate_generic(self, val, name): return (True, "") if val else (False, f"{name} não pode estar vazio.")
    def _validate_email(self, email):
        is_ok, msg = self._validate_generic(email, "Email");
        if not is_ok: return False, msg
        return (True, "") if re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email) else (False, "Formato de email inválido.")
    def _validate_dob(self, dob):
        is_ok, msg = self._validate_generic(dob, "Data de Nascimento");
        if not is_ok: return False, msg
        if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", dob): return False, "Formato DD/MM/AAAA."
        try:
            b_date = datetime.strptime(dob, "%d/%m/%Y").date(); today = date.today()
            age = today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))
            if age < 18: return False, "Deve ter pelo menos 18 anos."
            if b_date > today: return False, "Data não pode ser no futuro."
        except ValueError: return False, "Data inválida."
        return True, ""
    def _validate_reg_password_realtime(self, event=None):
        # ... (código mantido, usa validate_password_rules_static)
        pw = self.reg_password_entry.get(); is_valid, rules, _ = validate_password_rules_static(pw)
        for rule, lbl in self.req_labels.items(): lbl.config(foreground=self.text_success_color if rules.get(rule) else self.text_error_color)
        self._set_entry_style(self.reg_fields["reg_password_entry"]["entry"], "success" if is_valid else "error", self.reg_fields["reg_password_entry"]["check_label"])
        self._validate_confirm_password_realtime(); return is_valid
    def _validate_confirm_password_realtime(self, event=None):
        # ... (código mantido, usa validate_password_rules_static)
        pw = self.reg_password_entry.get(); conf_pw = self.reg_confirm_password_entry.get()
        entry, fb_lbl, chk_lbl = self.reg_fields["reg_confirm_password_entry"].values()
        is_main_valid, _, _ = validate_password_rules_static(pw)
        if not conf_pw and pw: self._set_entry_style(entry, "default", chk_lbl); fb_lbl.config(text=""); return False
        if is_main_valid and pw == conf_pw and conf_pw: self._set_entry_style(entry, "success", chk_lbl); fb_lbl.config(text=""); return True
        elif conf_pw: self._set_entry_style(entry, "error", chk_lbl); fb_lbl.config(text="As senhas não coincidem" if pw!=conf_pw else "", style="Error.TLabel"); return False
        else: self._set_entry_style(entry, "default", chk_lbl); fb_lbl.config(text=""); return False

    def _handle_login(self):
        # ... (código mantido, sem alterações significativas)
        email = self.login_email_entry.get().strip(); password = self.login_password_entry.get()
        is_email_ok, email_msg = self._validate_email(email)
        if not is_email_ok: messagebox.showerror("Erro Login", email_msg, parent=self); self._set_entry_style(self.login_email_entry, "error"); return
        else: self._set_entry_style(self.login_email_entry, "default")
        if not password: messagebox.showerror("Erro Login", "Senha vazia.", parent=self); self._set_entry_style(self.login_password_entry, "error"); return
        else: self._set_entry_style(self.login_password_entry, "default")
        try:
            user_data = None
            if not os.path.exists(DB_FILE_PATH): messagebox.showerror("Erro Login", "Nenhum usuário cadastrado.", parent=self); return
            with open(DB_FILE_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    s_line = line.strip();
                    if not s_line: continue
                    parts = s_line.split('|')
                    if len(parts) == len(USER_DATA_FIELDS):
                        curr_user = dict(zip(USER_DATA_FIELDS, parts))
                        if curr_user["email"] == email:
                            if verify_password(curr_user["hashed_password"], password): user_data = curr_user; break
                            else: messagebox.showerror("Erro Login", "Email ou senha incorretos.", parent=self); self._set_entry_style(self.login_password_entry, "error"); return
            if user_data: self.withdraw(); self.launch_callback(self, user_data, self.selected_language.get()) # Passa idioma
            else: messagebox.showerror("Erro Login", "Email ou senha incorretos.", parent=self); self._set_entry_style(self.login_email_entry, "error"); self._set_entry_style(self.login_password_entry, "error")
        except Exception as e: messagebox.showerror("Erro Login", f"Ocorreu um erro: {e}", parent=self)

    def _handle_register(self):
        # ... (código mantido, sem alterações significativas)
        for field in self.reg_fields.values():
            field["feedback_label"].config(text="")
            if field["entry"] not in [self.reg_password_entry, self.reg_confirm_password_entry]: self._set_entry_style(field["entry"], "default", field["check_label"])
        data = {k.split('_')[1]: v["entry"].get().strip() if k not in ["reg_password_entry", "reg_confirm_password_entry"] else v["entry"].get() for k,v in self.reg_fields.items()}
        data['password'] = self.reg_password_entry.get(); data['confirm_password'] = self.reg_confirm_password_entry.get() # Garante nomes corretos
        errors = False; err_msgs = []
        validators = [("fullname", "Nome Completo", lambda v: self._validate_generic(v, "Nome Completo")), ("company", "Empresa", lambda v: self._validate_generic(v, "Empresa")),
                      ("position", "Cargo", lambda v: self._validate_generic(v, "Cargo")), ("email", "Email", self._validate_email), ("dob", "Data de Nascimento", self._validate_dob)]
        for key, name, func in validators:
            is_ok, msg = func(data[key])
            if not is_ok: errors=True; self.reg_fields[f"reg_{key}_entry"]["feedback_label"].config(text=msg); self._set_entry_style(self.reg_fields[f"reg_{key}_entry"]["entry"], "error", self.reg_fields[f"reg_{key}_entry"]["check_label"]); err_msgs.append(msg)
        is_pw_valid, _, pw_errs = validate_password_rules_static(data["password"])
        if not data["password"]: errors=True; self.reg_fields["reg_password_entry"]["feedback_label"].config(text="Senha obrigatória."); self._set_entry_style(self.reg_password_entry, "error", self.reg_fields["reg_password_entry"]["check_label"]); [lbl.config(foreground=TEXT_COLOR) for lbl in self.req_labels.values()]; err_msgs.append("Senha obrigatória.")
        elif not is_pw_valid: errors=True; err_msgs.extend(pw_errs)
        if not data["confirm_password"] and data["password"]: errors=True; self.reg_fields["reg_confirm_password_entry"]["feedback_label"].config(text="Confirmação obrigatória."); self._set_entry_style(self.reg_confirm_password_entry, "error", self.reg_fields["reg_confirm_password_entry"]["check_label"]); err_msgs.append("Confirmação obrigatória.")
        elif data["password"] and data["password"] != data["confirm_password"]: errors=True; (self.reg_fields["reg_confirm_password_entry"]["feedback_label"].config(text="Senhas não coincidem") if not self.reg_fields["reg_confirm_password_entry"]["feedback_label"].cget("text") else None); err_msgs.append("Senhas não coincidem.")
        if not errors:
            try: # Verificação de duplicidade
                email_exists, fullname_exists, pw_hash_exists = False, False, False; curr_pw_hash = hash_password(data["password"])
                if os.path.exists(DB_FILE_PATH):
                    with open(DB_FILE_PATH, 'r', encoding='utf-8') as f:
                        for line in f:
                            s_line = line.strip(); parts = s_line.split('|')
                            if not s_line or len(parts) < len(USER_DATA_FIELDS): continue
                            if parts[USER_DATA_FIELDS.index("email")] == data["email"]: email_exists = True
                            if parts[USER_DATA_FIELDS.index("hashed_password")] == curr_pw_hash: pw_hash_exists = True
                            if parts[USER_DATA_FIELDS.index("fullname")].lower() == data["fullname"].lower(): fullname_exists = True
                for exists, key, msg_dupl in [(email_exists, "email", "Email já cadastrado."), (fullname_exists, "fullname", "Nome completo já em uso."), (pw_hash_exists, "password", "Senha já em uso. Escolha outra.")]:
                    if exists: errors=True; self.reg_fields[f"reg_{key}_entry"]["feedback_label"].config(text=msg_dupl); self._set_entry_style(self.reg_fields[f"reg_{key}_entry"]["entry"], "error", self.reg_fields[f"reg_{key}_entry"]["check_label"]); err_msgs.append(msg_dupl)
            except Exception as e: messagebox.showerror("Erro Verificação", f"Erro ao verificar dados: {e}", parent=self); return
        if errors: messagebox.showerror("Erro Cadastro", "Corrija os erros:\n\n" + "\n".join(f"- {m}" for m in list(set(err_msgs))), parent=self); return
        try: # Salvar
            new_user_line = "|".join([data["email"], hash_password(data["password"]), data["fullname"], data["company"], data["position"], data["dob"]]) + "\n"
            with open(DB_FILE_PATH, 'a', encoding='utf-8') as f: f.write(new_user_line)
            messagebox.showinfo("Cadastro Sucesso", "Conta criada! Faça login.", parent=self); self._show_login_frame()
            for field in self.reg_fields.values(): field["entry"].delete(0, tk.END); self._set_entry_style(field["entry"], "default", field.get("check_label")); field["feedback_label"].config(text="")
            [lbl.config(foreground=TEXT_COLOR) for lbl in self.req_labels.values()]
            self.show_reg_password_var.set(False); self._toggle_reg_password_visibility(); self.show_reg_confirm_password_var.set(False); self._toggle_reg_confirm_password_visibility()
        except Exception as e: messagebox.showerror("Erro Cadastro", f"Erro ao salvar: {e}", parent=self)
#===============================================================================
# FIM DA CLASSE LOGINAPP
#===============================================================================

#===============================================================================
# INÍCIO DAS CLASSES DE FRAMES DA JANELA PRINCIPAL
#===============================================================================
class MainContentFrame(ttk.Frame):
    def __init__(self, master_container, app_controller, user_data, *args, **kwargs):
        super().__init__(master_container, *args, **kwargs)
        self.app_controller = app_controller; self.user_data = user_data
        self.configure(style="Background.TFrame")
        top_bar = ttk.Frame(self, style="Background.TFrame"); top_bar.pack(fill=tk.X, pady=(5,0), padx=10)
        self.welcome_label = ttk.Label(top_bar, text="", style="TLabel", font=('Helvetica', 12, 'italic'), anchor="center")
        self.welcome_label.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)
        
        # Botão Configurações em vez de Perfil direto
        settings_button = ttk.Button(top_bar, text="Configurações", command=self.app_controller._show_settings_frame, style="Purple.TButton")
        settings_button.pack(side=tk.RIGHT, padx=10)
        
        buttons_frame = ttk.Frame(self, padding="20 10 20 20", style="Background.TFrame")
        buttons_frame.pack(expand=True, fill=tk.BOTH)
        ttk.Button(buttons_frame, text="Deep Save", command=self.app_controller._show_deepsave_frame, style="Purple.TButton").pack(pady=10, fill=tk.X)
        ttk.Button(buttons_frame, text="Deep Scan", command=self.app_controller.start_deepscan_gui_for_user, style="Purple.TButton").pack(pady=10, fill=tk.X)
        self.app_controller.after(100, self._show_welcome_message)

    def _show_welcome_message(self):
        fullname = self.user_data.get("fullname", "Usuário")
        self.welcome_label.config(text=f"Bem-vindo, {fullname}!")
        self.app_controller.after(8000, self._hide_welcome_message)
    def _hide_welcome_message(self):
        try:
            if self.welcome_label.winfo_exists(): self.welcome_label.config(text="")
        except tk.TclError: pass

class SettingsFrame(ttk.Frame):
    def __init__(self, master_container, app_controller, *args, **kwargs):
        super().__init__(master_container, *args, **kwargs)
        self.app_controller = app_controller
        self.configure(style="Background.TFrame")
        
        back_button = ttk.Button(self, text="Voltar para Deep", command=self.app_controller._show_main_content_frame, style="Purple.TButton")
        back_button.pack(pady=10, padx=10, anchor="nw")

        content_frame = ttk.Frame(self, padding="20", style="Background.TFrame")
        content_frame.pack(expand=True, fill=tk.BOTH)
        
        ttk.Label(content_frame, text="Configurações", style="Header.TLabel").pack(pady=(0,20))
        ttk.Button(content_frame, text="Perfil", command=self.app_controller._show_profile_frame, style="Purple.TButton").pack(fill=tk.X, pady=10)
        ttk.Button(content_frame, text="Idioma", command=self.app_controller._show_language_frame, style="Purple.TButton").pack(fill=tk.X, pady=10)

class LanguageFrame(ttk.Frame):
    def __init__(self, master_container, app_controller, current_language_var, *args, **kwargs):
        super().__init__(master_container, *args, **kwargs)
        self.app_controller = app_controller
        self.current_language_var = current_language_var # tk.StringVar da DeepMainWindow
        self.configure(style="Background.TFrame")

        back_button = ttk.Button(self, text="Voltar para Configurações", command=self.app_controller._show_settings_frame, style="Purple.TButton")
        back_button.pack(pady=10, padx=10, anchor="nw")

        content_frame = ttk.Frame(self, padding="20", style="Background.TFrame")
        content_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(content_frame, text="Selecionar Idioma", style="Header.TLabel").pack(pady=(0,20))
        
        self.lang_combobox = ttk.Combobox(content_frame, textvariable=self.current_language_var, values=LANGUAGES, state="readonly", width=25, style="TCombobox")
        self.lang_combobox.pack(pady=10)
        
        save_button = ttk.Button(content_frame, text="Salvar Idioma", command=self._save_language_preference, style="Purple.TButton")
        save_button.pack(pady=10)

    def _save_language_preference(self):
        selected = self.current_language_var.get()
        messagebox.showinfo("Idioma", f"Idioma '{selected}' selecionado.\n(A interface não será traduzida nesta versão)", parent=self)
        # Aqui iria a lógica para salvar a preferência e recarregar a UI
        print(f"[Idioma] Preferência de idioma salva: {selected}")
        self.app_controller.selected_language.set(selected) # Atualiza var na janela principal

class DeepMainWindow(tk.Tk):
    def __init__(self, login_app_instance, user_data, initial_language, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_app_instance = login_app_instance; self.user_data = user_data
        self.user_email = self.user_data.get("email")
        self.selected_language = tk.StringVar(value=initial_language) # Idioma da sessão

        self.title("Deep"); self.config(bg=BACKGROUND_COLOR)
        icon_path = get_resource_path("Deeplogo.ico")
        if os.path.exists(icon_path):
            try: self.iconbitmap(icon_path)
            except tk.TclError: print(f"[GUI_AVISO] Ícone principal '{os.path.basename(icon_path)}' inválido.")
        self.protocol("WM_DELETE_WINDOW", self._on_closing_deep_main_window)
        self.container_frame = ttk.Frame(self, style="Background.TFrame")
        self.container_frame.pack(expand=True, fill=tk.BOTH)
        self.current_frame_instance = None
        self._show_main_content_frame()
        self.after(150, self.check_initial_setup_deep_main)

    def _switch_frame(self, FrameClass, expected_geometry, *args_for_frame):
        if self.current_frame_instance: self.current_frame_instance.destroy()
        if FrameClass == MainContentFrame: self.current_frame_instance = FrameClass(self.container_frame, self, self.user_data, *args_for_frame)
        elif FrameClass == ProfileFrame: self.current_frame_instance = FrameClass(self.container_frame, self, self.user_data, self.login_app_instance, *args_for_frame)
        elif FrameClass == DeepSaveFrame: self.current_frame_instance = FrameClass(self.container_frame, self, self.user_email, *args_for_frame)
        elif FrameClass == SettingsFrame: self.current_frame_instance = FrameClass(self.container_frame, self, *args_for_frame)
        elif FrameClass == LanguageFrame: self.current_frame_instance = FrameClass(self.container_frame, self, self.selected_language, *args_for_frame) # Passa a var de idioma
        else: self.current_frame_instance = FrameClass(self.container_frame, self, *args_for_frame)
        self.current_frame_instance.pack(expand=True, fill=tk.BOTH)
        self.geometry(expected_geometry)

    def _show_main_content_frame(self): self._switch_frame(MainContentFrame, "400x300")
    def _show_profile_frame(self): self._switch_frame(ProfileFrame, "450x480") # Geometria inicial, pode mudar
    def _show_deepsave_frame(self): self._switch_frame(DeepSaveFrame, "500x550")
    def _show_settings_frame(self): self._switch_frame(SettingsFrame, "400x300")
    def _show_language_frame(self): self._switch_frame(LanguageFrame, "400x300")

    def _handle_logout(self):
        if self.current_frame_instance: self.current_frame_instance.destroy(); self.current_frame_instance = None
        self.destroy()
        if self.login_app_instance:
            try: self.login_app_instance._clear_login_fields(); self.login_app_instance.deiconify()
            except tk.TclError: pass
    def _on_closing_deep_main_window(self):
        if messagebox.askokcancel("Sair", "Deseja fechar e fazer logout?", parent=self): self._handle_logout()
    def check_initial_setup_deep_main(self):
        # ... (código mantido)
        haar_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
        if not os.path.exists(haar_path): messagebox.showwarning("Config. Incompleta", "Haar Cascade não encontrado.", parent=self)
        font_path = get_resource_path(os.path.join(DSC_SUBPASTA_FONTES, DSC_PATH_FONTE_TTF_NOME))
        if not os.path.exists(font_path) and PIL_AVAILABLE: print(f"[GUI_AVISO] Fonte TTF '{DSC_PATH_FONTE_TTF_NOME}' não encontrada.")
    def start_deepscan_gui_for_user(self):
        if not self.user_email: messagebox.showerror("Erro", "Email do usuário não encontrado.", parent=self); return
        messagebox.showinfo("Deep Scan", "Iniciando reconhecimento.\nNova janela OpenCV será aberta.", parent=self)
        run_function_in_thread(executar_reconhecimento_deep_scan, "deepscan_thread", "Deep Scan", args_tuple=(self.user_email,))
#===============================================================================
# FIM DAS CLASSES DE FRAMES DA JANELA PRINCIPAL
#===============================================================================

# Funções de utilidade (fora das classes)
def run_function_in_thread(target_function, thread_var_name, func_name_msg, args_tuple=()):
    global deepscan_thread # Apenas deepscan_thread é gerenciado globalmente agora
    thread_obj = deepscan_thread if thread_var_name == "deepscan_thread" else None
    if thread_obj and thread_obj.is_alive(): messagebox.showwarning("Em Execução", f"'{func_name_msg}' já está em execução."); return
    new_thread = threading.Thread(target=target_function, args=args_tuple, daemon=True)
    if thread_var_name == "deepscan_thread": deepscan_thread = new_thread
    new_thread.start()

def launch_deep_main_window(login_app_instance, user_data, selected_language): # Adicionado selected_language
    deep_app = DeepMainWindow(login_app_instance, user_data, selected_language)
    deep_app.mainloop()

def ensure_core_directories_and_files_exist():
    # ... (código mantido)
    print("[SETUP] Verificando diretórios e arquivos..."); os.makedirs(os.path.join(BASE_PATH, USER_DATA_ROOT_FOLDER), exist_ok=True)
    os.makedirs(get_resource_path(DSC_SUBPASTA_FONTES), exist_ok=True)
    if not os.path.exists(DB_FILE_PATH):
        try: open(DB_FILE_PATH, 'w', encoding='utf-8').close(); print(f"[SETUP_INFO] '{DB_FILENAME}' criado.")
        except IOError as e: print(f"[SETUP_ERRO CRÍTICO] Não foi possível criar '{DB_FILENAME}': {e}")

if __name__ == "__main__":
    ensure_core_directories_and_files_exist()
    login_app = LoginApp(launch_callback=launch_deep_main_window)
    login_app.mainloop()