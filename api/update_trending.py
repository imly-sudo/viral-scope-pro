"""
ViralScope 每日热点自动更新脚本
可通过 Vercel Cron 或本地 crontab 定时执行
"""
import json
import os
import urllib.request
from datetime import datetime

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "trending_cache.json")


def fetch_trending_via_gemini():
    """Use Gemini to generate current trending topics for each platform."""
    
    prompt = f"""你是一个社交媒体热点分析专家。今天是 {datetime.now().strftime('%Y年%m月%d日')}。

请根据你的知识，列出以下4个平台【当前最可能在热搜/推荐流中出现的10个热门话题关键词】。
这些关键词应该是真实、具体、可搜索的（不要太泛泛）。

请严格按照以下JSON格式输出（不要输出任何其他内容）:

{{
  "last_updated": "{datetime.now().strftime('%Y-%m-%d')}",
  "platforms": {{
    "red": {{
      "name": "小红书",
      "topics": ["话题1", "话题2", "话题3", "话题4", "话题5", "话题6", "话题7", "话题8", "话题9", "话题10"]
    }},
    "douyin": {{
      "name": "抖音",
      "topics": ["话题1", "话题2", "话题3", "话题4", "话题5", "话题6", "话题7", "话题8", "话题9", "话题10"]
    }},
    "tiktok": {{
      "name": "TikTok",
      "topics": ["topic1", "topic2", "topic3", "topic4", "topic5", "topic6", "topic7", "topic8", "topic9", "topic10"]
    }},
    "ins": {{
      "name": "Instagram",
      "topics": ["topic1", "topic2", "topic3", "topic4", "topic5", "topic6", "topic7", "topic8", "topic9", "topic10"]
    }}
  }}
}}

要求：
1. 小红书和抖音用中文关键词
2. TikTok和Instagram用英文关键词
3. 覆盖以下领域：首饰/Wellness、科技数码3C、新能源车、生活方式、美妆穿搭
4. 每个平台的话题要符合该平台的用户偏好和内容调性"""

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json"
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        GEMINI_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            trending_data = json.loads(text)

            # Save to cache file
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(trending_data, f, ensure_ascii=False, indent=2)

            print(f"[{datetime.now()}] Trending cache updated successfully.")
            return trending_data

    except Exception as e:
        print(f"[{datetime.now()}] Error updating trending: {e}")
        return None


if __name__ == "__main__":
    fetch_trending_via_gemini()
