"""
LLM 大题批改服务层
智批云后端 - services/llm_service.py

职责：
- 从 OCR 全文中按题号切分学生答案
- 调用 LLM（OpenAI 兼容接口）批改主观题
- 返回结构化批改结果（分数 + 评语）

answer_key 格式（向后兼容）：
  客观题: {"q1": "A", "q2": "B"}
  主观题: {"q5": {"type": "subjective", "answer": "参考答案", "score": 20, "keywords": ["关键词"]}}
  混合:   {"q1": "A", "q5": {"type": "subjective", ...}}
"""
import re
import json
import requests
from typing import Dict, List, Tuple, Optional

from config.settings import settings


# ===================== OCR 文本按题号切分 =====================

def split_ocr_by_questions(ocr_text: str, question_nums: List[int]) -> Dict[int, str]:
    """
    将 OCR 识别出的全文按题号切分为各题的学生答案文本。

    策略：用正则找 "数字 + 分隔符" 开头的行作为题号锚点，
    从一个题号到下一个题号之间的文本就是该题的答案。

    支持: "11. xxx" / "11、xxx" / "11) xxx" / "11: xxx" / "(11) xxx"
    """
    if not ocr_text:
        return {}

    lines = ocr_text.strip().split("\n")
    # 构建题号正则：匹配 11. / 11、 / 11) / (11) / 第11题 等
    num_set = set(question_nums)
    pattern = re.compile(
        r'^(?:[（(]?\s*(\d{1,3})\s*[）).、:：]\s*)|(?:第\s*(\d{1,3})\s*题)',
        re.MULTILINE
    )

    # 扫描所有行，记录题号出现的位置
    markers = []  # [(line_index, question_num)]
    for i, line in enumerate(lines):
        m = pattern.match(line.strip())
        if m:
            num_str = m.group(1) or m.group(2)
            try:
                num = int(num_str)
                if num in num_set:
                    markers.append((i, num))
            except ValueError:
                continue

    # 如果没找到任何题号标记，把全文作为唯一答案
    if not markers:
        return {q: ocr_text.strip() for q in question_nums if question_nums}

    # 切分：每两个 marker 之间的文本属于前一个题号
    result = {}
    for idx, (line_idx, q_num) in enumerate(markers):
        if idx + 1 < len(markers):
            end_idx = markers[idx + 1][0]
        else:
            end_idx = len(lines)

        # 该题的文本 = 当前行（去掉题号前缀）+ 后续行直到下一题
        first_line = lines[line_idx]
        # 去掉题号前缀
        cleaned_first = pattern.sub('', first_line.strip()).strip()
        body_lines = [cleaned_first] + lines[line_idx + 1:end_idx]
        text = "\n".join(l for l in body_lines if l.strip())
        result[q_num] = text.strip()

    return result


# ===================== LLM 批改核心 =====================

def _build_grading_prompt(
    subjective_items: List[Dict],
    student_answers: Dict[int, str]
) -> Tuple[str, str]:
    """
    构建发给 LLM 的 system prompt 和 user prompt。

    Returns: (system_prompt, user_prompt)
    """
    system_prompt = (
        "你是一位严谨负责的教师阅卷助手。你的任务是根据题目参考答案和评分标准，"
        "对学生的作答进行评分。\n\n"
        "评分规则：\n"
        "1. 按点给分，答到关键要点即给分，不必完全一致\n"
        "2. 如果有关键词列表，学生答案中出现该关键词或同义表述应给分\n"
        "3. 不得超出该题满分，最低0分\n"
        "4. 给出简短评语（不超过50字），指出得分点和不足\n\n"
        "你必须严格以 JSON 格式回复，不要包含任何其他文字。格式如下：\n"
        '```json\n[\n  {"question": "q5", "score": 15, "max_score": 20, "feedback": "得分点说明"},\n  ...\n]\n```'
    )

    # 构建题目列表
    items_text = []
    for item in subjective_items:
        q_key = item["q_key"]
        q_num = item["q_num"]
        ref_answer = item["answer"]
        max_score = item["score"]
        keywords = item.get("keywords", [])
        student_ans = student_answers.get(q_num, "（未识别到答案）")

        kw_str = f"（关键词：{', '.join(keywords)}）" if keywords else ""
        items_text.append(
            f"【{q_key}】（满分{max_score}分）{kw_str}\n"
            f"参考答案：{ref_answer}\n"
            f"学生答案：{student_ans}"
        )

    user_prompt = (
        "请批改以下主观题，每题给出分数和评语：\n\n"
        + "\n\n".join(items_text)
        + "\n\n请严格按 JSON 数组格式回复。"
    )

    return system_prompt, user_prompt


def call_llm_grade(
    subjective_items: List[Dict],
    student_answers: Dict[int, str]
) -> List[Dict]:
    """
    调用 LLM 批改主观题。

    Args:
        subjective_items: [{"q_key": "q5", "q_num": 5, "answer": "...", "score": 20, "keywords": [...]}]
        student_answers: {5: "学生写的答案文本", ...}

    Returns:
        [{"question": "q5", "score": 15.0, "max_score": 20, "feedback": "..."}]
    """
    api_key = settings.LLM_API_KEY
    if not api_key or api_key == "your_llm_api_key_here":
        raise RuntimeError(
            "LLM 未配置，请在 .env 中填写 LLM_API_KEY。"
            "DeepSeek 注册地址: https://platform.deepseek.com/"
        )

    system_prompt, user_prompt = _build_grading_prompt(subjective_items, student_answers)

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
        "temperature": 0.1,  # 低温度保证评分一致性
        "max_tokens": 2000,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()

        content = result["choices"][0]["message"]["content"]

        # 从回复中提取 JSON（兼容 ```json ... ``` 包裹和裸 JSON）
        json_str = _extract_json(content)
        if not json_str:
            raise ValueError(f"LLM 回复无法解析为 JSON: {content[:200]}")

        grading_results = json.loads(json_str)

        # 校验并规范化
        normalized = []
        for item in grading_results:
            q_key = item.get("question", "")
            score = float(item.get("score", 0))
            max_score = float(item.get("max_score", 0))
            feedback = item.get("feedback", "")

            # 确保分数不越界
            score = max(0, min(score, max_score))

            normalized.append({
                "question": q_key,
                "score": round(score, 2),
                "max_score": max_score,
                "feedback": feedback,
            })

        return normalized

    except requests.RequestException as e:
        raise RuntimeError(f"调用 LLM API 失败: {str(e)}")
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"解析 LLM 响应失败: {str(e)}")


