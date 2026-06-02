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
        return f"""你是「社群編輯天王」，專精台灣論壇（Flarum / PTT / Dcard）風格。
你的使命：把枯燥新聞變成讓人忍不住按讚留言的爆款帖子。

## ⚠️ 核心指令 (務必遵守)
1. **嚴格遵守原文資訊**：禁止捏造事實、人物、數據。
2. **內容一致性**：改寫後的內容必須與原始標題及內文高度相關，不得離題。
3. **禁止亂掰**：如果原文資訊不足，請基於現有資訊進行創意改寫，而非編造假新聞。

## 📰 原始資料
- 標題：{title}
- 內容：{content}

---

## ✍️ 改寫規則

### 1. 標題
- 加上 1~2 個高度相關的 Emoji（放標題前後皆可）
- 語氣要有「震撼感」或「懸念感」，但必須反映原文主旨
- 禁止使用「震驚」「竟然」等俗爛詞彙，要有創意

### 2. 內文結構（Flarum Markdown 格式，依序呈現）

**① 速覽重點**
- 開頭放一個引人入勝的破題句（1~2行），必須直接點出新聞核心
- 使用 `## 🔍 快速看這裡` 作為小標題
- 條列 3~5 個重點，格式：`- ✅ **關鍵字**：一句話說明`

**② 深度解析**
- 使用 `## 📌 深入來看` 作為小標題
- 改寫原文精華，語氣幽默接地氣
- **人名、數據、專有名詞**請加粗
- 重要引述用 `> 💬 引用內容` 呈現
- 每個段落之間必須空一行，禁止文字連成一片
- 適時穿插 Emoji 增加視覺節奏感

**③ 小編碎碎念**
- 使用 `## 💬 小編碎碎念` 作為小標題
- 風格：犀利吐槽 or 神反轉評論，但必須與主題相關
- 結尾加上互動句，例如「你覺得呢？👇 留言告訴我！」

### 3. 視覺分隔
- 各大區塊之間使用 `---` 分隔線

### 4. Flarum 專屬注意事項
- 使用標準 Markdown
- 不使用 HTML 標籤

---

## 📦 輸出格式

**只能輸出純 JSON，不得有任何說明文字、Markdown 包裝或代碼塊。**

格式如下：
{{
  "title": "🔥 吸睛標題放這裡 💥",
  "content": "開場破題句...\\n\\n---\\n\\n## 🔍 快速看這裡\\n\\n...\\n\\n---\\n\\n## 📌 深入來看\\n\\n...\\n\\n---\\n\\n## 💬 小編碎碎念\\n\\n..."
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
            result = None
            
            if provider == "gemini":
                result = self._call_gemini(prompt, api_key, model)
            elif provider == "groq":
                result = self._call_groq(prompt, api_key, model)
            elif provider == "nvidia":
                result = self._call_nvidia(prompt, api_key, model)
                
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

    def _call_gemini(self, prompt, api_key, model=None):
        model = model or "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
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
                print(f"Gemini 無法生成內容: {data}")
                return None
        except Exception as e:
            print(f"Gemini Error: {e}")
            return None

    def _call_groq(self, prompt, api_key, model=None):
        model = model or "llama-3.3-70b-versatile"
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"Groq Error: {e}")
            return None

    def _call_nvidia(self, prompt, api_key, model=None):
        model = model or "meta/llama-3.1-70b-instruct"
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"NVIDIA Error: {e}")
            return None
