from http.server import BaseHTTPRequestHandler
import os
import json
import urllib.request

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

PLATFORM_CONFIGS = {
    "red": {
        "name": "小红书",
        "weights_desc": "封面审美(40%) + 实用干货(30%) + SEO标签(20%) + 评论引导(10%)",
        "style_guide": """小红书爆款规律（基于真实案例库）：
- 标题公式：数字+利益点+情绪词。如"3步搞定""保姆级""后悔没早点知道"
- 封面：高饱和度、杂志感、文字覆盖20%以上面积、大标题贴纸
- 正文：Emoji分段（每段开头一个Emoji）、清单体（1️⃣2️⃣3️⃣）、结尾引导收藏
- 标签：5-8个，混搭大流量词+精准长尾词
- 爆款案例参考："我的2026年度灵性防护清单🧿"(45k赞)、"沉浸式书桌改造2026💻"(62k赞)"""
    },
    "douyin": {
        "name": "抖音/TikTok",
        "weights_desc": "黄金3s钩子(50%) + 情绪张力(30%) + 节奏感(10%) + 热点趋势(10%)",
        "style_guide": """抖音/TikTok爆款规律：
- 标题公式：反差冲突+悬念。如"别急着买！""千万别这样做""看完我沉默了"
- 封面/首帧：强视觉反差、大字报风格、人脸表情夸张
- 文案：10字以内短句、每句一个情绪冲击、金句密集
- 节奏：前3秒必须有钩子（提问/反转/冲突画面）
- 爆款案例："荣耀Magic9全系直屏！屏幕天花板？"(1.2M赞)、"比亚迪宋Ultra EV全域开挂！"(2.1M赞)"""
    },
    "tiktok": {
        "name": "TikTok (海外)",
        "weights_desc": "Hook前3s(50%) + Trend alignment(30%) + Shareability(10%) + Hashtags(10%)",
        "style_guide": """TikTok (International) viral patterns:
- Title: Short, punchy, curiosity-driven. "Wait for it...", "Nobody talks about this"
- Visual: High contrast, fast cuts, face-to-camera opening
- Captions: 2-3 lines max, emoji sparingly, trending sounds reference
- Hashtags: Mix trending + niche, 3-5 total
- Viral ref: "Permanent Jewelry: Worth it in 2026?"(850k views)"""
    },
    "ins": {
        "name": "Instagram",
        "weights_desc": "高级调性(50%) + 互动引导(30%) + 标签策略(20%)",
        "style_guide": """Instagram爆款规律：
- 标题/Caption：精炼、高级感、英文优先或中英混搭
- 视觉：色调统一、滤镜一致性、负空间构图、"less is more"
- 互动：结尾用提问句引导评论、Story投票/滑块
- Hashtags：15-20个，分层（5个大词+10个精准词+5个品牌词）
- 爆款案例："Chunky Gold Era: Bold Cuffs"(110k likes)"""
    }
}

TRENDING_DATA = {
    "last_updated": "2026-04-08",
    "platforms": {
        "red": {"name": "小红书", "topics": ["2026灵性防护清单", "沉浸式书桌改造", "AI数码好物", "宋韵轻国风", "小米SU7真实体验", "极简咖啡角", "春季穿搭公式", "新能源车露营", "副业自由", "治愈系风景"]},
        "douyin": {"name": "抖音", "topics": ["荣耀Magic9", "比亚迪宋Ultra", "AI替代打工人", "春日野餐", "数码开箱", "新能源对比测评", "沉浸式收纳", "国货之光", "职场逆袭", "一人食"]},
        "tiktok": {"name": "TikTok", "topics": ["permanent jewelry", "AI productivity", "desk setup 2026", "EV road trip", "crystal healing", "minimalist living", "tech unboxing", "side hustle", "aesthetic room", "wellness routine"]},
        "ins": {"name": "Instagram", "topics": ["chunky gold jewelry", "quiet luxury", "desk aesthetics", "EV lifestyle", "crystal collection", "old money style", "tech minimal", "wellness ritual", "capsule wardrobe", "slow living"]}
    }
}


