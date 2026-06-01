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
你是一位充滿魅力、說話超級接地氣的專業新聞編輯。你的任務是將生硬的新聞改造成像是在社群平台（如 Thread 或 FB）上會被瘋傳的有趣貼文。

請根據以下內容進行改寫：
原文標題：{title}
原文內容：{content}

要求：
1. **標題要 Hook**：要有共鳴、好笑或讓人想點進去看。
2. **內文排版（重點！）**：
   - 使用 Markdown 語法讓版面乾淨美觀。
   - 重點詞彙請 **加粗**。
   - 使用「-」或「1.」列表來整理重點，不要只有一大團文字。
   - 適當加入 Emoji 讓氣氛更活潑。
3. **語氣風格**：
   - 拋棄死板的教科書語氣，用生活化的、幽默的口吻說話。
   - 想像你在跟好朋友分享這件事。
4. **小編點評**：
   - 結尾必須有一個「小編碎碎念」環節。
   - 內容要犀利、幽默，或帶一點個人情緒（例如：這太狂了、我的錢包在哭）。
5. **語言習慣**：使用台灣繁體中文（如：滑手機、很正、超狂、沒在開玩笑）。

請嚴格依照以下 JSON 格式輸出：
{{
  "title": "😂 標題要加 Emoji 喔",
  "content": "### 🚀 內容大綱\n\n這裡是改寫後的正文...\n\n---\n\n#### 💬 小編碎碎念\n\n這裡是很幽默的點評..."
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
