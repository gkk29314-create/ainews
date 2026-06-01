import json
import requests
import feedparser
import os
import time
from ai_handler import AIHandler

# 配置資訊
CONFIG = {
    "FLARUM_URL": "https://manprompt.qzz.io",
    "FLARUM_API_KEY": os.environ.get("FLARUM_API_KEY"),
    "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
    "GROQ_API_KEY": os.environ.get("GROQ_API_KEY"),
    "AI_PROVIDER": os.environ.get("AI_PROVIDER", "gemini") # 預設使用 gemini
}

HISTORY_FILE = "history.json"

def load_json(path):
    if not os.path.exists(path):
        return {"mappings": []} if "mapping" in path else []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def post_to_flarum(user_id, tag_id, title, content):
    url = f"{CONFIG['FLARUM_URL']}/api/discussions"
    headers = {
        "Authorization": f"Token {CONFIG['FLARUM_API_KEY']}; userId={user_id}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "data": {
            "type": "discussions",
            "attributes": {
                "title": title,
                "content": content
            },
            "relationships": {
                "tags": {
                    "data": [
                        {"type": "tags", "id": str(tag_id)}
                    ]
                }
            }
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            print(f"✅ 發帖成功！標題: {title}")
            return True
        else:
            print(f"❌ 發帖失敗: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        print(f"❌ API 請求異常: {e}")
        return False

def run_bot():
    mappings = load_json("mapping.json")["mappings"]
    rss_sources = load_json("rss_sources.json")
    history = load_json(HISTORY_FILE)
    
    # 初始化 AI
    api_key = CONFIG["GEMINI_API_KEY"] if CONFIG["AI_PROVIDER"] == "gemini" else CONFIG["GROQ_API_KEY"]
    ai = AIHandler(provider=CONFIG["AI_PROVIDER"], api_key=api_key)
    
    mapping_dict = {m["channel"]: m for m in mappings}
    
    new_history = list(history)
    
    for source in rss_sources:
        print(f"🔍 正在抓取: {source['name']}")
        feed = feedparser.parse(source['url'])
        
        # 遍歷最新的 3 條新聞，避免遺漏
        for entry in feed.entries[:3]:
            url = entry.link
            if url in history:
                print(f"⏭️  跳過已發布內容: {entry.title}")
                continue
            
            category = source["category"]
            if category in mapping_dict:
                mapping = mapping_dict[category]
                
                print(f"🤖 正在為 [{mapping['display_name']}] 進行 AI 改寫...")
                new_content = ai.rewrite_content(entry.title, entry.description)
                
                if new_content:
                    if post_to_flarum(mapping["user_id"], mapping["tag_id"], entry.title, new_content):
                        new_history.append(url)
                        # 每次發帖後稍微停頓，避免頻率限制
                        time.sleep(3)
        
        # 只保留最近 200 條歷史記錄
        save_json(HISTORY_FILE, new_history[-200:])
        print("-" * 30)

if __name__ == "__main__":
    if not CONFIG["FLARUM_API_KEY"]:
        print("❌ 錯誤: 請設定 FLARUM_API_KEY 環境變數")
    else:
        run_bot()
