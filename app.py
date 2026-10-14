# -*- coding: utf-8 -*-
"""
全维语言能力 AI 评测平台 - 后端服务
深度对接 DeepSeek-V3 / DeepSeek-R1 模型
"""
import os
import time
import json
import random
import requests
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="乡村教育语言综合评测引擎", version="3.0.0")

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

def call_deepseek_api(prompt: str, system_prompt: str, user_api_key: str = None) -> dict:
    """调用 DeepSeek 官方 API，确保严格返回 JSON"""
    api_key = (user_api_key or DEEPSEEK_API_KEY).strip()
    if not api_key or api_key.startswith("sk-你的"):
        raise HTTPException(
            status_code=400, 
            detail="【未检测到有效的 DeepSeek API Key】请在页面右上角或 backend/.env 文件中配置你的 sk-xxx 密钥！"
        )

    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # 加入随机温度与时间戳 seed，保证每次点击生成完全不同的全新考题
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.85,
        "response_format": {"type": "json_object"}
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        res_json = resp.json()
        content = res_json["choices"][0]["message"]["content"]
        return json.loads(content)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"DeepSeek 接口通信失败: {str(e)}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="DeepSeek 返回的内容无法解析为标准 JSON，请重试")


class GenerateTestRequest(BaseModel):
    grade: str  # low (1-2), mid (3-4), high (5-6)
    student_id: str = "学生"
    api_key: str = ""

@app.post("/api/generate_all_modules")
def generate_all_modules(req: GenerateTestRequest):
    """
    一次性由 DeepSeek 动态生成涵盖听力、口语、阅读、写作的整套高级试卷
    要求题目富含文学性与思维推断，杜绝幼稚化
    """
    grade_map = {
        "low": "小学低年级 (1-2年级)",
        "mid": "小学中年级 (3-4年级)",
        "high": "小学高年级 (5-6年级)"
    }
    grade_desc = grade_map.get(req.grade, "小学中年级 (3-4年级)")
    rand_seed = int(time.time() * 1000) % 10000

    system_prompt = (
        "你是一名国家级普通话测试员、义务教育语文课标核心组命题专家，长期研究乡村教育及留守儿童语言发展。"
        "你需要生成一份针对该学段的高品质全维语文测评试卷。题目必须富有思考深度和文学美感，绝不能过于简单或直白。"
        "必须返回严格合法的 JSON 对象。"
    )

    user_prompt = f"""
    【命题任务】：请为【{grade_desc}】量身生成一套全维语文综合测评试题（随机批次代号: {rand_seed}）。
    
    要求包含以下四个完整模块，杜绝低幼问题：
    1. 【听力理解模块 (listening)】：
       - 听力材料 (passage)：一段 120-180 字的生动故事或生活对话（适合朗读播报，蕴含细节事实与情理）。
       - 2 道听力选择题 (questions)：每题必须有 A/B/C/D 4个具有迷惑性的选项，考查听力细节提取和意图推断，注明正确答案 (answer: "A"等)。
    2. 【口语表达模块 (speaking)】：
       - 朗读文章 (passage)：一段 120-160 字的优美散文，刻意嵌入容易引发方言负迁移的字词（如平翘舌 zh/ch/sh 与 z/c/s、前后鼻音 en/eng、in/ing、l/n）。
       - 考查要点 (focus_phonetics)：列出 4-6 个重点音韵字词。
    3. 【阅读理解模块 (reading)】：
       - 阅读短文 (passage)：一段 200-280 字具有哲理性、自然观察或生活趣味的微散文。
       - 2 道深度理解题 (questions)：考察词语语境义、主旨推理或言外之意，每题 4 个选项 (A/B/C/D)，注明正确答案 (answer)。
    4. 【核心写作模块 (writing)】：
       - 写作情境题 (prompt)：富有情感温度、激发乡村儿童主动表达的命题或半命题情境（如写给远方父母的心里话、家乡某一处细微变化等），附带字数要求与思维引导点。

    必须输出以下严格 JSON 结构：
    {{
      "grade_desc": "{grade_desc}",
      "listening": {{
        "passage": "听力播报正文...",
        "questions": [
          {{ "id": 1, "question": "题目1...", "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"], "answer": "B" }},
          {{ "id": 2, "question": "题目2...", "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"], "answer": "C" }}
        ]
      }},
      "speaking": {{
        "title": "朗读篇名",
        "passage": "朗读全文...",
        "word_count": 135,
        "focus_phonetics": ["笼罩 (zhào)", "穿透 (chuān)", "清脆 (cuì)"]
      }},
      "reading": {{
        "title": "阅读短文标题",
        "passage": "短文正文...",
        "questions": [
          {{ "id": 1, "question": "推断题1...", "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"], "answer": "A" }},
          {{ "id": 2, "question": "主旨题2...", "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"], "answer": "D" }}
        ]
      }},
      "writing": {{
        "topic": "写作题目",
        "prompt": "详细的情境引导说明...",
        "min_words": 60
      }},
      "quality_audit": {{
        "is_sufficient": true,
        "audit_note": "四大模块题量配比完全契合部编版课标，阅读量和思维层次具有合理区分度。"
      }}
    }}
    """

    return {"status": "success", "data": call_deepseek_api(user_prompt, system_prompt, req.api_key)}


