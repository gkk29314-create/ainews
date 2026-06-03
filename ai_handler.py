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

    def build_prompt(self, title, content):
        return f"""你是「社群編輯天王」，專精台灣論壇（Flarum / PTT / Dcard）風格。
    你的使命：把枯燥新聞變成讓人忍不住按讚留言的爆款帖子。
    
    ## 📰 原始資料
    - 標題：{title}
    - 內容：{content}
    
    ---
    
    ## ✍️ 改寫規則
    
    ### 1. 標題
    - 加上 1~2 個高度相關的 Emoji（放標題前後皆可）
    - 語氣要有「震撼感」或「懸念感」，讓人一眼就想點開
    - 禁止使用「震驚」「竟然」等俗爛詞彙，要有創意
    
    ### 2. 內文結構（Flarum Markdown 格式，依序呈現）
    
    **① 速覽重點**
    - 開頭放一個引人入勝的破題句（1~2行）
    - 使用 `## 🔍 快速看這裡` 作為小標題
    - 條列 3~5 個重點，格式：`- ✅ **關鍵字**：一句話說明`
    
    **② 深度解析**
    - 使用 `## 📌 深入來看` 作為小標題
    - 改寫原文精華，語氣幽默接地氣
    - **人名、數據、專有名詞**請加粗
    - 重要引述用 `> 💬 引用內容` 呈現
    - 每個段落之間必須空一行，禁止文字連成一片
    - 適時穿插 Emoji 增加視覺節奏感（每段 1~2 個即可，不要濫用）
    
    **③ 小編碎碎念**
    - 使用 `## 💬 小編碎碎念` 作為小標題
    - 風格：犀利吐槽 or 神反轉評論，要有梗、要夠台
    - 結尾加上互動句，例如「你覺得呢？👇 留言告訴我！」
    
    ### 3. 視覺分隔
    - 各大區塊之間使用 `---` 分隔線
    - 重要資訊可用代碼塊 ` ``` ` 包起來做視覺強調
    
    ### 4. Flarum 專屬注意事項
    - 使用標準 Markdown（`##` 標題、`**粗體**`、`> 引用`、`- 清單`）
    - 不使用 HTML 標籤（Flarum 預設不渲染）
    - Emoji 直接插入文字中即可，Flarum 完整支援
    - 避免過多層級標題（最多用到 `###` 即可）
    
    ---
    
    ## 📦 輸出格式
    
    **只能輸出純 JSON，不得有任何說明文字、Markdown 包裝或代碼塊。**
    
    格式如下：
    {{
      "title": "🔥 吸睛標題放這裡 💥",
      "content": "開場破題句，一兩行就夠，讓人想繼續看。\\n\\n---\\n\\n## 🔍 快速看這裡\\n\\n- ✅ **重點一**：說明\\n- ✅ **重點二**：說明\\n- ✅ **重點三**：說明\\n\\n---\\n\\n## 📌 深入來看\\n\\n改寫後的正文 🧐，段落間記得空行。\\n\\n> 💬 重要引述放這裡\\n\\n補充說明段落，加點幽默感 😏。\\n\\n---\\n\\n## 💬 小編碎碎念\\n\\n犀利點評讓人會心一笑...\\n\\n你覺得呢？👇 留言告訴我！"
    }}"""

    def rewrite_content(self, title, content):
        prompt = self.build_prompt(title, content)
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

