#Classe para interagir com a API do Gemini

# -*- coding: utf-8 -*-
import json
from tkinter import messagebox
from google import genai


class LanguageService:
    def __init__(self, api_key):
        self.is_configured = False
        if not api_key or api_key == "SUA_CHAVE_DE_API_AQUI":
            print("[API WARNING] Chave da API do Gemini não fornecida.")
            return
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.is_configured = True
            print("API do Gemini configurada com sucesso.")
        except Exception as e:
            print(f"Erro ao configurar a API do Gemini: {e}")
            messagebox.showwarning(
                "API não configurada",
                f"A chave de API do Gemini é inválida ou houve um erro.\n{e}\nA tradução está desabilitada."
            )

    def translate_ui_texts(self, texts_dict, target_language_code):
        if not self.is_configured:
            messagebox.showerror("Erro de API", "A API do Gemini não está configurada para tradução.")
            return None

        prompt = f"""
        Traduza os seguintes textos de interface de usuário para o idioma com o código '{target_language_code}'.
        Responda APENAS com um objeto JSON válido, usando as mesmas chaves do objeto original.

        Objeto original em português:
        {json.dumps(texts_dict, indent=2, ensure_ascii=False)}

        Sua resposta em JSON:
        """
        try:
            print(f"Enviando para o Gemini para tradução para '{target_language_code}'...")
            response = self.model.generate_content(prompt)
            cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
            translated_texts = json.loads(cleaned_response)
            print("Tradução recebida com sucesso.")
            return translated_texts
        except Exception as e:
            print(f"Erro durante a tradução: {e}")
            messagebox.showerror(
                "Erro de Tradução",
                f"Não foi possível traduzir os textos.\nVerifique sua conexão e a chave de API.\n\nErro: {e}"
            )
            return None