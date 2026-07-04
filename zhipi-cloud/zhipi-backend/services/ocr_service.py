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

    支持两类题目：
    - 选择题（objective，answer_key 值为字符串如 "A"）：
      三模式匹配 — 结构化 / 纯字母序列 / 坐标排序
    - 填空题 & 主观题（answer_key 值为 dict）：
      尝试按题号提取该行后续文本作为学生答案
    """
    result = {}
    if not answer_key:
        return result

    # 区分选择题和非选择题
    objective_keys = []
    text_keys = []
    for q_key, val in answer_key.items():
        if isinstance(val, str):
            objective_keys.append(q_key)
        else:
            text_keys.append(q_key)

    question_count = len(objective_keys)

    # 构建选择题有序题号列表
    q_items = []
    for q_key in objective_keys:
        q_num = q_key.replace("q", "").replace("Q", "")
        try:
            q_items.append((int(q_num), q_key))
        except ValueError:
            q_items.append((9999, q_key))
    q_items.sort()
    ordered_keys = [k for _, k in q_items]

    lines = [line.strip() for line in ocr_text.strip().split("\n") if line.strip()]

    # ========== 选择题：模式A — 结构化匹配 ==========
    found_structured = 0
    ocr_upper = ocr_text.upper()
    for idx, q_key in enumerate(ordered_keys):
        q_num = str(idx + 1)
        student_ans = ""

        # 捕获单选 [A-D] 或多选 [A-D,A-D,...]（逗号分隔）
        multi = r"([A-D](?:\s*[,，]\s*[A-D])*)"
        patterns_a = [
            rf"(?<!\d){q_num}\s*[.、,:：)\]]\s*{multi}",
            rf"第\s*{q_num}\s*题\s*[:：]?\s*{multi}",
            rf"\(\s*{q_num}\s*\)\s*{multi}",
            rf"(?<!\d){q_num}\s+{multi}\b",
        ]
        for pat in patterns_a:
            m = re.search(pat, ocr_upper)
            if m:
                student_ans = m.group(1)
                break

        if not student_ans:
            m = re.search(rf"(?<!\d){q_num}{multi}", ocr_upper)
            if m:
                student_ans = m.group(1)

        result[q_key] = student_ans
        if student_ans:
            found_structured += 1

    if found_structured >= max(question_count * 0.5, 1) if question_count > 0 else True:
        pass  # 继续执行后续模式，不提前 return
    if question_count > 0 and found_structured >= question_count * 0.5:
        pass  # 选择题已足够匹配，但仍需处理填空题/主观题

    # ========== 选择题：模式B — 纯字母序列 ==========
    if question_count > 0 and found_structured < question_count * 0.5:
        letter_sequence = []
        for line in lines:
            stripped = line.strip().upper()
            clean = re.sub(r'[\s.、,，;；()（）\[\]{}|/\\\-_=+*&^%$#@!~`\'"]', '', stripped)
            if clean and all(c in 'ABCD' for c in clean):
                letter_sequence.extend(list(clean))

        if len(letter_sequence) >= question_count * 0.6:
            for i, q_key in enumerate(ordered_keys):
                if i < len(letter_sequence):
                    result[q_key] = letter_sequence[i]
                else:
                    result[q_key] = result.get(q_key, "")

    # ========== 选择题：模式C — 位置排序兜底 ==========
    if question_count > 0 and words_result:
        # 检查是否还有选择题没识别到
        unmapped = [k for k in ordered_keys if not result.get(k)]
        if unmapped:
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

    # 确保所有选择题都有值
    for q_key in ordered_keys:
        if q_key not in result:
            result[q_key] = ""

    # ========== 填空题 & 主观题：按题号提取文本 ==========
    for q_key in text_keys:
        q_num = q_key.replace("q", "").replace("Q", "")
        found_text = ""
        # 尝试匹配 "题号. 文本内容" / "题号、 文本内容" / "第X题：文本内容"
        text_patterns = [
            rf"(?<!\d){q_num}\s*[.、,:：)\]]\s*(.+)",
            rf"第\s*{q_num}\s*题\s*[:：]?\s*(.+)",
            rf"\(\s*{q_num}\s*\)\s*(.+)",
        ]
        for pat in text_patterns:
            m = re.search(pat, ocr_text)
            if m:
                found_text = m.group(1).strip()
                # 截断到下一题号之前
                next_q_num = str(int(q_num) + 1) if q_num.isdigit() else ""
                if next_q_num:
                    cut_pat = rf"\s*{next_q_num}\s*[.、,:：)\]]"
                    cut_m = re.search(cut_pat, found_text)
                    if cut_m:
                        found_text = found_text[:cut_m.start()].strip()
                break
        result[q_key] = found_text

    return result


def auto_grade_answers(
    ocr_result: dict,
    answer_key: dict,
    total_score: float
) -> Tuple[float, List[Dict]]:
    """
    自动批改：仅比对选择题（objective）的 OCR 识别结果和标准答案。
    填空题和主观题不自动判分，返回 is_correct=None 供教师手动评分。

    Args:
        ocr_result:  学生答案 {q1: 'A', q2: 'B', q3: '手写文本...', ...}
        answer_key:  标准答案 {q1: 'A', q2: 'B', q3: {"type":"fill_blank",...}, ...}
        total_score: 试卷总分

    Returns:
        (ai_score, detail_list)
            ai_score:      选择题自动批阅分数
            detail_list:   每题批改详情
    """
    if not answer_key:
        return 0.0, []

    # 只统计选择题数量来均分客观题分数
    objective_keys = [k for k, v in answer_key.items() if isinstance(v, str)]
    objective_count = len(objective_keys)
    per_question_score = total_score / objective_count if objective_count > 0 else 0

    ai_score = 0.0
    detail_list = []

    for q_key, correct_ans in answer_key.items():
        student_ans = ocr_result.get(q_key, "")

        # 非选择题（填空题/主观题）：不自动判分
        if not isinstance(correct_ans, str):
            detail_list.append({
                "question": q_key,
                "student_answer": student_ans if student_ans else "（待识别）",
                "correct_answer": correct_ans.get("answer", "") if isinstance(correct_ans, dict) else "",
                "is_correct": None,
                "score": 0,
                "type": correct_ans.get("type", "subjective") if isinstance(correct_ans, dict) else "subjective",
                "max_score": correct_ans.get("score", 0) if isinstance(correct_ans, dict) else 0,
            })
            continue

        # 选择题：自动比对
        is_correct = False
        if isinstance(student_ans, str):
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
            "score": round(earned_score, 2),
            "type": "objective",
        })

    return round(ai_score, 2), detail_list
