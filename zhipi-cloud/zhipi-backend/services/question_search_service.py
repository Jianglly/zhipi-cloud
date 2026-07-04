"""
DeepSeek 搜题服务层
智批云后端 - services/question_search_service.py

职责：
- 将OCR识别出的试卷题目文本发给 DeepSeek，让LLM给出正确答案
- 解析LLM回复为结构化 answer_key（可直接存入 Paper.answer_key）
- 支持三种题型：objective（选择）、fill_blank（填空）、subjective（主观）
- 作为"搜题软件"的替身方案：利用LLM的海量知识替代题库API

answer_key 输出格式（与现有系统兼容）：
  客观题: {"q1": "A", "q2": "B", "q3": "C"}
  填空:   {"q4": {"type": "fill_blank", "answer": "光合作用", "score": 2}}
  主观:   {"q5": {"type": "subjective", "answer": "参考答案...", "score": 10, "keywords": ["关键点1"]}}
"""
import re
import json
import requests
from typing import Dict, Optional, Tuple

from config.settings import settings


# ===================== LLM 搜题核心 =====================

def _build_search_prompt(subject: str, ocr_text: str, total_score: float = 100) -> Tuple[str, str]:
    """
    构建搜题提示词 (system + user)。

    Args:
        subject: 科目（语文/数学/英语）
        ocr_text: OCR识别出的试卷题目全文
        total_score: 试卷总分（用于估算每题分值）

    Returns:
        (system_prompt, user_prompt)
    """
    subject_map = {
        "语文": "语文",
        "数学": "数学",
        "英语": "英语",
    }
    subject_name = subject_map.get(subject, subject)

    system_prompt = (
        f"你是一位经验丰富的{subject_name}教师。你的任务是阅读一份试卷的OCR文本，"
        "识别每道题目的题型，并给出正确答案。\n\n"
        "规则：\n"
        "1. 选择题（单选）：答案为单个字母 A/B/C/D\n"
        "2. 选择题（多选）：答案为逗号分隔的字母，如 'A,D'\n"
        "3. 填空题：答案为具体的文字/数字/单词\n"
        "4. 主观题（解答题/作文/翻译）：给出参考答案要点和评分关键词\n"
        f"5. 试卷总分 {total_score} 分，请合理分配每题分值\n"
        f"6. 客观题每题分数应相等；主观题根据难度分配\n\n"
        "你必须严格按照以下 JSON 格式回复，不要包含任何其他文字：\n"
        "```json\n"
        "{\n"
        '  "questions": [\n'
        '    {"num": 1, "type": "objective", "question": "题目内容摘要", "answer": "B", "score": 5},\n'
        '    {"num": 2, "type": "fill_blank", "question": "题目内容摘要", "answer": "正确答案", "score": 3},\n'
        '    {"num": 3, "type": "subjective", "question": "题目内容摘要", "answer": "参考答案要点", "score": 12, "keywords": ["要点1", "要点2"]}\n'
        "  ]\n"
        "}\n"
        "```"
    )

    user_prompt = (
        f"以下是{subject_name}试卷的OCR识别文本，请分析所有题目并给出正确答案：\n\n"
        f"--- 试卷内容 ---\n"
        f"{ocr_text}\n"
        f"--- 结束 ---\n\n"
        f"试卷总分：{total_score}分\n"
        "请严格按 JSON 数组格式回复。"
    )

    return system_prompt, user_prompt


