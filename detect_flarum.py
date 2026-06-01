import requests
import json

FORUM_URL = "https://manprompt.qzz.io"

def get_tags():
    print(f"正在獲取 {FORUM_URL} 的標籤資訊...")
    try:
        response = requests.get(f"{FORUM_URL}/api/tags")
        if response.status_code == 200:
            data = response.json()
            tags = {}
            for item in data.get('data', []):
                attributes = item.get('attributes', {})
                tags[attributes.get('slug')] = item.get('id')
            return tags
        else:
            print(f"無法獲取標籤，狀態碼: {response.status_code}")
    except Exception as e:
        print(f"發生錯誤: {e}")
    return {}

def update_mapping(tag_ids):
    mapping_path = "mapping.json"
    try:
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        
        updated = False
        for entry in mapping_data['mappings']:
            slug = entry['channel']
            if slug in tag_ids:
                entry['tag_id'] = int(tag_ids[slug])
                print(f"更新標籤: {entry['display_name']} ({slug}) -> ID: {tag_ids[slug]}")
                updated = True
        
        if updated:
            with open(mapping_path, 'w', encoding='utf-8') as f:
                json.dump(mapping_data, f, indent=2, ensure_ascii=False)
            print(f"已更新 {mapping_path}")
        else:
            print("沒有找到匹配的標籤 ID。")
            
    except FileNotFoundError:
        print(f"找不到 {mapping_path}")

if __name__ == "__main__":
    tags = get_tags()
    if tags:
        update_mapping(tags)
    else:
        print("未獲取到任何標籤資訊。")
    
    print("\n提示: 使用者 ID (UserID) 通常無法透過公開 API 大量獲取。")
    print("請確保您在 Flarum 後台註冊了 ai001 ~ ai009 帳號，並將其 ID 手動填入 mapping.json。")
