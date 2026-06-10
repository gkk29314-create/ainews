import requests
import json
import re
import time

class AIHandler:
    def __init__(self, keys, config=None):
        self.keys = keys
        # 預設配置
        self.config = config or {
            "priority": ["nvidia", "gemini", "groq"],
            "models": {
                "gemini": "gemini-2.0-flash",
                "groq": "llama-3.3-70b-versatile",
                "nvidia": "meta/llama-3.1-70b-instruct"
            }
        }

    def _retry_request(self, func, *args, **kwargs):
        """簡單的重試機制"""
        max_retries = 2
        for i in range(max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if result:
                    return result
            except Exception as e:
                if i < max_retries:
                    print(f"⚠️ 請求失敗 ({e})，正在進行第 {i+1} 次重試...")
                    time.sleep(2)
                else:
                    raise e
        return None

    def build_prompt(self, title, content, style="news"):
        # 通用的「反 AI 腔調」規則
        anti_ai_rules = """
    ## 🚫 嚴格禁令 (消除 AI 感)
    - 禁止使用：總而言之、不勝枚舉、值得注意的是、不僅如此、讓我們期待、是一個...的過程。
    - 禁止過度禮貌或官宣語氣，不要說「這是一個非常有趣的現象」。
    - 禁止使用「結語/總結」標籤。
    - 禁止在結尾說「希望這篇內容對你有幫助」。
    - 標點符號要自然：少用「！」，多用「...」或「～」，或者乾脆不加標點。
    """

        if style == "viral":
            return f"""你是「論壇話題製造機」，擅長用第一人稱 (POV) 或吐槽語氣引起共鳴。
    你的使命：把新聞內容轉化成一篇讓人忍不住想留言的爆款貼文。

    ## 📰 原始資料
    - 標題：{title}
    - 內容：{content}

    ---

    ## ✍️ 改寫規則 (爆款公式)
    1. **標題**：使用「只有我覺嗎？」、「某某事件的真相」、「(吐槽) 原來這就是...」等具有強烈情緒色彩的標題。
    2. **內文結構 (POV 吐槽流)**：
       - **第一段 (情緒破題)**：用一句話表達你的情緒 (驚訝、不屑、興奮)，例如「看到這則新聞我真的傻眼了...」。
       - **第二段 (重點大白話)**：把新聞重點用「白話文」講一遍，像是講給朋友聽。
       - **第三段 (犀利吐槽)**：抓出新聞中最荒謬或最反直覺的點進行評論。
    3. **互動引導**：結尾不要問「你覺得呢？」，要問「如果你是當事人，你會直接翻臉還是忍下來？」或「這價錢你真的買得下去？」。

    {anti_ai_rules}

    ## 📦 輸出格式 (純 JSON)
    {{
      "title": "標題 (要有情緒感)",
      "content": "內容 (要有段落感，適度留白)"
    }}"""

        if style == "casual":
            return f"""你是「論壇資深水友」，說話口語、隨性，喜歡分享心得並與人討論。
    你的使命：把新聞內容轉化成一篇像「真人發帖」的討論文。

    ## 📰 原始資料
    - 標題：{title}
    - 內容：{content}

    ---

    ## ✍️ 改寫規則 (真實水友感)
    1. **標題**：要像 PTT/Dcard 上的標題，可以使用 [閒聊] [討論] [分享] 等標記。
    2. **語氣**：非常口語，加入一些台灣論壇常用詞彙 (如：母湯、真假、扯、傻眼、真的覺得)。
    3. **結構**：
       - 像是在聊天，不要太整齊，內容要有層次但不要用標題符號 (##)。
       - 挑出 1~2 個最有趣的點，並帶入「我」的觀點。
    4. **視覺**：多用換行來分段，不要擠成一坨。

    {anti_ai_rules}

    ## 📦 輸出格式 (純 JSON)
    {{
      "title": "[閒聊] 剛看到這新聞真的母湯...",
      "content": "剛滑到這篇新聞... (白話敘述)... \\n\\n我覺得這點最扯... (感想)... \\n\\n大家覺得這會成真嗎？"
    }}"""

        # 預設：新聞風格 (專業編輯感)
        return f"""你是「社群編輯天王」，專精台灣論壇風格。
    你的使命：把新聞內容轉化為高資訊量且具吸引力的摘要。

    ## 📰 原始資料
    - 標題：{title}
    - 內容：{content}

    ---

    ## ✍️ 改寫規則 (專業編輯)
    1. **標題**：吸睛且包含重點，加上 1 個 Emoji。
    2. **內文結構**：
       - **## 🔍 懶人包**：3 個核心重點。
       - **## 📌 深入解讀**：改寫精華，語氣接地氣。
       - **## 💬 小編點評**：簡短犀利的評論。

    {anti_ai_rules}

    ## 📦 輸出格式 (純 JSON)
    {{
      "title": "🔥 標題 💥",
      "content": "導語...\\n\\n---\\n\\n## 🔍 懶人包\\n\\n- ✅ ...\\n\\n---\\n\\n## 📌 深入解讀\\n\\n正文...\\n\\n---\\n\\n## 💬 小編點評\\n\\n評論..."
    }}"""


    def rewrite_content(self, title, content, style="news"):
        prompt = self.build_prompt(title, content, style)
        providers = self.config.get("priority", ["nvidia", "gemini", "groq"])
        models = self.config.get("models", {})
        
        for provider in providers:
            api_key = self.keys.get(provider)
            if not api_key:
                continue
                
            model = models.get(provider)
            print(f"🤖 正在嘗試 {provider.upper()} (模型: {model})...")
            
            try:
                result = None
                if provider == "gemini":
                    result = self._retry_request(self._call_gemini, prompt, api_key, model)
                elif provider == "groq":
                    result = self._retry_request(self._call_groq, prompt, api_key, model)
                elif provider == "nvidia":
                    result = self._retry_request(self._call_nvidia, prompt, api_key, model)
                    
                if result:
                    parsed = self._safe_json_parse(result)
                    if parsed and "title" in parsed and "content" in parsed:
                        print(f"✅ {provider.upper()} 改寫成功")
                        return parsed
                    else:
                        print(f"⚠️ {provider.upper()} 輸出格式錯誤，內容: {result[:100]}...")
                else:
                    print(f"⚠️ {provider.upper()} 無結果回傳")
            except Exception as e:
                print(f"⚠️ {provider.upper()} 調用失敗: {e}")
                
        return None

    def _safe_json_parse(self, text):
        """
        嘗試解析 JSON，處理 Markdown 代碼塊和多餘文字
        """
        if not text:
            return None
            
        text = text.strip()
        
        # 1. 嘗試直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
            
        # 2. 嘗試提取 ```json ... ``` 中的內容
        json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
                
        # 3. 嘗試提取第一個 { 和最後一個 } 之間的內容
        brace_match = re.search(r"({.*})", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(1))
            except json.JSONDecodeError:
                pass
                
        return None

    def _call_gemini(self, prompt, api_key, model=None):
        model = model or "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
        }
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        data = response.json()
        if "candidates" in data and data["candidates"]:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        elif "error" in data:
            raise Exception(f"Gemini API Error: {data['error'].get('message', 'Unknown error')}")
        else:
            raise Exception(f"Gemini Unexpected Response: {data}")

    def _call_groq(self, prompt, api_key, model=None):
        model = model or "llama-3.3-70b-versatile"
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        response = requests.post(url, headers=headers, json=data, timeout=60)
        resp_json = response.json()
        if "choices" in resp_json and resp_json["choices"]:
            return resp_json['choices'][0]['message']['content']
        elif "error" in resp_json:
            raise Exception(f"Groq API Error: {resp_json['error'].get('message', 'Unknown error')}")
        else:
            raise Exception(f"Groq Unexpected Response: {resp_json}")

    def _call_nvidia(self, prompt, api_key, model=None):
        model = model or "meta/llama-3.1-70b-instruct"
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        response = requests.post(url, headers=headers, json=data, timeout=60)
        resp_json = response.json()
        if "choices" in resp_json and resp_json["choices"]:
            return resp_json['choices'][0]['message']['content']
        elif "error" in resp_json:
            raise Exception(f"NVIDIA API Error: {resp_json['error'].get('message', 'Unknown error')}")
        else:
            raise Exception(f"NVIDIA Unexpected Response: {resp_json}")

