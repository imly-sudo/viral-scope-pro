from http.server import BaseHTTPRequestHandler
import os
import json
import urllib.request

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

PLATFORM_CONFIGS = {
    "red": {
        "name": "\u5c0f\u7ea2\u4e66",
        "weights_desc": "\u5c01\u9762\u5ba1\u7f8e(40%) + \u5b9e\u7528\u5e72\u8d27(30%) + SEO\u6807\u7b7e(20%) + \u8bc4\u8bba\u5f15\u5bfc(10%)",
        "style_guide": "\u5c0f\u7ea2\u4e66\u7206\u6b3e\u89c4\u5f8b:\n- \u6807\u9898\u516c\u5f0f: \u6570\u5b57+\u5229\u76ca\u70b9+\u60c5\u7eea\u8bcd\n- \u5c01\u9762: \u9ad8\u9971\u548c\u5ea6\u3001\u6742\u5fd7\u611f\u3001\u6587\u5b57\u8986\u76d620%\u4ee5\u4e0a\n- \u6b63\u6587: Emoji\u5206\u6bb5\u3001\u6e05\u5355\u4f53\u3001\u7ed3\u5c3e\u5f15\u5bfc\u6536\u85cf\n- \u6807\u7b7e: 5-8\u4e2a"
    },
    "douyin": {
        "name": "\u6296\u97f3/TikTok",
        "weights_desc": "\u9ec4\u91d13s\u94a9\u5b50(50%) + \u60c5\u7eea\u5f20\u529b(30%) + \u8282\u594f\u611f(10%) + \u70ed\u70b9\u8d8b\u52bf(10%)",
        "style_guide": "\u6296\u97f3\u7206\u6b3e\u89c4\u5f8b:\n- \u6807\u9898: \u53cd\u5dee\u51b2\u7a81+\u60ac\u5ff5\n- \u5c01\u9762: \u5f3a\u89c6\u89c9\u53cd\u5dee\u3001\u5927\u5b57\u62a5\u98ce\u683c\n- \u6587\u6848: 10\u5b57\u4ee5\u5185\u77ed\u53e5\u3001\u91d1\u53e5\u5bc6\u96c6\n- \u524d3\u79d2\u5fc5\u987b\u6709\u94a9\u5b50"
    },
    "tiktok": {
        "name": "TikTok",
        "weights_desc": "Hook 3s(50%) + Trend(30%) + Shareability(10%) + Hashtags(10%)",
        "style_guide": "TikTok viral patterns:\n- Title: Short, punchy, curiosity-driven\n- Visual: High contrast, fast cuts\n- Captions: 2-3 lines max\n- Hashtags: Mix trending + niche, 3-5 total"
    },
    "ins": {
        "name": "Instagram",
        "weights_desc": "\u9ad8\u7ea7\u8c03\u6027(50%) + \u4e92\u52a8\u5f15\u5bfc(30%) + \u6807\u7b7e\u7b56\u7565(20%)",
        "style_guide": "Instagram\u7206\u6b3e\u89c4\u5f8b:\n- Caption: \u7cbe\u70bc\u3001\u9ad8\u7ea7\u611f\n- \u89c6\u89c9: \u8272\u8c03\u7edf\u4e00\u3001less is more\n- Hashtags: 15-20\u4e2a\u5206\u5c42"
    }
}

TRENDING_DATA = {
    "last_updated": "2026-04-08",
    "platforms": {
        "red": {"name": "\u5c0f\u7ea2\u4e66", "topics": ["2026\u7075\u6027\u9632\u62a4\u6e05\u5355", "\u6c89\u6d78\u5f0f\u4e66\u684c\u6539\u9020", "AI\u6570\u7801\u597d\u7269", "\u5b8b\u97f5\u8f7b\u56fd\u98ce", "\u5c0f\u7c73SU7\u771f\u5b9e\u4f53\u9a8c", "\u6781\u7b80\u5496\u5561\u89d2", "\u6625\u5b63\u7a7f\u642d\u516c\u5f0f", "\u65b0\u80fd\u6e90\u8f66\u9732\u8425", "\u526f\u4e1a\u81ea\u7531", "\u6cbb\u6108\u7cfb\u98ce\u666f"]},
        "douyin": {"name": "\u6296\u97f3", "topics": ["\u8363\u8000Magic9", "\u6bd4\u4e9a\u8fea\u5b8bUltra", "AI\u66ff\u4ee3\u6253\u5de5\u4eba", "\u6625\u65e5\u91ce\u9910", "\u6570\u7801\u5f00\u7bb1", "\u65b0\u80fd\u6e90\u5bf9\u6bd4\u6d4b\u8bc4", "\u6c89\u6d78\u5f0f\u6536\u7eb3", "\u56fd\u8d27\u4e4b\u5149", "\u804c\u573a\u9006\u88ad", "\u4e00\u4eba\u98df"]},
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


def build_prompt(platform, title, body):
    config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS["red"])
    return f"""You are ViralScope AI, an expert at predicting viral content.

Platform: {config['name']}
Weights: {config['weights_desc']}
Knowledge: {config['style_guide']}

User content:
- Title: {title}
- Body: {body}

Output ONLY this JSON:
{{
  "score": <0-100>,
  "score_breakdown": {{"dim1": <score>, "dim2": <score>, "dim3": <score>, "dim4": <score>}},
  "headlines": [
    "headline variant 1",
    "headline variant 2",
    "headline variant 3",
    "headline variant 4"
  ],
  "polished_body": "<optimized body text>",
  "visual_tips": ["tip1", "tip2", "tip3"],
  "tags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
  "fatal_flaw": "<biggest issue>",
  "viral_probability": "<percentage>"
}}"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/health":
            self._json({"status": "ok", "gemini": bool(GEMINI_API_KEY), "v": "3.0.1"})
        elif self.path == "/api/trending":
            self._json(TRENDING_DATA)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/analyze":
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length)) if length else {}
            platform = data.get("platform", "red")
            title = data.get("title", "")
            body = data.get("body", "")
            image_b64 = data.get("image")

            if not GEMINI_API_KEY:
                self._json({"error": "GEMINI_API_KEY not set"}, 500)
                return

            config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS["red"])
            result = call_gemini(build_prompt(platform, title, body))

            vision = None
            if image_b64:
                vision = call_gemini("Analyze this image for social media. Return JSON with: visual_score (0-100), composition, color_analysis, text_overlay_suggestion, crop_suggestion, improvement_tips (array), platform_fit.", image_b64)

            self._json({"platform_name": config["name"], "text_analysis": result, "vision_analysis": vision})
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
