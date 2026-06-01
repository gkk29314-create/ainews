import requests
import json
import re
import time

class AIHandler:
    def __init__(self, keys):
        self.keys = keys

    def _safe_json_parse(self, text):
        """強健的 JSON 解析，處理 Markdown 代碼塊或雜訊"""
        try:
            # 移除不可見字元
            text = re.sub(r'[\x00-\x1F\x7F]', '', text)
            # 嘗試直接解析
            return json.loads(text)
        except:
            # 嘗試使用正則提取 { ... }
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    return None
        return None

    def build_prompt(self, title, content):
        return f"""
你是一位充滿活力、說話接地氣的專業新聞編輯，擅長將生硬的科技資訊轉化為引人入勝的社群貼文。

請根據以下內容進行改寫：
原文標題：{title}
原文內容：{content}

要求：
1. 標題要吸引人（Hook），帶點幽默或前瞻性。
2. 正文要專業且精煉，使用 Markdown 格式（加粗、列表等）。
3. 結尾必須有一個「小編點評」環節，語氣要犀利或感性。
4. 語言風格：使用台灣繁體中文習慣用語（如：螢幕、電腦、數據、軟體）。

請嚴格依照以下 JSON 格式輸出：
{{
  "title": "吸引人的標題",
  "content": "改寫後的正文內容（含小編點評）"
}}
"""

    def rewrite_content(self, title, content):
        prompt = self.build_prompt(title, content)
        providers = ["gemini", "groq", "nvidia"]
        
        for provider in providers:
            api_key = self.keys.get(provider)
            if not api_key:
                continue
                
            print(f"🤖 正在嘗試 {provider.upper()}...")
            result = None
            
            if provider == "gemini":
                result = self._call_gemini(prompt, api_key)
            elif provider == "groq":
                result = self._call_groq(prompt, api_key)
            elif provider == "nvidia":
                result = self._call_nvidia(prompt, api_key)
                
            if result:
                parsed = self._safe_json_parse(result)
                if parsed and "title" in parsed and "content" in parsed:
                    print(f"✅ {provider.upper()} 改寫成功")
                    return parsed
                else:
                    print(f"⚠️ {provider.upper()} 輸出格式錯誤，嘗試下一個...")
            else:
                print(f"⚠️ {provider.upper()} 調用失敗...")
                
        return None

    def _call_gemini(self, prompt, api_key):
        # 使用 REST API 直連，避開 SDK 穩定性問題
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"Gemini Error: {e}")
            return None

    def _call_groq(self, prompt, api_key):
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"Groq Error: {e}")
            return None

    def _call_nvidia(self, prompt, api_key):
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": "meta/llama-3.1-70b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"NVIDIA Error: {e}")
            return None
