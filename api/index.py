from flask import Flask, request, jsonify
import os, json, urllib.request

app = Flask(__name__)

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

PLATFORMS = {
    "red": {
        "name": "小红书",
        "weights": "封面审美(40%) + 实用干货(30%) + SEO标签(20%) + 评论引导(10%)",
        "guide": """你必须严格遵循以下小红书爆款创作规则：
【标题规则】必须包含数字+利益点+情绪词，如"3步搞定""保姆级""后悔没早点知道""别再XX了"
【封面规则】高饱和度、杂志感、文字需覆盖20%以上面积、使用大标题贴纸
【正文规则】
- 每段开头必须有一个相关Emoji（如✨📍💡🔥）
- 使用清单体（1️⃣2️⃣3️⃣）或分点描述
- 段落之间空一行，每段不超过3行
- 结尾必须有互动引导语（如"你觉得呢？评论区告诉我～"）
- 结尾必须附上5-8个热门标签
【标签规则】混搭：3个大流量词 + 3个精准长尾词 + 2个情绪词
【爆款参考】"我的2026年度灵性防护清单🧿"(45k赞)、"沉浸式书桌改造2026💻"(62k赞)、"小米SU7对比特斯拉：30天真心话🚗"(88k赞)"""
    },
    "douyin": {
        "name": "抖音",
        "weights": "黄金3s钩子(50%) + 情绪张力(30%) + 节奏感(10%) + 热点趋势(10%)",
        "guide": """你必须严格遵循以下抖音爆款创作规则：
【标题规则】反差冲突+悬念，如"别急着买！""千万别这样做""看完我沉默了""99%的人都不知道"
【封面规则】强视觉反差、大字报风格、人脸表情夸张、颜色对比强烈
【正文规则】
- 每句话不超过10个字
- 每句一个情绪冲击点
- 金句密集、节奏快
- 使用短促有力的口语化表达
- 开头必须是一个能引发好奇的问题或反转
【节奏规则】前3秒必须有钩子（提问/反转/冲突/惊人数据）
【爆款参考】"荣耀Magic9全系直屏！屏幕天花板？"(1.2M赞)、"比亚迪宋Ultra EV全域开挂！"(2.1M赞)"""
    },
    "tiktok": {
        "name": "TikTok",
        "weights": "Hook 3s(50%) + Trend alignment(30%) + Shareability(10%) + Hashtags(10%)",
        "guide": """Strict TikTok viral creation rules:
【Title】Short, punchy, curiosity-driven. "Wait for it...", "Nobody talks about this", "POV:"
【Visual】High contrast, fast cuts, face-to-camera opening, trending filters
【Caption】2-3 lines max, use emoji sparingly, reference trending sounds
【Hashtags】Mix 2 trending + 2 niche + 1 branded, total 3-5
【Tone】Casual, authentic, slightly provocative, speak like a friend
【Viral ref】"Permanent Jewelry: Worth it in 2026?"(850k views)"""
    },
    "ins": {
        "name": "Instagram",
        "weights": "高级调性(50%) + 互动引导(30%) + 标签策略(20%)",
        "guide": """你必须严格遵循以下Instagram爆款创作规则：
【Caption规则】精炼、高级感、英文优先或中英混搭、"less is more"
【视觉规则】色调统一、滤镜一致性、负空间构图
【互动规则】结尾用提问句引导评论、设置Story投票/滑块
【Hashtags】15-20个，分层：5个大词(50w+帖子) + 10个精准词(1-10w帖子) + 5个品牌词
【爆款参考】"Chunky Gold Era: Bold Cuffs"(110k likes)"""
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
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    parts = [{"text": prompt}]
    if img_b64:
        parts.insert(0, {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}})
    body = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.75, "maxOutputTokens": 8192, "responseMimeType": "application/json"}
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.loads(r.read().decode())
            txt = res["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(txt)
    except Exception as e:
        return {"error": str(e)}


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "gemini": bool(GEMINI_KEY), "v": "4.0"})


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
    body = d.get("body", "")
    img = d.get("image")
    cfg = PLATFORMS.get(plat, PLATFORMS["red"])
    hot = TRENDING.get(plat, [])

    prompt = f"""# Role: ViralScope AI 爆款预测与内容优化专家

你是全球顶尖的社交媒体内容策略师。你的任务是：
1. 对用户的草稿进行精准评分
2. **直接帮用户改好内容**——不是给建议，而是给出**可以直接复制粘贴发布的成品**

## 目标平台: {cfg['name']}
## 评分权重: {cfg['weights']}

## 平台创作规则（你必须严格遵循）:
{cfg['guide']}

## 当前该平台热门话题:
{', '.join(hot)}

## 用户提交的原始内容:
标题: {title}
正文: {body}

## 你必须输出以下JSON（严格遵循格式，不要输出任何其他内容）:

{{
  "score": <0-100整数，严格按权重计算>,
  "score_breakdown": {{
    "<维度1名称>": <0-100>,
    "<维度2名称>": <0-100>,
    "<维度3名称>": <0-100>,
    "<维度4名称>": <0-100>
  }},
  "headlines": [
    "【损失厌恶】<在原标题基础上改写，加入让人害怕错过的元素>",
    "【悬念钩子】<在原标题基础上改写，留下好奇心缺口>",
    "【获得感】<在原标题基础上改写，强调用户能获得的具体利益>",
    "【身份认同】<在原标题基础上改写，让用户觉得'这就是我'>"
  ],
  "polished_body": "<这里必须是完整的、可以直接复制粘贴发布的正文。不是建议，不是提示，而是你帮用户改好的完整成品。必须包含：Emoji引导、分段排版、互动引导语、热门标签。长度至少是原文的1.5倍>",
  "visual_tips": [
    "<具体可执行的视觉修改指令，如：将主体放在画面左1/3处，右侧留白用于添加文字>",
    "<具体的色彩调整指令，如：提高饱和度15%，暖色调滤镜，对比度+10>",
    "<具体的文字叠加指令，如：在右上角添加白色粗体标题，字号占画面高度的1/5>"
  ],
  "tags": ["#标签1", "#标签2", "#标签3", "#标签4", "#标签5", "#标签6", "#标签7"],
  "fatal_flaw": "<一针见血指出当前内容最致命的问题，以及具体的修复方法>",
  "viral_probability": "<基于评分给出进入二级流量池的概率，如'72%'>",
  "best_post_time": "<根据该平台的算法特征，建议的最佳发布时间段>",
  "competitor_angle": "<如果要蹭热点，建议从哪个角度切入当前热门话题>"
}}

## 关键要求:
1. polished_body 必须是**完整成品**，用户可以直接复制粘贴发到{cfg['name']}上
2. 标题改写必须基于用户原标题，不能凭空创造
3. visual_tips 必须是具体到参数的操作指令
4. fatal_flaw 必须指出问题并给出解决方案
5. 如果原文太短或太空洞，你必须帮用户扩写，加入细节和故事性"""

    result = gemini(prompt, img)
    vision = None
    if img:
        vision = gemini(f"""分析这张图片作为{cfg['name']}封面图的表现力。输出JSON:
{{
  "visual_score": <0-100>,
  "composition": "<构图分析：主体位置、留白、视觉重心>",
  "color_analysis": "<色彩分析：饱和度、对比度、色调>",
  "text_overlay_suggestion": "<在图片哪个位置放文字、用什么颜色什么字号>",
  "crop_suggestion": "<裁剪比例建议，如4:3或1:1>",
  "improvement_tips": ["<改进1>", "<改进2>", "<改进3>"],
  "platform_fit": "<与{cfg['name']}审美的匹配度>"
}}""", img)

    return jsonify({"platform_name": cfg["name"], "text_analysis": result, "vision_analysis": vision}), 200, {"Access-Control-Allow-Origin": "*"}
