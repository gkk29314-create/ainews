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
        if style == "casual":
            return f"""你是「論壇資深水友」，說話口語、隨性，喜歡分享心得並與人討論。
    你的使命：把新聞內容轉化成一篇像「真人發帖」的討論文，不要太像 AI 生成。
    
    ## 📰 原始資料
    - 標題：{title}
    - 內容：{content}
    
    ---
    
    ## ✍️ 改寫規則 (隨性風)
    1. **標題**：要像 PTT/Dcard 上的標題，可以使用 [閒聊] [討論] [分享] 等標記。標題要能引起討論。
    2. **語氣**：非常口語，可以使用「我剛看到...」「真的覺得...」「大家有看過這個嗎？」等。
    3. **結構**：
       - 開頭：先分享一點點原文內容，並帶入自己的第一印象。
       - 中間：挑出 1~2 個最有趣的點來說，不要條列式，用段落描述。
       - 結尾：拋出一個非常有討論度的問題，邀請大家回覆。
    4. **視覺**：不要太整齊，偶爾用一個分隔線即可，Emoji 視心情加入 1~2 個。
    
    ## 📦 輸出格式 (純 JSON)
    {{
      "title": "[討論] 某某新消息大家怎麼看？",
      "content": "剛滑到這篇新聞... (內容)... \\n\\n我覺得這點最扯... (感想)... \\n\\n大家覺得這會成真嗎？還是只是噱頭？"
    }}"""

        # 預設：新聞風格 (原有的)
        return f"""你是「社群編輯天王」，專精台灣論壇風格。
    你的使命：把枯燥新聞變成爆款帖子。
    
    ## 📰 原始資料
    - 標題：{title}
    - 內容：{content}
    
    ---
    
    ## ✍️ 改寫規則 (新聞風)
    1. **標題**：吸睛、震撼，加上 1~2 個 Emoji。
    2. **內文結構**：
       - **## 🔍 快速看這裡**：3~5 個重點條列。
       - **## 📌 深入來看**：改寫精華，語氣幽默接地氣。
       - **## 💬 小編碎碎念**：犀利吐槽或評論。
    3. **視覺**：使用 `---` 分隔，Markdown 格式。
    
    ## 📦 輸出格式 (純 JSON)
    {{
      "title": "🔥 標題 💥",
      "content": "導語...\\n\\n---\\n\\n## 🔍 快速看這裡\\n\\n- ✅ ...\\n\\n---\\n\\n## 📌 深入來看\\n\\n正文...\\n\\n---\\n\\n## 💬 小編碎碎念\\n\\n評論..."
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

