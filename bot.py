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

# 標籤父子關係映射 (根據 tags.sql)
TAG_RELATIONS = {
    "9": "3",  # 產業應用 -> 數位 3C 硬體
    "17": "3", # 數位相機 -> 數位 3C 硬體
    "18": "3", # 電腦硬體 -> 數位 3C 硬體
    "45": "44", # 商業與製造 -> 應用案例
    "46": "44", # 醫療與健康 -> 應用案例
    "47": "44", # 教育與學習 -> 應用案例
    "22": "4",  # 框架與平台 -> 工具與資源
    "24": "4",  # 學習資源 -> 工具與資源
    "25": "4"   # 工具分享 -> 工具與資源
}

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
    
    # 建立標籤列表，包含父標籤 (如果有的話)
    tags_data = [{"type": "tags", "id": str(tag_id)}]
    if str(tag_id) in TAG_RELATIONS:
        tags_data.append({"type": "tags", "id": TAG_RELATIONS[str(tag_id)]})
    
    headers = {
        "Authorization": f"Token {CONFIG['FLARUM_API_KEY']};userId={user_id}",
        "Content-Type": "application/json"
    }
    
    print(f"✉️  正在執行身份冒充 -> 目標 UserID: {user_id}, Tags: {[t['id'] for t in tags_data]}")
    
    payload = {
        "data": {
            "type": "discussions",
            "attributes": {"title": title, "content": content},
            "relationships": {"tags": {"data": tags_data}}
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

    try:
        feed = feedparser.parse(source['url'])

        for entry in feed.entries[:3]:

            try:
                if getattr(entry, "link", "") in history:
                    continue

                category = source["category"]

                if category not in mapping_dict:
                    continue

                mapping = mapping_dict[category]

                title = getattr(entry, "title", "無標題")

                print(f"🤖 處理新聞: {title}")

                content = ""

                if hasattr(entry, "description"):
                    content = entry.description

                elif hasattr(entry, "summary"):
                    content = entry.summary

                elif hasattr(entry, "content") and entry.content:
                    content = entry.content[0].get("value", "")

                if not content:
                    print("⚠️ 找不到文章內容，跳過")
                    continue

                content = str(content)[:8000]

                ai_result = ai.rewrite_content(
                    title,
                    content
                )

                if not ai_result:
                    print("⚠️ AI 改寫失敗")
                    continue

                success = post_to_flarum(
                    mapping["user_id"],
                    mapping["tag_id"],
                    ai_result["title"],
                    ai_result["content"]
                )

                if success:
                    print("✅ 發帖成功")
                    new_history.append(getattr(entry, "link", ""))
                    time.sleep(3)

            except Exception as e:
                print(f"❌ 處理文章失敗: {e}")
                continue

    except Exception as e:
        print(f"❌ RSS 解析失敗: {e}")

    save_json(HISTORY_FILE, new_history[-200:])
    print("-" * 20)
if __name__ == "__main__":
    if CONFIG["FLARUM_API_KEY"] and CONFIG["SERVER_API_URL"]:
        run_bot()
    else:
        print("❌ 環境變數缺失")
