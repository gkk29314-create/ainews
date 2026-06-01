import json
import requests
import feedparser
import os
import time
from ai_handler import AIHandler

# 配置資訊
CONFIG = {
    "SERVER_API_URL": os.environ.get("SERVER_API_URL"),
    "FLARUM_API_KEY": os.environ.get("FLARUM_API_KEY"),
    "AI_KEYS": {
        "gemini": os.environ.get("GEMINI_API_KEY"),
        "groq": os.environ.get("GROQ_API_KEY"),
        "nvidia": os.environ.get("NVIDIA_API_KEY")
    }
}

HISTORY_FILE = "history.json"

def load_json(path):
    if not os.path.exists(path):
        if "mapping" in path: return {"mappings": []}
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return []

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def post_to_flarum(user_id, tag_id, title, content):
    if not CONFIG["SERVER_API_URL"]: return False
    url = f"{CONFIG['SERVER_API_URL']}/api/discussions"
    
    # 最終修正：Flarum 身份代理標準標頭 (不要有空格)
    # 注意：資料庫中的 api_keys.user_id 必須為 NULL 才能冒充他人
    headers = {
        "Authorization": f"Token {CONFIG['FLARUM_API_KEY']};userId={user_id}",
        "Content-Type": "application/json"
    }
    
    print(f"✉️  正在執行身份冒充 -> 目標 UserID: {user_id}")
    
    payload = {
        "data": {
            "type": "discussions",
            "attributes": {"title": title, "content": content},
            "relationships": {"tags": {"data": [{"type": "tags", "id": str(tag_id)}]}}
        }
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            return True
        else:
            print(f"❌ API 回應: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
        return False

def run_bot():
    mappings = load_json("mapping.json").get("mappings", [])
    rss_sources = load_json("rss_sources.json")
    history = load_json(HISTORY_FILE)
    if not isinstance(history, list): history = []
    
    ai = AIHandler(CONFIG["AI_KEYS"])
    mapping_dict = {m["channel"]: m for m in mappings}
    new_history = list(history)
    
    for source in rss_sources:
        print(f"🔍 抓取源: {source['name']}")
        feed = feedparser.parse(source['url'])
        for entry in feed.entries[:3]:
            if entry.link in history: continue
            
            category = source["category"]
            if category in mapping_dict:
                mapping = mapping_dict[category]
                print(f"🤖 處理新聞: {entry.title}")
                
                ai_result = ai.rewrite_content(entry.title, entry.description)
                
                if ai_result:
                    if post_to_flarum(mapping["user_id"], mapping["tag_id"], ai_result["title"], ai_result["content"]):
                        print(f"✅ 發帖成功")
                        new_history.append(entry.link)
                        time.sleep(3)
        
        save_json(HISTORY_FILE, new_history[-200:])
        print("-" * 20)

if __name__ == "__main__":
    if CONFIG["FLARUM_API_KEY"] and CONFIG["SERVER_API_URL"]:
        run_bot()
    else:
        print("❌ 環境變數缺失")
