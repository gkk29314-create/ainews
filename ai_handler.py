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
你是一位充滿魅力、說話超級接地氣的專業新聞編輯，也是一位 Markdown 排版大師。
你的任務是將新聞改造成版面精美、層次分明、語氣幽默的社群貼文。

請根據以下內容進行改寫：
原文標題：{title}
原文內容：{content}

---

### 🎨 貼文製作規則（請嚴格遵守）：

1. **標題 (Title)**：
   - 必須加上 1-2 個相關的 Emoji。
   - 語氣要像震撼彈，讓人一眼就想點。

2. **內文排版 (Formatting) - 這是最重要的一點！**：
   - **分段明確**：段落與段落之間「必須」空一行（使用兩個換行符 \n\n），絕對不能全部擠在一起。
   - **視覺層次**：使用 `###` 或 `####` 作為小標題。
   - **重點加粗**：關鍵字、數據、人名請用 `**加粗**`。
   - **條列清單**：使用 `-` 符號列出 3-5 個新聞重點，增加易讀性。
   - **引用金句**：重要的話可以用 `> ` 引用塊。
   - **分割線**：在正文與小編碎碎念之間使用 `---` 分隔線。

3. **幽默文風 (Style)**：
   - 使用台灣社群風格（Thread/FB/PTT），生活化、幽默、愛吐槽。
   - 結尾的「#### 💬 小編碎碎念」要夠犀利、夠有梗。

---

請嚴格依照以下 JSON 格式輸出：
{{
  "title": "😂 標題要加 Emoji 喔",
  "content": "### 🚀 內容快速看\\n\\n- **重點一**：內容描述\\n- **重點二**：內容描述\\n\\n---\\n\\n### 📝 深入解析\\n\\n這裡放專業改寫後的詳細正文，記得每段都要空行。\\n\\n---\\n\\n#### 💬 小編碎碎念\\n\\n這裡是很幽默的點評..."
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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            data = response.json()
            if "candidates" in data and data["candidates"]:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                print(f"Gemini 無法生成內容（可能觸發過濾）: {data}")
                return None
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
