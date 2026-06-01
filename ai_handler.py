import google.generativeai as genai
import requests
import os
import json

class AIHandler:
    def __init__(self, keys):
        self.keys = keys
        if keys.get("gemini"):
            try:
                genai.configure(api_key=keys["gemini"])
                # 改用更穩定且免費的 1.5-flash 模型
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                print(f"Gemini 初始化失敗: {e}")
                self.gemini_model = None
        else:
            self.gemini_model = None
        
    def rewrite_content(self, title, content, style_guide="專業正文 + 幽默點評"):
        prompt = f"""
        你是一位專業的新聞小編。請根據以下新聞內容進行改寫。
        要求：標題吸引人、正文專業精煉、結尾有幽默點評。使用 Markdown 格式。
        
        原文標題：{title}
        原文內容：{content}
        """
        
        providers = ["gemini", "groq", "nvidia"]
        
        for provider in providers:
            api_key = self.keys.get(provider)
            if not api_key:
                continue
                
            print(f"🤖 嘗試使用 {provider.upper()}...")
            result = None
            
            if provider == "gemini" and self.gemini_model:
                result = self._call_gemini(prompt)
            elif provider == "groq":
                result = self._call_groq(prompt, api_key)
            elif provider == "nvidia":
                result = self._call_nvidia(prompt, api_key)
                
            if result:
                return result
            
        print("❌ 所有 AI 接口均調用失敗")
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
        # 使用最新的 Llama 3.1 模型，這是目前 Groq 最穩定的
        data = {
            "model": "llama-3.1-70b-versatile",
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            resp_json = response.json()
            if 'choices' in resp_json:
                return resp_json['choices'][0]['message']['content']
            else:
                print(f"Groq API 報錯: {resp_json.get('error', {}).get('message', '未知錯誤')}")
                return None
        except Exception as e:
            print(f"Groq 請求失敗: {e}")
            return None

    def _call_nvidia(self, prompt, api_key):
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        # 確保模型名稱完全正確
        data = {
            "model": "meta/llama-3.1-405b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code != 200:
                print(f"NVIDIA API 錯誤狀態碼: {response.status_code}, 內容: {response.text}")
                return None
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"NVIDIA 請求失敗: {e}")
            return None