def call_llm_search(ocr_text: str, subject: str, total_score: float = 100) -> Dict:
    """
    调用 DeepSeek LLM 搜题，返回结构化 answer_key。

    Args:
        ocr_text: OCR识别出的试卷题目文本
        subject: 科目（语文/数学/英语）
        total_score: 试卷总分

    Returns:
        answer_key 格式的字典，如 {"q1": "A", "q2": "B", ...}

    Raises:
        RuntimeError: LLM未配置或调用失败
        ValueError: LLM回复无法解析
    """
    api_key = settings.LLM_API_KEY
    if not api_key or api_key == "your_llm_api_key_here":
        raise RuntimeError(
            "LLM 未配置，无法使用搜题功能。请在 .env 中填写 LLM_API_KEY。\n"
            "DeepSeek 注册地址: https://platform.deepseek.com/"
        )

    system_prompt, user_prompt = _build_search_prompt(subject, ocr_text, total_score)

    url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.05,  # 极低温度确保答案确定性
        "max_tokens": 3000,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=90)
        resp.raise_for_status()
        result = resp.json()
        content = result["choices"][0]["message"]["content"]

        # 提取 JSON
        json_str = _extract_json(content)
        if not json_str:
            raise ValueError(
                f"LLM 回复无法解析为 JSON。\n"
                f"原始回复前300字符: {content[:300]}"
            )

        parsed = json.loads(json_str)
        answer_key = _parse_search_result(parsed, subject)

        if not answer_key:
            raise ValueError("LLM 未识别到任何题目，请检查试卷图片是否清晰")

        return answer_key

    except requests.RequestException as e:
        raise RuntimeError(f"调用 LLM API 失败: {str(e)}")
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"解析 LLM 响应失败: {str(e)}")


def _extract_json(text: str) -> Optional[str]:
    """从 LLM 回复中提取 JSON，兼容 markdown 代码块包裹。"""
    # 尝试 ```json { ... } ```
    m = re.search(r'```(?:json)?\s*\n?(\{.*?\})\s*\n?```', text, re.DOTALL)
    if m:
        return m.group(1)

    # 尝试裸 JSON 对象
    m = re.search(r'\{\s*"questions"\s*:\s*\[.*?\]\s*\}', text, re.DOTALL)
    if m:
        return m.group(0)

    return None


def _parse_search_result(parsed: Dict, subject: str) -> Dict:
    """
    将 LLM 返回的题目列表转换为系统 answer_key 格式。

    输入格式（LLM返回）:
        {"questions": [{"num": 1, "type": "objective", "answer": "B", ...}, ...]}

    输出格式（系统标准）:
        {"q1": "B", "q5": {"type": "subjective", "answer": "...", "score": 10, "keywords": [...]}}
    """
    questions = parsed.get("questions", [])
    if not isinstance(questions, list):
        questions = []

    answer_key = {}
    for q in questions:
        if not isinstance(q, dict):
            continue

        q_num = q.get("num", 0)
        q_type = q.get("type", "objective")
        answer = q.get("answer", "")
        score = q.get("score", 0)
        keywords = q.get("keywords", [])

        q_key = f"q{q_num}"

        if q_type == "objective":
            # 选择题：直接存答案字母
            answer_key[q_key] = str(answer).strip().upper()
        elif q_type in ("subjective", "fill_blank"):
            # 主观题 & 填空题：存 dict
            answer_key[q_key] = {
                "type": q_type,
                "answer": str(answer).strip() if answer else "",
                "score": float(score) if score else 0,
            }
            if keywords and isinstance(keywords, list):
                answer_key[q_key]["keywords"] = [str(k) for k in keywords if k]
        else:
            # 未知类型降级为客观题
            answer_key[q_key] = str(answer).strip().upper()

    return answer_key


# ===================== 从OCR图片完整搜题（集成OCR+LLM） =====================

def search_answers_from_image(
    image_path: str,
    subject: str,
    total_score: float = 100,
    answer_key: Optional[Dict] = None
) -> Dict:
    """
    完整链路：OCR图片 → LLM搜答案 → 返回结构化 answer_key。

    如果传入了 answer_key（已有部分答案），则LLM只补充缺失的题目。

    Args:
        image_path: 试卷图片路径
        subject: 科目
        total_score: 试卷总分
        answer_key: 已有的部分答案（可选，用于增量补充）

    Returns:
        answer_key 格式的字典
    """
    # 调用百度OCR（从 ocr_controller 复用）
    from controllers.ocr_controller import call_baidu_ocr
    ocr_text, _ = call_baidu_ocr(image_path)

    if not ocr_text or not ocr_text.strip():
        raise RuntimeError("试卷图片OCR识别为空，请检查图片清晰度")

    # 如果已有部分答案，在 prompt 中告知
    if answer_key and len(answer_key) > 0:
        existing_info = f"\n\n注意：以下题目已有标准答案，请勿重复给出：\n{json.dumps(answer_key, ensure_ascii=False, indent=2)}"
        ocr_text = ocr_text + existing_info

    return call_llm_search(ocr_text, subject, total_score)