def call_gemini(prompt, image_base64=None):
    parts = [{"text": prompt}]
    if image_base64:
        parts.insert(0, {"inlineData": {"mimeType": "image/jpeg", "data": image_base64}})

    payload = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096, "responseMimeType": "application/json"}
    }).encode("utf-8")

    req = urllib.request.Request(GEMINI_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
    except Exception as e:
        return {"error": str(e)}


def build_analysis_prompt(platform, title, body):
    config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS["red"])
    return f"""你是一个全平台爆款内容预测专家 (ViralScope AI)。你精通社交媒体算法、消费心理学和视觉传达。

## 目标平台: {config['name']}
## 该平台的评分权重: {config['weights_desc']}
## 该平台的爆款知识库:
{config['style_guide']}

## 用户提交的原始内容:
- 标题: {title}
- 正文: {body}

## 你的任务:
请严格按照以下JSON格式输出分析结果（不要输出任何其他内容）:

{{
  "score": <0-100的整数，基于该平台权重的综合评分>,
  "score_breakdown": {{
    "dimension_1_name": <分数>,
    "dimension_2_name": <分数>,
    "dimension_3_name": <分数>,
    "dimension_4_name": <分数>
  }},
  "headlines": [
    "【损失厌恶】<基于原始标题改写的高点击率版本>",
    "【悬念钩子】<利用好奇心缺口改写>",
    "【获得感】<强调用户能获得什么>",
    "【身份认同】<让用户觉得这是'我的'内容>"
  ],
  "polished_body": "<根据该平台风格重新排版的正文，包含Emoji、分段、标签等>",
  "visual_tips": [
    "<具体的视觉优化建议1>",
    "<具体的视觉优化建议2>",
    "<具体的视觉优化建议3>"
  ],
  "tags": ["#标签1", "#标签2", "#标签3", "#标签4", "#标签5"],
  "fatal_flaw": "<当前内容最可能导致'石沉大海'的一个致命问题>",
  "viral_probability": "<进入二级流量池的概率百分比>"
}}

注意：
1. score_breakdown 的维度名称必须与该平台的权重维度一致
2. headlines 必须基于用户的原始标题进行改写，不要凭空创造
3. polished_body 必须保留用户原文的核心信息，只做排版和语气优化
4. visual_tips 要具体可执行，不要泛泛而谈
5. fatal_flaw 要一针见血，指出最关键的问题"""


def build_vision_prompt(platform):
    config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS["red"])
    return f"""你是一个专业的社交媒体视觉分析专家。请分析这张图片作为「{config['name']}」平台的封面图/主图的表现力。

请严格按照以下JSON格式输出（不要输出任何其他内容）:

{{
  "visual_score": <0-100的整数>,
  "composition": "<构图分析>",
  "color_analysis": "<色彩分析>",
  "text_overlay_suggestion": "<文字叠加建议>",
  "crop_suggestion": "<裁剪建议>",
  "improvement_tips": ["<建议1>", "<建议2>", "<建议3>"],
  "platform_fit": "<平台匹配度分析>"
}}"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/health":
            self._json_response({"status": "ok", "gemini_configured": bool(GEMINI_API_KEY), "version": "3.0.0"})
        elif self.path == "/api/trending":
            self._json_response(TRENDING_DATA)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/analyze":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body) if body else {}

            platform = data.get("platform", "red")
            title = data.get("title", "")
            text_body = data.get("body", "")
            image_b64 = data.get("image", None)

            if not GEMINI_API_KEY:
                self._json_response({"error": "GEMINI_API_KEY not configured"}, 500)
                return

            config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS["red"])
            text_prompt = build_analysis_prompt(platform, title, text_body)
            text_result = call_gemini(text_prompt)

            vision_result = None
            if image_b64:
                vision_prompt = build_vision_prompt(platform)
                vision_result = call_gemini(vision_prompt, image_b64)

            self._json_response({
                "platform_name": config["name"],
                "weights": config["weights_desc"],
                "text_analysis": text_result,
                "vision_analysis": vision_result
            })
        else:
            self.send_response(404)
            self.end_headers()

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