class EvaluateRequest(BaseModel):
    student_id: str
    grade: str
    test_data: dict
    student_answers: dict
    api_key: str = ""

@app.post("/api/evaluate_submission")
def evaluate_submission(req: EvaluateRequest):
    """
    由 DeepSeek 对学生的完整作答进行多维综合评测，生成托福式 Rubric 与留守儿童断层诊断
    """
    system_prompt = (
        "你是一名资深教育测量学专家和儿童语言心理学专家。"
        "请根据学生的作答情况，给出严谨客观的托福式四维分值、标准化 Rubric 表格、"
        "并深入分析该乡村儿童‘输入型能力’与‘输出型能力’的断层发展模式。"
    )

    user_prompt = f"""
    【学生身份】：学号 {req.student_id}（学段: {req.grade}）
    【试卷考题内容】：
    {json.dumps(req.test_data, ensure_ascii=False)}

    【学生实际作答数据】：
    {json.dumps(req.student_answers, ensure_ascii=False)}

    请根据上述数据执行客观批阅，输出严格 JSON：
    {{
      "scores": {{
        "listening": 85,
        "speaking": 68,
        "reading": 90,
        "writing": 72,
        "overall": 79
      }},
      "level": "良好 / 二级甲等水平",
      "gap_analysis": "该学生的输入型能力（听力85、阅读90）显著优于输出型能力（口语68、写作72），呈现典型的留守儿童语言输入输出断层特征。",
      "rubric_table": [
        {{
          "dimension": "听力理解 (Listening)",
          "max_score": 100,
          "score": 85,
          "criteria": "能够准确抓取语流细节，理解深层言外之意",
          "deduction_analysis": "在深层推理题上略有粗心，关键信息捕捉基本准确",
          "status": "优秀"
        }},
        {{
          "dimension": "口语表达 (Speaking)",
          "max_score": 100,
          "score": 68,
          "criteria": "声韵调标准规范，平翘舌清晰，语流自然无唱读",
          "deduction_analysis": "存在明显的方言舌位靠前替代现象，后半程声音变小，缺乏语调起伏",
          "status": "需强化"
        }},
        {{
          "dimension": "阅读理解 (Reading)",
          "max_score": 100,
          "score": 90,
          "criteria": "快速把握主旨，理解语境深意与修辞手法",
          "deduction_analysis": "对文章情感态度把握精准，识字量达到该学段高分要求",
          "status": "优秀"
        }},
        {{
          "dimension": "核心写作 (Writing)",
          "max_score": 100,
          "score": 72,
          "criteria": "语句通顺，书面语表达丰富，情感真挚，逻辑清晰",
          "deduction_analysis": "书面词汇储备相对局限，口语化表达痕迹明显，但在真情实感上表现出色",
          "status": "中等"
        }}
      ],
      "rural_speech_diagnostic": [
        "平翘舌界限模糊：受家庭方言环境影响，zh/ch/sh 发音位置普遍偏平",
        "音量渐弱效应：独诵时后半段吞音明显，表现出缺乏日常伴读肯定的羞怯心理",
        "词汇输入与输出不对称：能读懂高阶词汇，但日常写作倾向于使用极为有限的口语词"
      ],
      "teaching_advice": [
        "推行‘朗读伙伴计划’：每日早读让学生开展结对互听互纠，重点解决翘舌音问题。",
        "设置‘口语录音日记’：鼓励学生每周录下一段与外出务工父母的分享语音，建立表达自信。",
        "由词入句写作支架训练：提供高频书面关联词与情感描写词卡，跨越表达断层。"
      ]
    }}
    """

    return {"status": "success", "data": call_deepseek_api(user_prompt, system_prompt, req.api_key)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
