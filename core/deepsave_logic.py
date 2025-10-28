#Lógica de captura e salvamento de rostos

# -*- coding: utf-8 -*-
import cv2
import os
import time
import re
import config

def get_next_person_id(user_faces_path):
    if not os.path.exists(user_faces_path):
        os.makedirs(user_faces_path, exist_ok=True)
        return "001"
    
    jpg_files = [f for f in os.listdir(user_faces_path) if f.lower().endswith((".jpg", ".jpeg"))]
    if not jpg_files:
        return "001"
        
    pattern = re.compile(r"^(\d{3})")
    numeric_ids = set()
    for filename in jpg_files:
        match = pattern.match(filename)
        if match:
            numeric_ids.add(int(match.group(1)))
            
    if not numeric_ids:
        return "001"
        
    return f"{max(numeric_ids) + 1:03d}"

def generate_photo_filename(person_id, photo_index):
    return f"{person_id}.jpg" if photo_index == 0 else f"{person_id} ({photo_index}).jpg"

def add_person_info(person_id, full_name, gender, user_info_file_path):
    line = f"{person_id}:{full_name},{gender}\n"
    try:
        with open(user_info_file_path, 'a', encoding='utf-8') as f:
            f.write(line)
        print(f"[DS_INFO] Informações de '{full_name}' salvas em {os.path.basename(user_info_file_path)}.")
        return True
    except Exception as e:
        print(f"[DS_ERRO] Não foi possível salvar as informações: {e}")
        return False

def capture_and_save_face(full_image_path_to_save, haar_cascade_path):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[DS_ERRO] Não foi possível abrir a câmera.")
        return False, "camera_error"

    face_cascade = cv2.CascadeClassifier(haar_cascade_path)
    detection_start_time = None
    face_saved = False
    
    print(f"[DS] Preparando para salvar em: {os.path.basename(full_image_path_to_save)}")
    cv2.namedWindow(config.DS_CAPTURE_WINDOW_NAME)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[DS_ERRO] Não foi possível ler o frame da câmera.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
        
        display_frame = frame.copy()
        cv2.putText(display_frame, "Pressione Q ou E para Sair", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

        if len(faces) > 0:
            x, y, w, h = faces[0]
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (102, 0, 235), 2)
            
            if detection_start_time is None:
                detection_start_time = time.time()
                cv2.putText(display_frame, "Rosto detectado!", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            elapsed_time = time.time() - detection_start_time
            
            if elapsed_time <= 3:
                cv2.putText(display_frame, f"Capturando em {3 - int(elapsed_time)}s...", (20, display_frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            else:
                try:
                    cv2.imwrite(full_image_path_to_save, frame[y:y + h, x:x + w])
                    face_saved = True
                    print(f"[DS_OK] Rosto salvo: {os.path.basename(full_image_path_to_save)}")
                    break
                except Exception as e:
                    print(f"[DS_ERRO] Não foi possível salvar a imagem: {e}")
                    detection_start_time = None
        else:
            detection_start_time = None
            cv2.putText(display_frame, "Procurando rosto...", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow(config.DS_CAPTURE_WINDOW_NAME, display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key in [ord('q'), ord('e')]:
            print("[DS] Captura cancelada pelo usuário.")
            break
        
        try:
            if cv2.getWindowProperty(config.DS_CAPTURE_WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                print("[DS] Janela de captura fechada.")
                break
        except cv2.error:
            print("[DS] Janela de captura não encontrada, encerrando.")
            break

    cap.release()
    cv2.destroyAllWindows()
    # Garante que a janela feche em todos os sistemas
    for _ in range(5):
        cv2.waitKey(1)
        
    return face_saved, None