def _extract_json(text: str) -> Optional[str]:
    """从文本中提取 JSON 数组，兼容 markdown 代码块包裹。"""
    # 先尝试找 ```json ... ```
    m = re.search(r'```(?:json)?\s*\n?(\[.*?\])\s*\n?```', text, re.DOTALL)
    if m:
        return m.group(1)

    # 再尝试找裸 JSON 数组
    m = re.search(r'\[\s*\{.*?\}\s*\]', text, re.DOTALL)
    if m:
        return m.group(0)

    return None


# ===================== 统一批改入口（客观+主观）=====================

def grade_mixed_answers(
    ocr_text: str,
    answer_key: Dict,
    total_score: float,
    ocr_result: Optional[Dict] = None
) -> Tuple[float, List[Dict]]:
    """
    混合批改：客观题用正则比对，主观题用 LLM。

    answer_key 格式：
      客观题: {"q1": "A"}
      主观题: {"q5": {"type": "subjective", "answer": "...", "score": 20, "keywords": [...]}}

    Args:
        ocr_text: OCR 识别出的全文
        answer_key: 标准答案
        total_score: 试卷总分
        ocr_result: 已解析的客观题答案（可选，避免重复解析）

    Returns:
        (ai_score, detail_list)
    """
    if not answer_key:
        return 0.0, []

    # 分离客观题和主观题
    objective_keys = []   # [(q_num, q_key, correct_answer)]
    subjective_items = []  # [{"q_key", "q_num", "answer", "score", "keywords"}]

    for q_key, val in answer_key.items():
        q_num = _extract_q_num(q_key)

        if isinstance(val, dict) and val.get("type") == "subjective":
            subjective_items.append({
                "q_key": q_key,
                "q_num": q_num,
                "answer": val.get("answer", ""),
                "score": float(val.get("score", 0)),
                "keywords": val.get("keywords", []),
            })
        else:
            # 字符串值 = 客观题（向后兼容）
            objective_keys.append((q_num, q_key, val))

    detail_list = []
    ai_score = 0.0

    # ===== 客观题：正则比对 =====
    if objective_keys:
        from services.ocr_service import parse_ocr_text_to_answers, auto_grade_answers

        # 构建纯客观题 answer_key
        obj_answer_key = {q_key: ans for _, q_key, ans in objective_keys}

        if ocr_result:
            # 已有 OCR 结果，直接用
            obj_ocr = {q_key: ocr_result.get(q_key, "") for q_key in obj_answer_key}
        else:
            obj_ocr = parse_ocr_text_to_answers(ocr_text, obj_answer_key)

        obj_score, obj_detail = auto_grade_answers(obj_ocr, obj_answer_key, 0)
        # auto_grade_answers 用总分0算每题分=0，需要手动算
        obj_count = len(obj_answer_key)
        # 客观题总分 = 试卷总分 - 主观题总分
        subjective_total = sum(item["score"] for item in subjective_items)
        objective_total = total_score - subjective_total
        per_q = objective_total / obj_count if obj_count > 0 else 0

        for d in obj_detail:
            d["score"] = round(per_q, 2) if d["is_correct"] else 0.0
            d["max_score"] = round(per_q, 2)
            d["type"] = "objective"
            if d["is_correct"]:
                ai_score += per_q
            detail_list.append(d)

    # ===== 主观题：LLM 批改 =====
    if subjective_items:
        # 从 OCR 全文中切分各题答案
        q_nums = [item["q_num"] for item in subjective_items]
        student_answers = split_ocr_by_questions(ocr_text, q_nums)

        # 调用 LLM
        llm_results = call_llm_grade(subjective_items, student_answers)

        # 构建 q_key → item 的映射
        item_map = {item["q_key"]: item for item in subjective_items}
        q_num_map = {item["q_num"]: item["q_key"] for item in subjective_items}

        for llm_r in llm_results:
            q_key = llm_r["question"]
            item = item_map.get(q_key)
            if not item:
                # 尝试用题号匹配
                q_key = q_num_map.get(_extract_q_num(q_key), q_key)
                item = item_map.get(q_key)
            if not item:
                continue

            score = llm_r["score"]
            max_score = llm_r["max_score"] or item["score"]
            ai_score += score

            detail_list.append({
                "question": item["q_key"],
                "student_answer": student_answers.get(item["q_num"], "（未识别）"),
                "correct_answer": item["answer"],
                "is_correct": score >= max_score * 0.6,  # 60%以上算基本正确
                "score": round(score, 2),
                "max_score": round(max_score, 2),
                "type": "subjective",
                "feedback": llm_r["feedback"],
            })

    return round(ai_score, 2), detail_list


def _extract_q_num(q_key: str) -> int:
    """从 q_key 中提取题号，如 'q5' → 5, 'Q12' → 12。"""
    num = re.sub(r'[^0-9]', '', q_key)
    try:
        return int(num) if num else 9999
    except ValueError:
        return 9999
