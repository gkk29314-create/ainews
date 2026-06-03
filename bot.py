import json
import requests
import feedparser
import os
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor
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
history_lock = threading.Lock()
post_lock = threading.Lock()

# 標籤父子關係映射
TAG_RELATIONS = {
    "38": "1", # 科技焦點 -> 新聞趨勢
    "8": "1",  # 未來趨勢 -> 新聞趨勢
    "7": "1",  # 倫理與規範 -> 新聞趨勢
    "9": "3",  # 產業應用 -> 數位 3C 硬體
    "17": "3", # 數位相機 -> 數位 3C 硬體
    "18": "3", # 電腦硬體 -> 數位 3C 硬體
    "45": "44", # 商業與製造 -> 應用案例
    "46": "44", # 醫療與健康 -> 應用案例
    "47": "44", # 教育與學習 -> 應用案例
    "22": "4",  # 框架與平台 -> 工具與資源
    "24": "4",  # 學習資源 -> 工具與資源
    "25": "4",  # 工具分享 -> 工具與資源
    "10": "2",  # 圖像生成 -> 技術交流
    "11": "2",  # 影音生成 -> 技術交流
    "13": "2",  # 文本與程式 -> 技術交流
    "14": "2"   # 智能體與自動化 -> 技術交流
}

def load_json(path):
    if not os.path.exists(path):
        if "mapping" in path: return {"mappings": [], "forum_url": ""}
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return []

def save_json(path, data):
    with history_lock:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def fetch_article_content(url):
    """使用 trafilatura 高效抓取新聞正文"""
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            content = trafilatura.extract(downloaded, include_comments=False, include_tables=False, no_fallback=False)
            return content if content else ""
    except Exception as e:
        print(f"⚠️ Trafilatura 抓取失敗: {e}")
    return ""

def post_to_flarum(user_ids, tag_id, title, content):
    if not CONFIG["SERVER_API_URL"]: 
        print("❌ 錯誤: SERVER_API_URL 未設定")
        return False
        
    url = f"{CONFIG['SERVER_API_URL'].rstrip('/')}/api/discussions"
    
    if isinstance(user_ids, str):
        ids = [i.strip() for i in user_ids.split(",") if i.strip()]
    elif isinstance(user_ids, list):
        ids = user_ids
    else:
        ids = [str(user_ids)]
        
    target_user_id = random.choice(ids)
    
    tags_data = [{"type": "tags", "id": str(tag_id)}]
    if str(tag_id) in TAG_RELATIONS:
        tags_data.append({"type": "tags", "id": TAG_RELATIONS[str(tag_id)]})
    
    headers = {
        "Authorization": f"Token {CONFIG['FLARUM_API_KEY']};userId={target_user_id}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "data": {
            "type": "discussions",
            "attributes": {"title": title, "content": content},
            "relationships": {"tags": {"data": tags_data}}
        }
    }
    
    # 發帖時加上鎖，避免論壇併發衝突
    with post_lock:
        try:
            print(f"✉️  正在發帖 -> UserID: {target_user_id}, Title: {title[:20]}...")
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            if response.status_code == 201:
                time.sleep(1) # 微小間隔
                return True
            else:
                print(f"❌ API 回應: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 請求失敗: {e}")
            return False

def process_entry(entry, source, mapping, ai, history):
    link = getattr(entry, "link", "")
    if not link or link in history:
        return None

    title = getattr(entry, "title", "無標題")
    print(f"🤖 處理新聞: {title}")

    # 優先抓取全文
    content = fetch_article_content(link)
    
    # 如果全文抓不到，嘗試 RSS 摘要
    if not content or len(content) < 200:
        if hasattr(entry, "description"):
            content = entry.description
        elif hasattr(entry, "summary"):
            content = entry.summary
        elif hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
            
    if not content or len(content) < 50:
        print(f"⚠️ 內容不足，跳過: {title}")
        return None

    content = str(content)[:8000]
    ai_result = ai.rewrite_content(title, content)

    if ai_result:
        success = post_to_flarum(
            mapping["user_id"],
            mapping["tag_id"],
            ai_result["title"],
            ai_result["content"]
        )
        if success:
            return link
    return None

def run_bot():
    mapping_data = load_json("mapping.json")
    mappings = mapping_data.get("mappings", [])
    ai_config = mapping_data.get("ai_config", None)
    
    if not CONFIG["SERVER_API_URL"]:
        CONFIG["SERVER_API_URL"] = mapping_data.get("forum_url")
    
    rss_sources = load_json("rss_sources.json")
    history = load_json(HISTORY_FILE)
    if not isinstance(history, list): history = []
    
    ai = AIHandler(CONFIG["AI_KEYS"], config=ai_config)
    mapping_dict = {m["channel"]: m for m in mappings}
    
    tasks = []
    for source in rss_sources:
        try:
            feed = feedparser.parse(source["url"])
            category = source["category"]
            if category not in mapping_dict: continue
            
            # 每個源取前 3 篇
            for entry in feed.entries[:3]:
                tasks.append((entry, source, mapping_dict[category]))
        except Exception as e:
            print(f"❌ RSS 抓取失敗 ({source['name']}): {e}")

    print(f"🚀 開始併發處理，總任務數: {len(tasks)}")
    
    new_links = []
    # 使用 3 個執行緒進行併發，避免過度擁擠
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(process_entry, t[0], t[1], t[2], ai, history) for t in tasks]
        for future in futures:
            result = future.result()
            if result:
                new_links.append(result)

    if new_links:
        history.extend(new_links)
        save_json(HISTORY_FILE, history[-300:])
        print(f"✅ 任務完成，新增 {len(new_links)} 篇帖文")

if __name__ == "__main__":
    if CONFIG["FLARUM_API_KEY"]:
        start_time = time.time()
        run_bot()
        print(f"⏱️ 總執行時間: {time.time() - start_time:.2f} 秒")
    else:
        print("❌ 環境變數缺失 (FLARUM_API_KEY)")
