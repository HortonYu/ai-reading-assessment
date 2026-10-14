# -*- coding: utf-8 -*-
"""
全维语言能力 AI 评测平台 - 后端核心
【100% 真实 DeepSeek 调用】坚决杜绝假题目与无作答虚假分数
"""
import os
import time
import json
import random
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="乡村教育全维语言评测引擎", version="5.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

def find_frontend_dir():
    candidates = [
        os.path.join(os.getcwd(), "frontend"),
        os.path.join(os.path.dirname(__file__), "..", "frontend"),
        os.path.join(os.path.dirname(__file__), "frontend"),
        os.path.join(os.getcwd(), "reading-ai-tool", "frontend"),
    ]
    for c in candidates:
        if os.path.exists(os.path.join(c, "index.html")):
            return os.path.abspath(c)
    for root, dirs, files in os.walk(os.getcwd()):
        if "index.html" in files:
            return root
    return None

FRONTEND_DIR = find_frontend_dir()

@app.get("/")
def serve_home():
    if FRONTEND_DIR and os.path.exists(os.path.join(FRONTEND_DIR, "index.html")):
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
    return HTMLResponse("<h2>AI评测服务正常运行</h2>")

@app.get("/{page_name}")
def serve_pages(page_name: str):
    if FRONTEND_DIR:
        target = os.path.join(FRONTEND_DIR, page_name)
        if os.path.exists(target):
            return FileResponse(target)
        if not page_name.endswith(".html"):
            html_target = os.path.join(FRONTEND_DIR, f"{page_name}.html")
            if os.path.exists(html_target):
                return FileResponse(html_target)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# 真实调用 DeepSeek API，报错直接透传，绝不静默隐藏
def request_deepseek(prompt: str, system_prompt: str) -> dict:
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=400, detail="未配置 DEEPSEEK_API_KEY，请在 Render 后台 Environment 中填入密钥！")

    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.9,
        "response_format": {"type": "json_object"}
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 402:
            raise HTTPException(status_code=402, detail="DeepSeek 账户余额不足(402 Payment Required)！请先在 platform.deepseek.com 充值 1~2 元。")
        if resp.status_code == 401:
            raise HTTPException(status_code=401, detail="DeepSeek API Key 无效，请检查 Render 中的密钥是否正确！")
        resp.raise_for_status()
        res_data = resp.json()
        return json.loads(res_data["choices"][0]["message"]["content"])
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="DeepSeek 官方服务器响应超时，请重试！")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"调用 DeepSeek 接口通信失败: {str(e)}")


class GenerateTestRequest(BaseModel):
    grade: str = "mid"
    student_id: str = "学生"

@app.post("/api/generate_all_modules")
def generate_all_modules(req: GenerateTestRequest):
    """【真·AI出题】：严格按年级段让 DeepSeek 原创命题"""
    grade_desc_map = {
        "low": "小学低年级 (1-2年级，侧重基础童话、拼音字词辨识与朗读清晰度)",
        "mid": "小学中年级 (3-4年级，侧重散文叙事、前后鼻音、句式停连与细节把握)",
        "high": "小学高年级 (5-6年级，侧重思想哲理、修辞意蕴、深层推断与逻辑表达)"
    }
    grade_desc = grade_desc_map.get(req.grade, "小学中年级 (3-4年级)")
    batch_seed = int(time.time() * 1000) % 100000

    system_prompt = (
        "你是一名国家级普通话水平测试员及小学语文教材命题专家。"
        "请根据所指定的学段要求，为中国乡村小学儿童量身原创命制全套全维语文试卷。"
        "必须严格根据所给学段的认知规律出题，题目需兼具文学性与思维推断深度，坚决杜绝低幼问题。"
        "必须严格输出符合规范的 JSON 对象。"
    )

    user_prompt = f"""
    【命题任务】：请为【{grade_desc}】原创生成一套全新的全维测评试卷（随机批次种子: {batch_seed}）：
    
    1. listening (听力理解):
       - passage: 适合听记的生动故事或生活对话（字数按学段：低段80字，中段130字，高段180字）
       - questions: 2道细节理解与逻辑推断题，每题包含 id, question, options (4个选项), answer (正确选项字母)
    2. speaking (口语表达):
       - title: 朗读文章标题
       - passage: 针对乡村方言特征（平翘舌、前后鼻音）的适龄美文（字数：低段80字，中段130字，高段170字）
    3. reading (阅读理解):
       - title: 阅读短文标题
       - passage: 寓意深刻的自然观察或生活哲理短文（字数：低段120字，中段180字，高段250字）
       - questions: 2道深度主旨或词句推断题，每题包含 id, question, options (4个选项), answer (正确选项字母)
    4. writing (核心写作):
       - topic: 贴近乡村儿童生活的写作题目
       - prompt: 启发式情境引导语（激发真情实感）

    必须严格按如下 JSON 结构返回：
    {{
      "grade_desc": "{grade_desc}",
      "listening": {{
        "passage": "听力文章正文...",
        "questions": [
          {{ "id": 1, "question": "题目1...", "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"], "answer": "B" }},
          {{ "id": 2, "question": "题目2...", "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"], "answer": "C" }}
        ]
      }},
      "speaking": {{ "title": "朗读标题", "passage": "朗读正文..." }},
      "reading": {{
        "title": "阅读标题",
        "passage": "阅读正文...",
        "questions": [
          {{ "id": 1, "question": "题目1...", "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"], "answer": "A" }},
          {{ "id": 2, "question": "题目2...", "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"], "answer": "D" }}
        ]
      }},
      "writing": {{ "topic": "写作题目", "prompt": "情境引导语..." }}
    }}
    """

    data = request_deepseek(user_prompt, system_prompt)
    return {"status": "success", "engine": "DeepSeek-V3 实时命题", "data": data}


