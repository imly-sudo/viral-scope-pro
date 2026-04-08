from flask import Flask, request, jsonify, Response
import os, json, urllib.request

app = Flask(__name__)

# ===== 首页：直接读文件返回，不依赖 Flask static =====
HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

@app.route("/")
def index():
    try:
        with open(HTML_PATH, "r", encoding="utf-8") as f:
            return Response(f.read(), status=200, content_type="text/html; charset=utf-8")
    except FileNotFoundError:
        return Response(
            f"<h1>index.html not found</h1><p>Looking at: {HTML_PATH}</p>"
            f"<p>Files in project root: {os.listdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))}</p>",
            status=500, content_type="text/html"
        )

# ===== Gemini 配置 =====
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

PLATFORMS = {
    "red": {
        "name": "小红书",
        "weights": {"封面审美": 40, "实用干货": 30, "SEO标签": 20, "评论引导": 10},
        "guide": """小红书爆款铁律：
- 标题必须：数字+利益点+情绪词（"3步搞定""保姆级""后悔没早知道"）
- 正文：每段Emoji开头，清单体，段间空行，每段≤3行
- 结尾：互动引导语 + 5-8个标签（3大流量+3长尾+2情绪）
- 封面：高饱和、杂志感、文字覆盖≥20%面积"""
    },
    "douyin": {
        "name": "抖音",
        "weights": {"黄金3s钩子": 50, "情绪张力": 30, "节奏感": 10, "热点趋势": 10},
        "guide": """抖音爆款铁律：
- 标题：反差+悬念（"别急着买！""99%的人不知道"）
- 前3秒必须有钩子（提问/反转/冲突/惊人数据）
- 每句≤10字，每句一个情绪冲击点
- 口语化、金句密集、节奏快"""
    },
    "tiktok": {
        "name": "TikTok",
        "weights": {"Hook 3s": 50, "Trend alignment": 30, "Shareability": 10, "Hashtags": 10},
        "guide": """TikTok viral rules:
- Title: Short, punchy, curiosity-driven ("Wait for it...", "POV:", "Nobody talks about this")
- Hook in first 3 seconds
- Caption: 2-3 lines max, reference trending sounds
- Hashtags: 2 trending + 2 niche + 1 branded
- Tone: Casual, authentic, speak like a friend"""
    },
    "ins": {
        "name": "Instagram",
        "weights": {"高级调性": 50, "互动引导": 30, "标签策略": 20},
        "guide": """Instagram爆款铁律：
- Caption：精炼高级感，英文优先或中英混搭，less is more
- 视觉：色调统一、负空间构图
- 结尾提问引导评论
- Hashtags 15-20个：5大词(50w+) + 10精准词(1-10w) + 5品牌词"""
    }
}

TRENDING = {
    "red": ["2026灵性防护清单", "沉浸式书桌改造", "AI数码好物", "宋韵轻国风", "小米SU7真实体验", "极简咖啡角", "春季穿搭公式", "新能源车露营", "副业自由", "治愈系风景"],
    "douyin": ["荣耀Magic9", "比亚迪宋Ultra", "AI替代打工人", "春日野餐", "数码开箱", "新能源对比测评", "沉浸式收纳", "国货之光", "职场逆袭", "一人食"],
    "tiktok": ["permanent jewelry", "AI productivity", "desk setup 2026", "EV road trip", "crystal healing", "minimalist living", "tech unboxing", "side hustle", "aesthetic room", "wellness routine"],
    "ins": ["chunky gold jewelry", "quiet luxury", "desk aesthetics", "EV lifestyle", "crystal collection", "old money style", "tech minimal", "wellness ritual", "capsule wardrobe", "slow living"]
}


def gemini(prompt, img_b64=None):
    if not GEMINI_KEY:
        return {"error": "API Key未配置"}
    
    import time
    import urllib.request
    
    # 按优先级尝试不同模型
    models = [
        "gemini-2.5-flash",
        "gemini-2.0-flash", 
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-pro"
    ]
    
    for model_name in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
            parts = [{"text": prompt}]
            if img_b64:
                parts.insert(0, {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}})
            body = json.dumps({
                "contents": [{"parts": parts}],
                "generationConfig": {"temperature": 0.92, "maxOutputTokens": 8192, "responseMimeType": "application/json"}
            }).encode()
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(req, timeout=60) as r:
                        res = json.loads(r.read().decode())
                        txt = res["candidates"][0]["content"]["parts"][0]["text"]
                        return json.loads(txt)
                except urllib.error.HTTPError as e:
                    if e.code == 503 and attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                    raise
        except Exception as e:
            continue
    
    return {"error": "所有模型均不可用"}

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "gemini": bool(GEMINI_KEY), "v": "5.0", "html_path": HTML_PATH, "html_exists": os.path.exists(HTML_PATH)})


@app.route("/api/trending")
def trending():
    return jsonify({"platforms": {k: {"topics": v} for k, v in TRENDING.items()}})


