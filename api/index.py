from flask import Flask, request, jsonify, render_template_string
import random
import os

app = Flask(__name__)

# Platform configs for scoring
PLATFORM_CONFIGS = {
    "red": {
        "name": "小红书",
        "weights": {"visual": 0.4, "utility": 0.3, "seo": 0.2, "engagement": 0.1},
        "tips": ["增强封面美感", "加入干货清单", "Emoji 分段引导"]
    },
    "douyin": {
        "name": "抖音/TikTok",
        "weights": {"hook": 0.5, "emotion": 0.3, "pacing": 0.1, "trend": 0.1},
        "tips": ["黄金 3s 视觉反差", "短促有力的金句", "蹭当前热门话题标签"]
    },
    "ins": {
        "name": "Instagram",
        "weights": {"aesthetic": 0.5, "interaction": 0.3, "tags": 0.2},
        "tips": ["色调一致性检查", "Story 互动引导", "中英双语 Caption"]
    }
}

@app.route('/')
def index():
    # Return the UI (could also use send_from_directory for static files)
    with open('static/index.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/analyze', methods=['POST'])
def analyze():
    # In production, this would call GPT-4o Vision or Claude 3.5 Sonnet
    # For now, we simulate the refined logic we developed locally
    data = request.json or request.form
    platform = data.get('platform', 'red')
    title = data.get('title', '')
    body = data.get('body', '')
    
    config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS['red'])
    opt_score = random.randint(85, 98)
    
    optimized_headlines = [
        f"【损失厌恶】别再错过了！发出来前如果不做这步，流量可能损失 90%",
        f"【悬念钩子】{title}？只有 1% 的人知道这个爆款秘密...",
        f"【获得感】保姆级攻略！3 分钟教你把「{title}」做成爆款",
        f"【身份认同】如果你也是 AI 创作者，这篇文章建议反复观看"
    ]
    
    # Simulate content polishing
    polished_body = f"✨ 进化版草稿已准备好！\n\n{body[:100]}...\n\n#流量密码 #{config['name']} #爆款技巧"
    
    return jsonify({
        "score": opt_score,
        "headlines": optimized_headlines,
        "polished_body": polished_body,
        "tips": config['tips'],
        "platform_name": config['name']
    })

# Vercel needs the app variable to be named 'app'
if __name__ == "__main__":
    app.run()