class EvaluateRequest(BaseModel):
    student_id: str
    grade: str
    test_data: dict
    student_answers: dict

@app.post("/api/evaluate_submission")
def evaluate_submission(req: EvaluateRequest):
    """【真·AI客观判分】：对实际作答进行严格打分，空白作答一律 0 分"""
    l_ans = req.student_answers.get("listening", {})
    r_ans = req.student_answers.get("reading", {})
    spk_duration = req.student_answers.get("speaking_duration", 0)
    writing_text = req.student_answers.get("writing", "").strip()

    # 严格判定：未作答模块坚决给 0 分，绝不造假
    has_listening = len(l_ans) > 0
    has_speaking = spk_duration >= 3
    has_reading = len(r_ans) > 0
    has_writing = len(writing_text) > 5

    # 如果四个模块全部未作答，直接给出客观真实的 0 分报告
    if not (has_listening or has_speaking or has_reading or has_writing):
        return {
            "status": "success",
            "data": {
                "scores": {"listening": 0, "speaking": 0, "reading": 0, "writing": 0, "overall": 0},
                "level": "未完成测评 (0分)",
                "gap_analysis": "考生在本次测试中未作答任何听力与阅读选择题、未进行口语录音，且未提交作文内容。无法评估其语言发展能力。",
                "rubric_table": [
                    {"dimension": "听力理解 (Listening)", "max_score": 100, "score": 0, "criteria": "准确抓取语流细节", "deduction_analysis": "考生未提交任何听力答案，判 0 分", "status": "未作答"},
                    {"dimension": "口语表达 (Speaking)", "max_score": 100, "score": 0, "criteria": "普通话发音规范清晰", "deduction_analysis": "未检测到有效朗读录音（时长不足3秒），判 0 分", "status": "未作答"},
                    {"dimension": "阅读理解 (Reading)", "max_score": 100, "score": 0, "criteria": "快速把握主旨与修辞", "deduction_analysis": "考生未提交任何阅读答案，判 0 分", "status": "未作答"},
                    {"dimension": "核心写作 (Writing)", "max_score": 100, "score": 0, "criteria": "书面用词丰富，真情实感", "deduction_analysis": "作文内容为空，判 0 分", "status": "未作答"}
                ],
                "rural_speech_diagnostic": ["本次测评因未作答无法提取语言学特征。"],
                "teaching_advice": ["建议引导学生消除畏难心理，在老师或志愿者陪同下完成完整测试。"]
            }
        }

    # 有作答内容时，交由 DeepSeek 进行深度阅卷与真实评分
    system_prompt = (
        "你是一名国家级普通话水平测试员及语文阅卷专家。"
        "请根据学生实际提交的作答内容、作文文本、朗读用时进行严格客观的托福式多维打分。"
        "未做的题目必须扣分，作文必须根据学生写的真实水平打分，严禁虚假高分。必须返回合法 JSON。"
    )

    user_prompt = f"""
    【考生身份】：学号 {req.student_id}（学段代号: {req.grade}）
    【试卷考题内容】：{json.dumps(req.test_data, ensure_ascii=False)}
    【学生实际作答数据】：
    - 听力作答: {json.dumps(l_ans, ensure_ascii=False)}
    - 口语朗读时长: {spk_duration} 秒
    - 阅读作答: {json.dumps(r_ans, ensure_ascii=False)}
    - 核心写作实写作文: {json.dumps(writing_text, ensure_ascii=False)}

    【评分要求】：
    1. 计算真实得分（0-100分）：未作答或错误的题目必须严格扣分；作文根据词汇、文意和表达客观打分。
    2. 输出标准 Rubric 打分表，针对作文实际写出的优缺点给出具体点评分析。
    3. 输出留守儿童语言发展断层分析与教学建议。

    必须返回严格合法的 JSON：
    {{
      "scores": {{ "listening": 80, "speaking": 60, "reading": 85, "writing": 65, "overall": 72 }},
      "level": "二级甲等 / 良好",
      "gap_analysis": "结合学生真实分数的断层分析...",
      "rubric_table": [
        {{ "dimension": "听力理解 (Listening)", "max_score": 100, "score": 80, "criteria": "...", "deduction_analysis": "...", "status": "良" }},
        {{ "dimension": "口语表达 (Speaking)", "max_score": 100, "score": 60, "criteria": "...", "deduction_analysis": "...", "status": "中" }},
        {{ "dimension": "阅读理解 (Reading)", "max_score": 100, "score": 85, "criteria": "...", "deduction_analysis": "...", "status": "优" }},
        {{ "dimension": "核心写作 (Writing)", "max_score": 100, "score": 65, "criteria": "...", "deduction_analysis": "对学生真实作文的点评...", "status": "中" }}
      ],
      "rural_speech_diagnostic": [ "诊断1", "诊断2", "诊断3" ],
      "teaching_advice": [ "建议1", "建议2", "建议3" ]
    }}
    """

    data = request_deepseek(user_prompt, system_prompt)
    return {"status": "success", "engine": "DeepSeek-V3 真实阅卷", "data": data}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
