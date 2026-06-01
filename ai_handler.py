import google.generativeai as genai
import requests
import os

class AIHandler:
    def __init__(self, keys):
        """
        keys: 字典，包含 gemini, groq, nvidia 的金鑰
        """
        self.keys = keys
        # 初始化 Gemini
        if keys.get("gemini"):
            genai.configure(api_key=keys["gemini"])
            self.gemini_model = genai.GenerativeModel('gemini-pro')
        
    def rewrite_content(self, title, content, style_guide="專業正文 + 幽默點評"):
        prompt = f"""
        你是一位專業的新聞小編。請根據以下新聞內容進行改寫。
        要求：標題吸引人、正文專業精煉、結尾有幽默點評。使用 Markdown。
        
        原文標題：{title}
        原文內容：{content}
        """
        
        # 遞補順序：Gemini -> Groq -> NVIDIA
        providers = ["gemini", "groq", "nvidia"]
        
        for provider in providers:
            api_key = self.keys.get(provider)
            if not api_key:
                continue
                
            print(f"🤖 嘗試使用 {provider.upper()} 進行改寫...")
            result = None
            
            if provider == "gemini":
                result = self._call_gemini(prompt)
            elif provider == "groq":
                result = self._call_groq(prompt, api_key)
            elif provider == "nvidia":
                result = self._call_nvidia(prompt, api_key)
                
            if result:
                print(f"✅ {provider.upper()} 改寫成功！")
                return result
            else:
                print(f"⚠️ {provider.upper()} 失敗，嘗試下一個備援 AI...")
                
        return None

    def _call_gemini(self, prompt):
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini 錯誤: {e}")
            return None

    def _call_groq(self, prompt, api_key):
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": "mixtral-8x7b-32768",
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"Groq 錯誤: {e}")
            return None

    def _call_nvidia(self, prompt, api_key):
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": "meta/llama-3.1-405b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "top_p": 0.7,
            "max_tokens": 1024,
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"NVIDIA 錯誤: {e}")
            return None
