"""
OCR 服务层 — 从控制器中提取的 OCR 解析与批改业务逻辑
智批云后端 - services/ocr_service.py

职责：
- OCR 文本解析为结构化答案（原 parse_ocr_text_to_answers）
- 自动批改比对（原 auto_grade）
- 不依赖 HTTP 类型（Request/Response/HTTPException）
"""
import re
from typing import Dict, List, Optional, Tuple


def parse_ocr_text_to_answers(
    ocr_text: str,
    answer_key: Dict,
    words_result: Optional[List[Dict]] = None
) -> Dict:
    """
    将OCR识别的文本解析为结构化答案。

    针对手写选择题答卷优化，支持三种模式：

    模式A — 结构化答卷（如 "1. A / 2. D"）：
      按题号+空格/标点+字母的正则匹配提取

    模式B — 纯字母列表（如 "A D D C"）：
      检测到连续字母时按顺序分配给各题

    模式C — 位置排序兜底：
      利用OCR返回的词坐标，从上到下从左到右排序，
      筛选出单个A-D字母，按题号顺序分配
    """
    result = {}
    if not answer_key:
        return result

    question_count = len(answer_key)

    # 构建有序题号列表
    q_items = []
    for q_key in answer_key.keys():
        q_num = q_key.replace("q", "").replace("Q", "")
        try:
            q_items.append((int(q_num), q_key))
        except ValueError:
            q_items.append((9999, q_key))
    q_items.sort()
    ordered_keys = [k for _, k in q_items]

    lines = [line.strip() for line in ocr_text.strip().split("\n") if line.strip()]

    # ========== 模式A：结构化匹配 ==========
    found_structured = 0
    ocr_upper = ocr_text.upper()
    for idx, q_key in enumerate(ordered_keys):
        q_num = str(idx + 1)
        student_ans = ""

        patterns_a = [
            rf"(?<!\d){q_num}\s*[.、,:：)\]]\s*([A-D])(?!\s*[a-z])",
            rf"第\s*{q_num}\s*题\s*[:：]?\s*([A-D])",
            rf"\(\s*{q_num}\s*\)\s*([A-D])",
            rf"(?<!\d){q_num}\s+([A-D])\b",
        ]
        for pat in patterns_a:
            m = re.search(pat, ocr_upper)
            if m:
                student_ans = m.group(1)
                break

        if not student_ans:
            m = re.search(rf"(?<!\d){q_num}([A-D])(?!\s*[a-z])", ocr_upper)
            if m:
                student_ans = m.group(1)

        result[q_key] = student_ans
        if student_ans:
            found_structured += 1

    if found_structured >= question_count * 0.5:
        return result

    # ========== 模式B：纯字母序列 ==========
    letter_sequence = []
    for line in lines:
        stripped = line.strip().upper()
        clean = re.sub(r'[\s.、,，;；()（）\[\]{}|/\\\-_=+*&^%$#@!~`\'"]', '', stripped)
        if clean and all(c in 'ABCD' for c in clean) and len(clean) <= 4:
            letter_sequence.extend(list(clean))

    if len(letter_sequence) >= question_count * 0.6:
        for i, q_key in enumerate(ordered_keys):
            if i < len(letter_sequence):
                result[q_key] = letter_sequence[i]
            else:
                result[q_key] = result.get(q_key, "")
        return result

    # ========== 模式C：位置排序兜底 ==========
    if words_result:
        letter_items = []
        for item in words_result:
            word = item.get("words", "").strip().upper()
            loc = item.get("location", {})
            clean_word = re.sub(r'[^A-D]', '', word)
            if len(clean_word) == 1 and clean_word in 'ABCD':
                top = loc.get("top", 0)
                left = loc.get("left", 0)
                letter_items.append({"letter": clean_word, "y": top, "x": left})

        if letter_items:
            letter_items.sort(key=lambda it: it["y"])
            rows = []
            current_row = [letter_items[0]]
            for item in letter_items[1:]:
                if abs(item["y"] - current_row[-1]["y"]) < 30:
                    current_row.append(item)
                else:
                    rows.append(current_row)
                    current_row = [item]
            rows.append(current_row)

            for row in rows:
                row.sort(key=lambda it: it["x"])

            ordered_letters = []
            for row in rows:
                ordered_letters.extend([it["letter"] for it in row])

            filtered_letters = []
            for row in rows:
                if len(row) <= 4:
                    filtered_letters.extend([it["letter"] for it in row])

            source = filtered_letters if len(filtered_letters) >= question_count * 0.4 else ordered_letters

            for i, q_key in enumerate(ordered_keys):
                if not result.get(q_key) and i < len(source):
                    result[q_key] = source[i]
                elif not result.get(q_key):
                    result[q_key] = ""

    for q_key in ordered_keys:
        if q_key not in result:
            result[q_key] = ""

    return result


def auto_grade_answers(
    ocr_result: dict,
    answer_key: dict,
    total_score: float
) -> Tuple[float, List[Dict]]:
    """
    自动批改：比对 OCR 识别结果和标准答案

    Args:
        ocr_result:  学生答案 {q1: 'A', q2: 'B', ...}
        answer_key:  标准答案 {q1: 'A', q2: 'B', ...}
        total_score: 试卷总分

    Returns:
        (ai_score, detail_list)
            ai_score:      AI 批阅分数
            detail_list:   每题批改详情
    """
    if not answer_key:
        return 0.0, []

    total_questions = len(answer_key)
    ai_score = 0.0
    detail_list = []

    per_question_score = total_score / total_questions if total_questions > 0 else 0

    for q_key, correct_ans in answer_key.items():
        student_ans = ocr_result.get(q_key, "")
        is_correct = False

        if isinstance(correct_ans, str) and isinstance(student_ans, str):
            if not student_ans:
                is_correct = False
            elif "," in student_ans or "，" in student_ans:
                student_set = set(student_ans.replace(" ", "").replace("，", ",").split(","))
                correct_set = set(correct_ans.replace(" ", "").replace("，", ",").split(","))
                is_correct = student_set == correct_set
            else:
                is_correct = student_ans.strip().upper() == correct_ans.strip().upper()

        earned_score = per_question_score if is_correct else 0.0
        if is_correct:
            ai_score += per_question_score

        detail_list.append({
            "question": q_key,
            "student_answer": student_ans if student_ans else "（未识别）",
            "correct_answer": correct_ans,
            "is_correct": is_correct,
            "score": round(earned_score, 2)
        })

    return round(ai_score, 2), detail_list
