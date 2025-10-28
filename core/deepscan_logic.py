#Lógica de reconhecimento facial

# -*- coding: utf-8 -*-
import cv2
import os
import re
import numpy as np
from tkinter import messagebox

# Tenta importar dependências pesadas
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

import config
import utils

# --- Variáveis de Cache da Sessão ---
SESSION_CACHE = {
    "embeddings": [],
    "person_info": {},
    "pillow_font": None,
    "models_loaded": False
}

def _load_person_info(info_file_path, force_reload=False):
    if not force_reload and SESSION_CACHE["person_info"]:
        return SESSION_CACHE["person_info"]
    
    info = {}
    try:
        with open(info_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or ':' not in line or line.startswith("#"):
                    continue
                key, data_str = line.split(':', 1)
                data = [d.strip() for d in data_str.split(',')]
                if len(data) >= 1:
                    info[key.upper().strip()] = (data[0].strip(), "N/A") # Nome, Sexo (simplificado)
        SESSION_CACHE["person_info"] = info
    except FileNotFoundError:
        print(f"[DSC_ERRO] Arquivo de informações não encontrado: {os.path.basename(info_file_path)}")
    except Exception as e:
        print(f"[DSC_ERRO] Ao ler informações: {e}")
    return SESSION_CACHE["person_info"]

def _load_known_faces(faces_path, person_info, force_reload=False):
    if not DEEPFACE_AVAILABLE: return []
    if SESSION_CACHE["embeddings"] and not force_reload:
        return SESSION_CACHE["embeddings"]

    known_faces_data = []
    if not os.path.exists(faces_path):
        print(f"[DSC_ERRO] Pasta de rostos não encontrada: {os.path.basename(faces_path)}")
        return []

    images_by_id = {}
    for filename in os.listdir(faces_path):
        full_path = os.path.join(faces_path, filename)
        if os.path.isfile(full_path) and filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            match = re.match(r"(\d{3})", os.path.splitext(filename)[0])
            if not match: continue
            
            base_id = match.group(1).upper()
            if base_id not in person_info: continue
            
            # Pega a primeira foto de cada pessoa para representação
            if base_id not in images_by_id:
                 images_by_id[base_id] = {'path': full_path, 'filename': filename}

    if not images_by_id: return []

    for person_id, img_data in images_by_id.items():
        try:
            representation = DeepFace.represent(
                img_path=img_data['path'],
                model_name=config.DSC_RECOGNITION_MODEL,
                detector_backend=config.DSC_DETECTION_MODEL,
                enforce_detection=True,
                align=True
            )
            if representation and 'embedding' in representation[0]:
                known_faces_data.append({
                    "person_id": person_id,
                    "embedding": representation[0]['embedding'],
                    "person_data": person_info[person_id]
                })
        except Exception as e:
            print(f"[DSC_ERRO] Processando '{img_data['filename']}' (ID: {person_id}): {e}")
    
    SESSION_CACHE["embeddings"] = known_faces_data
    if known_faces_data:
        print(f"[DSC_INFO] {len(known_faces_data)} representações de rostos carregadas.")
    return known_faces_data

def _draw_face_info(frame, face_data, x, y, w, h, is_identified):
    # ... (Lógica de desenho mantida, mas simplificada para focar na estrutura)
    # Esta função desenha o retângulo e o nome na imagem
    name_display = "Desconhecido"
    box_color = (0, 0, 255) # Vermelho para desconhecido
    text_color = (0, 0, 255)

    if is_identified and face_data and "person_data" in face_data:
        full_name, _ = face_data["person_data"]
        name_display = full_name.strip()
        box_color = (0, 255, 0) # Verde para conhecido
        text_color = (0, 255, 0)

    cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
    
    # Lógica para desenhar texto com Pillow (melhor para acentos) ou OpenCV
    y_text = y - 10 if y - 10 > 10 else y + h + 20
    cv2.putText(frame, name_display, (x, y_text), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)


def execute_recognition_session(user_email):
    if not DEEPFACE_AVAILABLE:
        messagebox.showerror("DeepScan - Erro", "A biblioteca DeepFace não está instalada.")
        return
    if not user_email:
        messagebox.showerror("DeepScan - Erro", "Email do usuário não fornecido.")
        return

    faces_path, info_path = utils.get_user_specific_paths(user_email)
    print(f"[DeepScan] Iniciando para: {user_email}")

    # Pré-carregamento de modelos
    if not SESSION_CACHE["models_loaded"]:
        try:
            print("[DSC_INFO] Pré-carregando modelos DeepFace...")
            DeepFace.build_model(config.DSC_RECOGNITION_MODEL)
            SESSION_CACHE["models_loaded"] = True
            print(f"[DSC_INFO] Modelo '{config.DSC_RECOGNITION_MODEL}' pré-carregado.")
        except Exception as e:
            messagebox.showerror("DeepScan - Erro", f"Erro ao carregar modelos: {e}")
            return

    # Carregar dados do usuário (forçando recarregamento a cada sessão)
    person_info = _load_person_info(info_path, force_reload=True)
    known_embeddings = _load_known_faces(faces_path, person_info, force_reload=True)

    if not known_embeddings:
        msg = "Nenhum rosto conhecido foi carregado. Todos serão marcados como 'Desconhecido'."
        messagebox.showwarning("DeepScan - Sem Dados", msg)
        print(f"[DSC_AVISO] {msg}")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("DeepScan - Erro", "Não foi possível abrir a webcam.")
        return

    cv2.namedWindow(config.DSC_APP_WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(config.DSC_APP_WINDOW_NAME, config.DSC_WINDOW_WIDTH, config.DSC_WINDOW_HEIGHT)
    
    print(f"\n[DSC_INFO] Pressione Q ou E para sair.")
    
    running = True
    while running:
        ret, frame = cap.read()
        if not ret: break

        try:
            # Usa a função find para uma abordagem mais direta e otimizada
            found_faces = DeepFace.find(
                img_path=frame,
                db_path=faces_path,
                model_name=config.DSC_RECOGNITION_MODEL,
                detector_backend=config.DSC_DETECTION_MODEL,
                distance_metric='cosine',
                enforce_detection=False,
                silent=True
            )

            # DeepFace.find retorna uma lista de DataFrames, um para cada rosto detectado
            for df in found_faces:
                if not df.empty:
                    # Pega a melhor correspondência (menor distância)
                    best_match = df.iloc[0]
                    identity_path = best_match['identity']
                    
                    # Extrai o ID do arquivo (ex: '.../Rostos/001.jpg' -> '001')
                    match_id = re.search(r"(\d{3})", os.path.basename(identity_path))
                    if match_id:
                        person_id = match_id.group(1).upper()
                        person_data = {"person_data": person_info.get(person_id, ("Desconhecido", ""))}
                        
                        # Pega as coordenadas do rosto detectado
                        x, y, w, h = best_match['source_x'], best_match['source_y'], best_match['source_w'], best_match['source_h']
                        _draw_face_info(frame, person_data, x, y, w, h, is_identified=True)

        except Exception as e:
            # Se DeepFace.find falhar (ex: nenhum rosto detectado), apenas continue
            pass

        cv2.imshow(config.DSC_APP_WINDOW_NAME, frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key in [ord('q'), ord('e')]:
            running = False
        try:
            if cv2.getWindowProperty(config.DSC_APP_WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                running = False
        except cv2.error:
            running = False

    cap.release()
    cv2.destroyAllWindows()
    for _ in range(5): cv2.waitKey(1)
    print(f"[DSC_INFO] Sessão DeepScan encerrada para '{user_email}'.")