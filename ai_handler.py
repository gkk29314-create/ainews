import google.generativeai as genai
import requests
import os

class AIHandler:
    def __init__(self, provider="gemini", api_key=None):
        self.provider = provider
        self.api_key = api_key
        if provider == "gemini":
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        elif provider == "groq":
            self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def rewrite_content(self, title, content, style_guide="專業正文 + 幽默點評"):
        prompt = f"""
        你是一位專業的新聞小編。請根據以下新聞內容進行改寫。
        
        要求：
        1. 標題要吸引人，且保留原意。
        2. 正文部分要專業、精煉。
        3. 最後增加一個「小編點評」環節，語氣要幽默、犀利或帶有前瞻性。
        4. 使用 Markdown 格式輸出。
        
        風格指南：{style_guide}
        
        原文標題：{title}
        原文內容：{content}
        
        改寫後的內容：
        """
        
        if self.provider == "gemini":
            return self._call_gemini(prompt)
        elif self.provider == "groq":
            return self._call_groq(prompt)
        return None

    def _call_gemini(self, prompt):
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini 改寫失敗: {e}")
            return None

    def _call_groq(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "mixtral-8x7b-32768",
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"Groq 改寫失敗: {e}")
            return None
