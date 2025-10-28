#Constantes globais para fácil acesso e modificação

# -*- coding: utf-8 -*-

# --- Cores da Interface ---
BACKGROUND_COLOR = "#0A0A0A"
TEXT_COLOR = "#6600EB"
ENTRY_BG_COLOR = "#181818"
BUTTON_BG_COLOR = "#FFFFFF"
PROFILE_ENTRY_BG_COLOR = "#FAFAFA"
PROFILE_ENTRY_FG_COLOR = "#181818"
ERROR_COLOR = "pink"
SUCCESS_COLOR = "lightgreen"
TEXT_ERROR_COLOR = "red"
TEXT_SUCCESS_COLOR = "green"

# --- Sistema de Login e Cadastro ---
DB_FILENAME = "cadastros.txt"
USER_DATA_FIELDS = ["email", "hashed_password", "fullname", "company", "position", "dob"]

# --- Pastas e Arquivos de Dados do Usuário ---
USER_DATA_ROOT_FOLDER = "UserData"
DS_SUBFOLDER_FACES = "Rostos"
DSC_SUBFOLDER_FONTS = "Fontes"
DS_INFO_FILENAME = 'inforos.txt'

# --- Configurações do DeepSave ---
DS_MAX_PHOTOS_PER_PERSON = 5
DS_CAPTURE_WINDOW_NAME = "Deep Save"

# --- Configurações do DeepScan ---
DSC_DETECTION_MODEL = 'opencv'
DSC_RECOGNITION_MODEL = 'Facenet512'
DSC_SIMILARITY_THRESHOLD = 0.40
DSC_FONT_FILENAME = "arial.ttf"
DSC_APP_WINDOW_NAME = "Deep Scan"
DSC_WINDOW_WIDTH = 1280
DSC_WINDOW_HEIGHT = int(DSC_WINDOW_WIDTH * 9 / 16)

# --- Configurações de Idioma ---
LANGUAGES = sorted(["Português", "English", "Deutsch", "Español", "Français", "Italiano", "Nederlands"])
DEFAULT_LANGUAGE = "Português"
LANGUAGE_MAP = {
    "English": "en",
    "Deutsch": "de",
    "Español": "es",
    "Français": "fr",
    "Italiano": "it",
    "Nederlands": "nl"
}
# Mapeamento de chaves de texto da UI para tradução
UI_TEXTS = {
    "settings_title": "Configurações",
    "profile_button": "Perfil",
    "language_button": "Idioma",
    "back_to_deep_button": "Voltar para Deep",
    "language_select_title": "Selecionar Idioma",
    "save_language_button": "Salvar Idioma",
    "back_to_settings_button": "Voltar para Configurações",
}