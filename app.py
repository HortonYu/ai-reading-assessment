# -*- coding: utf-8 -*-
"""
全维语言能力 AI 评测平台 - 后端核心
100% 真实调用 DeepSeek 动态出题与深度批阅打分
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

app = FastAPI(title="乡村教育全维语言评测引擎", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 寻找前端目录
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
    return HTMLResponse("<h2>AI评测服务运行中</h2>")

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

# 真实调用 DeepSeek API（设置充足超时为 60 秒）
def call_deepseek(prompt: str, system_prompt: str, user_api_key: str = None) -> dict:
    api_key = (user_api_key or DEEPSEEK_API_KEY).strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="未检测到有效 DeepSeek API Key，请检查配置！")

    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "response_format": {"type": "json_object"}
    }
    
    # 充足超时，保证 DeepSeek 完整生成整套卷子
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    res_data = resp.json()
    return json.loads(res_data["choices"][0]["message"]["content"])


class GenerateTestRequest(BaseModel):
    grade: str = "mid"
    student_id: str = "学生"
    api_key: str = ""

@app.post("/api/generate_all_modules")
def generate_all_modules(req: GenerateTestRequest):
    """【真·AI出题】：由 DeepSeek 根据学段深度命制全套考卷"""
    grade_desc_map = {
        "low": "小学低年级 (1-2年级，以声韵母辨识与童趣故事为主)",
        "mid": "小学中年级 (3-4年级，注重前后鼻音、句式连贯与细节概括)",
        "high": "小学高年级 (5-6年级，注重语调修辞、情感内涵与逻辑思维)"
    }
    grade_desc = grade_desc_map.get(req.grade, "小学中年级 (3-4年级)")

    system_prompt = (
        "你是一名国家级普通话水平测试员、小学语文课标命题专家，深耕中国乡村教育。"
        "请为指定学段量身原创一套高品质全维语文测评试题（包含听力、口语、阅读、写作）。"
        "题目必须兼具文学性与思维推断深度，坚决杜绝低幼直白问题。必须返回合规的 JSON 对象。"
    )

    user_prompt = f"""
    请为【{grade_desc}】动态创作一套全维语文综合测评试卷（随机批次: {int(time.time()*1000)%10000}）：

    【四模块具体命题指标】：
    1. listening (听力理解):
       - passage: 适合听记的哲理小故事或生活观察故事（110-150字）
       - questions: 2道细节理解与深层推断选择题，每题必须包含 id, question, options (A/B/C/D四个完整选项), answer (正确选项字母如 "A"或"B")
    2. speaking (口语表达):
       - title: 朗读文章标题
       - passage: 优美散文语段（110-140字，融入平翘舌zh/ch/sh、前后鼻音en/eng、in/ing等易错发音）
    3. reading (阅读理解):
       - title: 阅读短文标题
       - passage: 寓意深刻的自然观察或生活哲理微短文（160-220字）
       - questions: 2道深度主旨推断或词句含义分析题，每题包含 id, question, options (A/B/C/D四个选项), answer (正确选项字母)
    4. writing (核心写作):
       - topic: 作文题目
       - prompt: 启发式情境引导语（80-120字要求，激发乡村儿童真情实感表达）

    严格返回如下结构的合规 JSON：
    {{
      "grade_desc": "{grade_desc}",
      "listening": {{
        "passage": "听力播报正文...",
        "questions": [
          {{ "id": 1, "question": "听力题目1...", "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"], "answer": "B" }},
          {{ "id": 2, "question": "听力题目2...", "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"], "answer": "C" }}
        ]
      }},
      "speaking": {{
        "title": "朗读篇名",
        "passage": "朗读全文..."
      }},
      "reading": {{
        "title": "阅读短文标题",
        "passage": "阅读正文...",
        "questions": [
          {{ "id": 1, "question": "阅读题目1...", "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"], "answer": "A" }},
          {{ "id": 2, "question": "阅读题目2...", "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"], "answer": "D" }}
        ]
      }},
      "writing": {{
        "topic": "写作题目",
        "prompt": "情境引导语..."
      }}
    }}
    """

    try:
        data = call_deepseek(user_prompt, system_prompt, req.api_key)
        return {"status": "success", "engine": "DeepSeek-V3 实时命题", "data": data}
    except Exception as e:
        print(f"DeepSeek 出题报错: {e}")
        raise HTTPException(status_code=500, detail=f"DeepSeek 命题失败: {str(e)}")


class EvaluateRequest(BaseModel):
    student_id: str
    grade: str
    test_data: dict
    student_answers: dict
    api_key: str = ""

@app.post("/api/evaluate_submission")
def evaluate_submission(req: EvaluateRequest):
    """【真·AI打分】：由 DeepSeek 亲自批阅作答，量化打分并生成 Rubric 与多维图谱数据"""
    grade_desc_map = {"low": "小学低年级", "mid": "小学中年级", "high": "小学高年级"}
    grade_desc = grade_desc_map.get(req.grade, "小学中年级")

    system_prompt = (
        "你是一名国家级普通话测试员、儿童语言心理学专家及语文阅卷专家。"
        "请对乡村小学留守儿童的实际作答（尤其是写作作文内容、口语用时和选择题）进行严谨客观的托福式多维打分。"
        "必须结合学生实际写出的作文内容给出具体评析，严禁千篇一律套话。必须返回合规 JSON。"
    )

    user_prompt = f"""
    【考生身份】：学号 {req.student_id}（学段: {grade_desc}）
    【试卷考题内容】：
    - 听力材料: {req.test_data.get('listening', {}).get('passage', '')}
    - 听力题目与答案: {json.dumps(req.test_data.get('listening', {}).get('questions', []), ensure_ascii=False)}
    - 口语朗读文本: {req.test_data.get('speaking', {}).get('passage', '')}
    - 阅读材料与题目: {json.dumps(req.test_data.get('reading', {}), ensure_ascii=False)}
    - 写作题目与要求: {json.dumps(req.test_data.get('writing', {}), ensure_ascii=False)}

    【学生实际作答内容】：
    - 听力选择作答: {req.student_answers.get('listening', {})}
    - 口语朗读实际用时: {req.student_answers.get('speaking_duration', 0)} 秒
    - 阅读选择作答: {req.student_answers.get('reading', {})}
    - 核心写作学生实际提交作文: {json.dumps(req.student_answers.get('writing', ''), ensure_ascii=False)}

    【打分与诊断要求】：
    请客观给出四个维度分值（0-100分），并撰写标准 Rubric 打分细则表和留守儿童语言发展诊断报告。

    严格返回如下 JSON 结构：
    {{
      "scores": {{
        "listening": 85,
        "speaking": 68,
        "reading": 90,
        "writing": 72,
        "overall": 79
      }},
      "level": "二级甲等 / 良好",
      "gap_analysis": "深入分析该学生在输入型能力与输出型能力之间的发展断层特征...",
      "rubric_table": [
        {{ "dimension": "听力理解 (Listening)", "max_score": 100, "score": 85, "criteria": "评分基准...", "deduction_analysis": "具体失分与得分析...", "status": "优秀" }},
        {{ "dimension": "口语表达 (Speaking)", "max_score": 100, "score": 68, "criteria": "评分基准...", "deduction_analysis": "具体分析...", "status": "需强化" }},
        {{ "dimension": "阅读理解 (Reading)", "max_score": 100, "score": 90, "criteria": "评分基准...", "deduction_analysis": "具体分析...", "status": "优秀" }},
        {{ "dimension": "核心写作 (Writing)", "max_score": 100, "score": 72, "criteria": "结合学生作文语句、词汇的评分基准...", "deduction_analysis": "针对学生真实作文内容的批改点评...", "status": "中等" }}
      ],
      "rural_speech_diagnostic": [
        "针对发音与心理特征诊断项1",
        "针对发音与心理特征诊断项2",
        "针对书面表达特征诊断项3"
      ],
      "teaching_advice": [
        "教学提升对策1",
        "亲情伴读对策2",
        "写作支架对策3"
      ]
    }}
    """

    try:
        data = call_deepseek(user_prompt, system_prompt, req.api_key)
        return {"status": "success", "engine": "DeepSeek-V3 真实批阅", "data": data}
    except Exception as e:
        print(f"DeepSeek 打分报错: {e}")
        raise HTTPException(status_code=500, detail=f"DeepSeek 批阅失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