@app.route("/api/analyze", methods=["POST", "OPTIONS"])
def analyze():
    if request.method == "OPTIONS":
        return "", 200, {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type"}

    d = request.json or {}
    plat = d.get("platform", "red")
    title = d.get("title", "")
    body_text = d.get("body", "")
    img = d.get("image")
    cfg = PLATFORMS.get(plat, PLATFORMS["red"])
    hot = TRENDING.get(plat, [])
    weights = cfg["weights"]
    weight_str = " / ".join([f"{k}({v}%)" for k, v in weights.items()])
    dims = list(weights.keys())

    prompt = f"""你是一个毒舌但极其专业的{cfg['name']}爆款内容操盘手。用户把草稿交给你，你的任务不是"提建议"，而是直接动手帮他改到能爆的程度。

## 用户原始草稿
标题：{title}
正文：{body_text}

## 平台：{cfg['name']}
## 评分维度：{weight_str}
## 平台规则：
{cfg['guide']}

## 当前热门话题（你必须从中挑选相关的融入改写）：
{', '.join(hot)}

---

## 你的任务（按顺序执行）：

### 第一步：诊断原稿
逐句分析原文，找出以下问题：
- 标题有没有钩子？能不能在信息流里抢到注意力？
- 正文结构是否符合平台阅读习惯？
- 有没有故事性/画面感/情绪共鸣？
- 标签是否精准？有没有蹭到热点？
- 有没有互动引导？

### 第二步：重写内容
- 标题：给出4个完全不同策略的改写版本，每个都必须比原标题强10倍
- 正文：从头到尾重写，不是在原文上加几个emoji就完事。你要：
  * 重新组织结构和叙事逻辑
  * 加入具体细节、数据、场景描写
  * 制造情绪起伏（先痛点→再方案→再获得感）
  * 融入至少2个当前热门话题的关键词
  * 长度必须是原文的2倍以上
  * 严格遵循平台排版规则
- 标签：根据内容重新生成，禁止用万能标签，每个标签必须和内容强相关

### 第三步：评分
对原稿（不是改后的）按维度打分，要求严格，60分以下的内容就该是60分以下。

## 输出JSON格式（严格遵循，不要输出任何JSON以外的内容）：

{{
  "fatal_flaw": "用一句毒舌但准确的话指出原稿最致命的问题",
  "diagnosis": "用3-5句话逐点分析原稿的具体问题，要引用原文的具体句子来说明为什么不行",
  "score": 整数0-100,
  "score_breakdown": {{
    "{dims[0]}": 整数0-100,
    "{dims[1]}": 整数0-100,
    "{dims[2]}": 整数0-100{(',' + chr(10) + '    "' + dims[3] + '": 整数0-100') if len(dims) > 3 else ''}
  }},
  "headlines": [
    "【恐惧驱动】用害怕错过/损失厌恶改写的标题",
    "【悬念缺口】用好奇心缺口改写的标题",
    "【利益承诺】用具体获得感改写的标题",
    "【身份共鸣】用'这说的就是我'改写的标题"
  ],
  "polished_body": "完整重写后的正文。必须是可以直接复制粘贴发布的成品。包含emoji排版、分段、互动引导、热门标签。禁止偷懒只改几个词。",
  "tags": ["#标签1", "#标签2", "#标签3", "#标签4", "#标签5", "#标签6", "#标签7", "#标签8"],
  "visual_tips": [
    "具体到参数的封面/配图修改指令1",
    "具体到参数的封面/配图修改指令2",
    "具体到参数的封面/配图修改指令3"
  ],
  "viral_probability": "进入二级流量池的概率估算，如32%",
  "best_post_time": "最佳发布时间段",
  "competitor_angle": "如何蹭当前热点的具体角度"
}}

## 铁律：
1. polished_body 必须从头重写，禁止只在原文上微调
2. 如果原文只有一两句话，你必须扩写到至少200字
3. 标签必须和改写后的内容匹配，禁止用通用标签
4. score要诚实，烂内容就给低分，不要客气
5. 所有标题改写必须基于原标题的核心主题，不能跑题"""

    result = gemini(prompt, img)
    vision = None
    if img:
        vision = gemini(f"""分析这张图片作为{cfg['name']}封面图的表现力。严格评估，不要客气。输出JSON:
{{
  "visual_score": 0-100整数,
  "composition": "构图分析：主体位置、留白、视觉重心、是否符合平台审美",
  "color_analysis": "色彩：饱和度、对比度、色调是否适合{cfg['name']}",
  "text_overlay_suggestion": "在图片哪个位置放文字、用什么颜色什么字号、具体参数",
  "crop_suggestion": "裁剪比例建议及原因",
  "improvement_tips": ["具体改进指令1（带参数）", "具体改进指令2（带参数）", "具体改进指令3（带参数）"],
  "platform_fit": "与{cfg['name']}审美的匹配度分析"
}}""", img)

    return jsonify({"platform_name": cfg["name"], "text_analysis": result, "vision_analysis": vision}), 200, {"Access-Control-Allow-Origin": "*"}


@app.route("/api/test-key")
def test_key():
    from flask import request as _req
    k = _req.args.get("key", "")
    model = _req.args.get("model", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={k}"
    body = json.dumps({"contents": [{"parts": [{"text": "say hi"}]}]}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.loads(r.read().decode())
            return jsonify({"status": "ok", "model": model, "response": res.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")[:100]})
    except Exception as e:
        return jsonify({"status": "error", "model": model, "error": str(e)[:200]})
