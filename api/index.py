from flask import Flask, request, jsonify, send_file
import os, json, urllib.request

app = Flask(__name__)

# === 根路径：返回 HTML ===
@app.route("/")
def index():
    return send_file(os.path.join(os.path.dirname(__file__), "page.html"))

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


# ===== Gemini 调用（支持 Google Search grounding）=====
def gemini(prompt, img_b64=None, use_search=False, temperature=0.92):
    if not GEMINI_KEY:
        return {"error": "API Key未配置"}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    parts = [{"text": prompt}]
    if img_b64:
        parts.insert(0, {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 8192}
    }

    if not use_search:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    if use_search:
        payload["tools"] = [{"google_search": {}}]

    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.loads(r.read().decode())
            txt = res["candidates"][0]["content"]["parts"][0]["text"]
            if use_search:
                return {"text": txt}
            return json.loads(txt)
    except Exception as e:
        return {"error": str(e)}


# ===== Step 1: 搜索真实爆款案例 =====
def search_viral_examples(platform_name, user_topic):
    prompt = f"""请搜索"{platform_name}"平台上最近关于"{user_topic}"主题的爆款内容。

我需要你找到3-5个真实存在的高互动帖子/视频案例，对每个案例提供：
1. 标题/文案的原文或核心内容
2. 大致的互动数据（点赞、评论、转发）
3. 为什么这个内容能火的1-2个关键因素

同时告诉我这个主题在"{platform_name}"上当前的热门标签和流行趋势方向。

请尽可能提供真实、具体的案例，不要编造数据。如果搜索不到精确数据，请说明是估算。"""

    return gemini(prompt, use_search=True, temperature=0.3)


# ===== 路由 =====
@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "gemini": bool(GEMINI_KEY), "v": "6.0"})


@app.route("/api/trending")
def trending():
    plat = request.args.get("platform", "red")
    cfg = PLATFORMS.get(plat, PLATFORMS["red"])
    result = gemini(
        f"请搜索{cfg['name']}平台上今天最热门的10个内容话题/趋势关键词，只返回JSON数组格式如[\"话题1\",\"话题2\",...]",
        use_search=True, temperature=0.2
    )
    if "text" in result:
        try:
            txt = result["text"]
            start = txt.find("[")
            end = txt.rfind("]") + 1
            if start >= 0 and end > start:
                topics = json.loads(txt[start:end])
                return jsonify({"platforms": {plat: {"topics": topics}}})
        except Exception:
            pass
    return jsonify({"platforms": {plat: {"topics": ["暂无数据"]}}})


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

    # ===== Step 1: 搜索真实爆款案例 =====
    topic_keywords = title if title else body_text[:50]
    search_result = search_viral_examples(cfg["name"], topic_keywords)
    real_examples = search_result.get("text", "未找到相关案例") if isinstance(search_result, dict) else "搜索失败"

    # ===== Step 2: 基于真实案例做诊断+改写 =====
    prompt = f"""你是一个毒舌但极其专业的{cfg['name']}爆款内容操盘手。

## 真实爆款参考（来自实时搜索）
以下是{cfg['name']}上与用户主题相关的真实爆款案例：
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

## 你的任务（按顺序执行）：

### 第一步：对标分析
将用户草稿与上面的真实爆款案例逐项对比：
- 标题钩子强度差距
- 正文结构和叙事方式差距
- 标签策略差距
- 互动引导差距
引用真实案例的具体做法来说明用户草稿哪里不行。

### 第二步：重写内容
参考真实爆款的成功模式，从头重写用户内容：
- 标题：给出4个不同策略的改写版本
- 正文：从头到尾重写，融入爆款案例验证过的技巧
  * 重新组织结构和叙事逻辑
  * 加入具体细节、数据、场景描写
  * 制造情绪起伏（先痛点→再方案→再获得感）
  * 长度必须是原文的2倍以上
  * 严格遵循平台排版规则
- 标签：参考爆款案例使用的标签策略，生成强相关标签

### 第三步：评分
以真实爆款为满分标杆，对原稿按维度打分。有了真实案例做参照，你的评分必须更精准。

## 输出JSON格式（严格遵循）：

{{
    "real_benchmarks": "用2-3句话概括搜索到的爆款案例的共同成功模式",
    "fatal_flaw": "对比爆款案例后，一句话指出原稿最致命的差距",
    "diagnosis": "用3-5句话对标分析，引用真实案例说明差距",
    "score": 整数0-100,
    "score_breakdown": {{
        "{dims[0]}": 整数0-100,
        "{dims[1]}": 整数0-100,
        "{dims[2]}": 整数0-100{(',' + chr(10) + '        "' + dims[3] + '": 整数0-100') if len(dims) > 3 else ''}
    }},
    "headlines": [
        "【恐惧驱动】用害怕错过/损失厌恶改写的标题",
        "【悬念缺口】用好奇心缺口改写的标题",
        "【利益承诺】用具体获得感改写的标题",
        "【身份共鸣】用'这说的就是我'改写的标题"
    ],
    "polished_body": "完整重写后的正文，参考爆款案例的成功模式。可直接复制粘贴发布。包含emoji排版、分段、互动引导、标签。",
    "tags": ["#标签1", "#标签2", "#标签3", "#标签4", "#标签5", "#标签6", "#标签7", "#标签8"],
    "visual_tips": [
        "具体到参数的封面/配图修改指令1",
        "具体到参数的封面/配图修改指令2",
        "具体到参数的封面/配图修改指令3"
    ],
    "viral_probability": "基于与爆款案例的差距估算进入流量池的概率",
    "best_post_time": "最佳发布时间段",
    "competitor_angle": "参考爆款案例的切入角度建议"
}}

## 铁律：
1. polished_body 必须从头重写，参考爆款模式，禁止只微调
2. 如果原文只有一两句话，必须扩写到至少200字
3. 标签必须参考爆款案例的标签策略
4. score 以真实爆款为标杆，诚实打分
5. 标题改写必须基于原标题核心主题"""

    result = gemini(prompt, img)

    vision = None
    if img:
        vision = gemini(f"""分析这张图片作为{cfg['name']}封面图的表现力。严格评估。输出JSON:
{{
    "visual_score": 0-100整数,
    "composition": "构图分析",
    "color_analysis": "色彩分析",
    "text_overlay_suggestion": "文字叠加建议（具体位置、颜色、字号）",
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
