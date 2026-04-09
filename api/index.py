from flask import Flask, request, jsonify, Response
import os, json, urllib.request

app = Flask(__name__)

# ===== 首页 =====
@app.route("/")
def index():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page.html")
    with open(p, "r", encoding="utf-8") as f:
        return Response(f.read(), content_type="text/html; charset=utf-8")

# ===== 配置 =====
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

FALLBACK_TRENDING = {
    "red": ["2026灵性防护清单", "沉浸式书桌改造", "AI数码好物", "宋韵轻国风", "小米SU7真实体验", "极简咖啡角", "春季穿搭公式", "新能源车露营", "副业自由", "治愈系风景"],
    "douyin": ["荣耀Magic9", "比亚迪宋Ultra", "AI替代打工人", "春日野餐", "数码开箱", "新能源对比测评", "沉浸式收纳", "国货之光", "职场逆袭", "一人食"],
    "tiktok": ["permanent jewelry", "AI productivity", "desk setup 2026", "EV road trip", "crystal healing", "minimalist living", "tech unboxing", "side hustle", "aesthetic room", "wellness routine"],
    "ins": ["chunky gold jewelry", "quiet luxury", "desk aesthetics", "EV lifestyle", "crystal collection", "old money style", "tech minimal", "wellness ritual", "capsule wardrobe", "slow living"]
}


# ===== Gemini 基础调用（返回 parsed JSON）=====
def gemini(prompt, img_b64=None, temperature=0.92):
    """标准 Gemini 调用，要求返回 JSON，解析后返回 dict"""
    if not GEMINI_KEY:
        return {"error": "API Key未配置"}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    parts = [{"text": prompt}]
    if img_b64:
        parts.insert(0, {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}})
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json"
        }
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.loads(r.read().decode())
            txt = res["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(txt)
    except Exception as e:
        return {"error": str(e)}


# ===== Gemini 搜索调用（带 fallback，返回纯文本）=====
def gemini_search(prompt):
    """尝试用 Google Search grounding 搜索，失败则降级为普通调用"""
    if not GEMINI_KEY:
        return "API Key未配置"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"

    # 第一次尝试：带 Google Search
    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
            "tools": [{"google_search": {}}]
        }
        body = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode())
            return res["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        pass

    # 降级：不带搜索，让 Gemini 基于训练知识回答
    try:
        payload = {
            "contents": [{"parts": [{"text": prompt + "\n\n请基于你的专业知识回答，给出具体的案例分析。"}]}],
            "generationConfig": {"temperature": 0.5, "maxOutputTokens": 4096}
        }
        body = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode())
            return res["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"搜索失败: {str(e)}"


# ===== 路由 =====
@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "gemini": bool(GEMINI_KEY), "v": "6.2"})


@app.route("/api/trending")
def trending():
    return jsonify({"platforms": {k: {"topics": v} for k, v in FALLBACK_TRENDING.items()}})


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
    weights = cfg["weights"]
    weight_str = " / ".join([f"{k}({v}%)" for k, v in weights.items()])
    dims = list(weights.keys())

    # ===== Step 1: 搜索爆款案例（用 gemini_search，带 fallback）=====
    topic_keywords = title if title else body_text[:50]
    real_examples = gemini_search(
        f'请搜索"{cfg["name"]}"平台上最近关于"{topic_keywords}"主题的爆款内容。'
        f'找到3-5个高互动案例，每个提供：标题、互动数据、为什么能火。'
        f'同时列出当前热门标签和趋势方向。'
    )

    # ===== Step 2: 基于案例做诊断+改写（用 gemini，返回 JSON）=====
    prompt = f"""你是一个毒舌但极其专业的{cfg['name']}爆款内容操盘手。

## 爆款参考案例
{real_examples}

---

## 用户原始草稿
标题：{title}
正文：{body_text}

## 平台：{cfg['name']}
## 评分维度：{weight_str}
## 平台规则：
{cfg['guide']}

---

## 任务：

### 第一步：对标分析
将用户草稿与爆款案例逐项对比，找出标题、正文、标签、互动引导的差距。

### 第二步：重写内容
- 标题：4个不同策略的改写版本
- 正文：从头到尾重写，融入爆款技巧，长度是原文2倍以上，严格遵循平台排版规则
- 标签：参考爆款标签策略生成

### 第三步：评分
以爆款为满分标杆，对原稿按维度严格打分。

## 输出JSON（严格遵循）：

{{
  "real_benchmarks": "2-3句话概括爆款案例的共同成功模式",
  "fatal_flaw": "对比爆款后，一句话指出原稿最致命的差距",
  "diagnosis": "3-5句话对标分析，引用案例说明差距",
  "score": 整数0-100,
  "score_breakdown": {{
    "{dims[0]}": 整数0-100,
    "{dims[1]}": 整数0-100,
    "{dims[2]}": 整数0-100{(',' + chr(10) + '    "' + dims[3] + '": 整数0-100') if len(dims) > 3 else ''}
  }},
  "headlines": [
    "【恐惧驱动】用损失厌恶改写的标题",
    "【悬念缺口】用好奇心缺口改写的标题",
    "【利益承诺】用具体获得感改写的标题",
    "【身份共鸣】用'这说的就是我'改写的标题"
  ],
  "polished_body": "完整重写后的正文，可直接复制粘贴发布。包含emoji排版、分段、互动引导、标签。",
  "tags": ["#标签1", "#标签2", "#标签3", "#标签4", "#标签5", "#标签6", "#标签7", "#标签8"],
  "visual_tips": [
    "具体到参数的封面修改指令1",
    "具体到参数的封面修改指令2",
    "具体到参数的封面修改指令3"
  ],
  "viral_probability": "进入流量池的概率估算",
  "best_post_time": "最佳发布时间段",
  "competitor_angle": "参考爆款的切入角度建议"
}}

## 铁律：
1. polished_body 必须从头重写，禁止只微调
2. 原文太短必须扩写到至少200字
3. 标签必须和内容强相关
4. score 诚实打分
5. 标题改写基于原标题核心主题"""

    result = gemini(prompt, img)

    vision = None
    if img:
        vision = gemini(f"""分析这张图片作为{cfg['name']}封面图的表现力。严格评估。输出JSON:
{{
  "visual_score": 0-100整数,
  "composition": "构图分析",
  "color_analysis": "色彩分析",
  "text_overlay_suggestion": "文字叠加建议（位置、颜色、字号）",
  "crop_suggestion": "裁剪比例建议",
  "improvement_tips": ["改进1", "改进2", "改进3"],
  "platform_fit": "平台审美匹配度"
}}""", img)

    return jsonify({
        "platform_name": cfg["name"],
        "text_analysis": result,
        "vision_analysis": vision,
        "search_context": real_examples[:500] if isinstance(real_examples, str) else None
    }), 200, {"Access-Control-Allow-Origin": "*"}
