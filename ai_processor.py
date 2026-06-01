import os
import sys
import json
import requests

# --- 配置區 ---
# 提示詞模板
PROMPT_TEMPLATE = """
請將以下科技或攝影產品新聞改寫為繁體中文，並嚴格區分為以下兩個部分，中間使用 [SPLIT] 符號隔開：

[第一部分：新聞正文]
要求：文風必須極其「嚴肅、客觀、專業」，專注於產品規格、技術數據與事實。

[SPLIT]

[第二部分：小編點評]
要求：文風轉變為「幽默輕鬆、如老朋友話家常」。以專業但毫無架子的角度點評這個產品，點出優缺點，引導讀者討論。

原文內容：
{raw_text}
"""

def load_providers():
    with open("ai_providers.json", "r", encoding="utf-8") as f:
        return json.load(f)

def call_gemini(url, api_key, prompt):
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(f"{url}?key={api_key}", json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()['candidates'][0]['content']['parts'][0]['text']

def call_openai_compatible(url, api_key, model, prompt):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
    response = requests.post(url, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

def get_raw_news():
    """
    抓取原始新聞。
    目前為模擬數據，實際使用可接入 RSS 抓取邏輯。
    """
    # 範例數據：Sony 新相機新聞
    return {
        "title": "Sony A7C II Update",
        "content": "Sony announced a new lightweight content-creation camera with AI tracking and enhanced cooling system, pricing at $799.",
        "url": "https://example.com/sony-news"
    }

def main():
    # 1. 獲取原始新聞
    news_data = get_raw_news()
    raw_news_text = news_data["content"]
    prompt = PROMPT_TEMPLATE.format(raw_text=raw_news_text)
    
    # 2. 遍歷 AI 提供商進行改寫
    providers = load_providers()
    final_result = None
    
    for provider in providers:
        api_key = os.getenv(provider["key_env"])
        if not api_key:
            print(f"⚠️ 跳過 {provider['name']} (未設定 API Key)")
            continue
            
        print(f"🚀 嘗試使用 {provider['name']}...")
        try:
            if provider["type"] == "gemini":
                final_result = call_gemini(provider["url"], api_key, prompt)
            else:
                final_result = call_openai_compatible(provider["url"], api_key, provider["model"], prompt)
                
            if final_result:
                print(f"✅ {provider['name']} 成功！")
                break
        except Exception as e:
            print(f"❌ {provider['name']} 失敗: {str(e)}")

    if not final_result:
        print("🚨 所有 AI API 皆不可用！")
        sys.exit(1)

    # 3. 拆分文風
    try:
        if "[SPLIT]" in final_result:
            content_parts = final_result.split("[SPLIT]")
            news_content = content_parts[0].replace("[第一部分：新聞正文]", "").strip()
            editor_review = content_parts[1].replace("[第二部分：小編點評]", "").strip()
        else:
            # 容錯處理：如果 AI 沒有按格式輸出
            news_content = final_result.strip()
            editor_review = "這款新品挺有意思的，大家怎麼看？歡迎留言聊聊！"
    except Exception:
        news_content = final_result.strip()
        editor_review = "這款新品挺有意思的，大家怎麼看？歡迎留言聊聊！"

    # 4. 打包數據發送至遠端伺服器
    # 這裡可以根據新聞標題進行簡單改寫，或者直接使用 AI 輸出的內容
    payload = {
        "title": "AI 推播：" + news_data["title"], 
        "content": news_content,
        "editor_review": editor_review,
        "category": "Tech-News",
        "tags": "AI, Tech, Automation",
        "img_url": "", 
        "source_url": news_data["url"]
    }
    
    target_url = os.getenv("SERVER_API_URL")
    sync_token = os.getenv("SYNC_TOKEN")
    
    if target_url and sync_token:
        headers = {"X-Secure-Token": sync_token, "Content-Type": "application/json"}
        try:
            res = requests.post(target_url, headers=headers, json=payload, timeout=10)
            print(f"📦 同步至遠端伺服器 狀態碼: {res.status_code}")
            print(f"回傳訊息: {res.text}")
        except Exception as e:
            print(f"❌ 同步失敗: {str(e)}")
    else:
        print("⚠️ 未設定 SERVER_API_URL 或 SYNC_TOKEN，跳過同步。")

if __name__ == "__main__":
    main()
