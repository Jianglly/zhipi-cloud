"""
OCR 文本解析与自动批改 — 单元测试
智批云后端 - tests/test_ocr_service.py

覆盖 ocr_service.py 中的三个核心函数：
1. parse_ocr_text_to_answers — OCR文本→结构化答案（三种模式）
2. auto_grade_answers — 答案比对评分
3. 边界情况和异常处理
"""

import pytest
from fixtures.test_data import (
    ANSWER_KEY_OBJECTIVE_ONLY,
    ANSWER_KEY_MULTI_CHOICE,
    OCR_TEXT_STRUCTURED,
    OCR_TEXT_LETTER_SEQUENCE,
    OCR_TEXT_MULTI_CHOICE,
    OCR_TEXT_EMPTY,
    OCR_TEXT_GARBLED,
)

# 导入被测试函数
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.ocr_service import (
    parse_ocr_text_to_answers,
    auto_grade_answers,
)


# ============================================================
# parse_ocr_text_to_answers — OCR 文本解析测试
# ============================================================

class TestOCRTextParsing:
    """OCR 文本解析为结构化答案"""

    # ---------- 模式A：结构化格式 ----------

    def test_mode_a_standard_format(self):
        """模式A — 标准 '1. A' 格式"""
        result = parse_ocr_text_to_answers(OCR_TEXT_STRUCTURED, ANSWER_KEY_OBJECTIVE_ONLY)
        assert len(result) == 10
        assert result["q1"] == "A"
        assert result["q5"] == "A"
        assert result["q10"] == "B"

    def test_mode_a_chinese_punctuation(self):
        """模式A — 中文标点 '1、A' """
        text = "1、A\n2、B\n3、C\n4、D\n5、A"
        key = {f"q{i}": chr(64 + i) for i in range(1, 6)}  # q1=A, q2=B, ...
        result = parse_ocr_text_to_answers(text, key)
        assert result["q1"] == "A"
        assert result["q5"] == "A"

    def test_mode_a_colon_format(self):
        """模式A — 冒号格式 '1: A' """
        text = "1: A\n2: B\n3: C\n4: D"
        key = {f"q{i}": chr(64 + i) for i in range(1, 5)}
        result = parse_ocr_text_to_answers(text, key)
        assert result["q1"] == "A"
        assert result["q3"] == "C"

    def test_mode_a_no_space(self):
        """模式A — 无空格 '1A' 格式"""
        text = "1A\n2B\n3C\n4D"
        key = {f"q{i}": chr(64 + i) for i in range(1, 5)}
        result = parse_ocr_text_to_answers(text, key)
        assert result["q1"] == "A"
        assert result["q4"] == "D"

    def test_mode_a_bracket_format(self):
        """模式A — 括号格式 '(1) A' """
        text = "(1) A\n(2) B\n(3) C"
        key = {f"q{i}": chr(64 + i) for i in range(1, 4)}
        result = parse_ocr_text_to_answers(text, key)
        assert result["q1"] == "A"
        assert result["q3"] == "C"

    def test_mode_a_chinese_prefix(self):
        """模式A — 中文前缀 '第1题：A' """
        text = "第1题：A\n第2题：B\n第3题：C"
        key = {f"q{i}": chr(64 + i) for i in range(1, 4)}
        result = parse_ocr_text_to_answers(text, key)
        assert result["q1"] == "A"
        assert result["q2"] == "B"

    # ---------- 模式B：纯字母序列 ----------

    def test_mode_b_pure_letter_sequence(self):
        """模式B — 纯字母列表 'A B C D A B' """
        result = parse_ocr_text_to_answers(OCR_TEXT_LETTER_SEQUENCE, ANSWER_KEY_OBJECTIVE_ONLY)
        assert result["q1"] == "A"
        assert result["q2"] == "B"
        assert result["q10"] == "B"

    def test_mode_b_compact_letters(self):
        """模式B — 紧凑字母 'ABCDABCDAB' """
        text = "ABCDABCDAB"
        result = parse_ocr_text_to_answers(text, ANSWER_KEY_OBJECTIVE_ONLY)
        assert result["q1"] == "A"
        assert result["q2"] == "B"
        assert result["q4"] == "D"

    def test_mode_b_letters_with_punctuation(self):
        """模式B — 带标点 'A. D. D. C.' """
        text = "A. D. D. C. A. B. C. D. A. B."
        result = parse_ocr_text_to_answers(text, ANSWER_KEY_OBJECTIVE_ONLY)
        assert result["q1"] == "A"
        assert result["q4"] == "C"

    # ---------- 模式C：位置排序兜底 ----------

    def test_mode_c_position_sorting(self):
        """模式C — 利用词坐标排序（模拟OCR词级结果）"""
        words_result = [
            {"words": "A", "location": {"top": 100, "left": 200, "width": 30, "height": 40}},
            {"words": "B", "location": {"top": 150, "left": 200, "width": 30, "height": 40}},
            {"words": "C", "location": {"top": 200, "left": 200, "width": 30, "height": 40}},
            {"words": "D", "location": {"top": 250, "left": 200, "width": 30, "height": 40}},
        ]
        key = {"q1": "A", "q2": "B", "q3": "C", "q4": "D"}
        # 使用不会触发模式A的文本
        text = "ABCD"  # 无题号标记
        result = parse_ocr_text_to_answers(text, key, words_result)
        assert result["q1"] == "A"
        assert result["q4"] == "D"

    def test_mode_c_same_row_sorting(self):
        """模式C — 同一行多字母从左到右排序"""
        words_result = [
            {"words": "A", "location": {"top": 100, "left": 100, "width": 30, "height": 40}},
            {"words": "B", "location": {"top": 100, "left": 200, "width": 30, "height": 40}},
            {"words": "C", "location": {"top": 100, "left": 300, "width": 30, "height": 40}},
            {"words": "D", "location": {"top": 200, "left": 100, "width": 30, "height": 40}},
        ]
        key = {"q1": "A", "q2": "B", "q3": "C", "q4": "D"}
        text = "ABCD"
        result = parse_ocr_text_to_answers(text, key, words_result)
        # 第一行: A→B→C, 第二行: D
        assert result["q1"] == "A"
        assert result["q3"] == "C"
        assert result["q4"] == "D"

    # ---------- 多选题格式 ----------

    def test_multi_choice_parsing(self):
        """多选答案识别 'A,B' """
        result = parse_ocr_text_to_answers(OCR_TEXT_MULTI_CHOICE, ANSWER_KEY_MULTI_CHOICE)
        assert result["q1"] == "A,B"
        assert result["q4"] == "A,B,C,D"
        assert "q3" in result

    # ---------- 边界情况 ----------

    def test_empty_ocr_text(self):
        """空 OCR 文本"""
        result = parse_ocr_text_to_answers(OCR_TEXT_EMPTY, ANSWER_KEY_OBJECTIVE_ONLY)
        assert len(result) == 10
        # 所有答案应为空字符串
        assert all(v == "" for v in result.values())

    def test_empty_answer_key(self):
        """空标准答案"""
        result = parse_ocr_text_to_answers(OCR_TEXT_STRUCTURED, {})
        assert result == {}

    def test_garble_ocr_text(self):
        """乱码 OCR 文本"""
        result = parse_ocr_text_to_answers(OCR_TEXT_GARBLED, ANSWER_KEY_OBJECTIVE_ONLY)
        assert len(result) == 10
        # 乱码应导致所有答案为空
        assert all(v == "" for v in result.values())

    def test_partial_recognition(self):
        """部分题目未能识别（模式A 识别率 < 50% 触发模式B降级）"""
        text = "1. A\n2. B\n3. C"  # 只有 3/10 被识别
        result = parse_ocr_text_to_answers(text, ANSWER_KEY_OBJECTIVE_ONLY)
        # 模式A 识别率不足 50%，可能降级到模式B
        assert len(result) == 10

    def test_large_answer_key(self):
        """大量题目（50 题）"""
        key = {f"q{i}": "A" for i in range(1, 51)}
        text = "\n".join([f"{i}. A" for i in range(1, 51)])
        result = parse_ocr_text_to_answers(text, key)
        assert len(result) == 50
        assert result["q1"] == "A"
        assert result["q50"] == "A"

    def test_mixed_case_keys(self):
        """大小写混合题号 Q1/q1"""
        key = {"Q1": "A", "Q2": "B", "q3": "C"}
        text = "1. A\n2. B\n3. C"
        result = parse_ocr_text_to_answers(text, key)
        assert result.get("Q1") == "A" or result.get("Q1") == "A"


# ============================================================
# auto_grade_answers — 自动批改比对测试
# ============================================================

class TestAutoGrading:
    """自动批改比对"""

    def test_all_correct(self):
        """全部正确"""
        ocr_result = {"q1": "A", "q2": "B", "q3": "C", "q4": "D", "q5": "A"}
        answer_key = {"q1": "A", "q2": "B", "q3": "C", "q4": "D", "q5": "A"}
        ai_score, detail = auto_grade_answers(ocr_result, answer_key, total_score=100)
        assert ai_score == 100.0
        assert all(d["is_correct"] for d in detail)
        assert len(detail) == 5

    def test_all_wrong(self):
        """全部错误"""
        ocr_result = {"q1": "D", "q2": "C", "q3": "B", "q4": "A", "q5": "D"}
        answer_key = {"q1": "A", "q2": "B", "q3": "C", "q4": "D", "q5": "A"}
        ai_score, detail = auto_grade_answers(ocr_result, answer_key, total_score=100)
        assert ai_score == 0.0
        assert not any(d["is_correct"] for d in detail)

    def test_partial_correct(self):
        """部分正确"""
        ocr_result = {"q1": "A", "q2": "B", "q3": "X", "q4": "X", "q5": "A"}
        answer_key = {"q1": "A", "q2": "B", "q3": "C", "q4": "D", "q5": "A"}
        ai_score, detail = auto_grade_answers(ocr_result, answer_key, total_score=100)
        assert ai_score == 60.0  # 3/5 = 60

    def test_multi_choice_exact_match(self):
        """多选精确匹配"""
        ocr_result = {"q1": "A,B", "q2": "B,C,D"}
        answer_key = {"q1": "A,B", "q2": "B,C,D"}
        ai_score, detail = auto_grade_answers(ocr_result, answer_key, total_score=50)
        assert ai_score == 50.0

    def test_multi_choice_order_insensitive(self):
        """多选顺序无关"""
        ocr_result = {"q1": "B,A", "q2": "D,B,C"}
        answer_key = {"q1": "A,B", "q2": "B,C,D"}
        ai_score, detail = auto_grade_answers(ocr_result, answer_key, total_score=50)
        assert ai_score == 50.0

    def test_multi_choice_partial(self):
        """多选部分错（如果选项多）"""
        ocr_result = {"q1": "A", "q2": "B,C"}
        answer_key = {"q1": "A,B", "q2": "B,C"}
        ai_score, detail = auto_grade_answers(ocr_result, answer_key, total_score=50)
        assert ai_score == 25.0  # q1 错，q2 对

    def test_missing_student_answer(self):
        """学生未作答（空答案）"""
        ocr_result = {"q1": "", "q2": "B", "q3": ""}
        answer_key = {"q1": "A", "q2": "B", "q3": "C"}
        ai_score, detail = auto_grade_answers(ocr_result, answer_key, total_score=30)
        assert ai_score == 10.0  # 只有 q2 对了
        assert detail[0]["student_answer"] == "（未识别）"

    def test_case_insensitive(self):
        """大小写不敏感"""
        ocr_result = {"q1": "a", "q2": "b"}
        answer_key = {"q1": "A", "q2": "B"}
        ai_score, _ = auto_grade_answers(ocr_result, answer_key, total_score=20)
        assert ai_score == 20.0

    def test_whitespace_trimming(self):
        """空格处理"""
        ocr_result = {"q1": " A ", "q2": "B "}
        answer_key = {"q1": "A", "q2": "B"}
        ai_score, _ = auto_grade_answers(ocr_result, answer_key, total_score=20)
        assert ai_score == 20.0

    def test_empty_answer_key(self):
        """空标准答案"""
        ai_score, detail = auto_grade_answers({}, {}, 100)
        assert ai_score == 0.0
        assert detail == []

    def test_non_equal_question_count(self):
        """OCR 结果题目数多于标准答案（多识别了噪声）"""
        ocr_result = {"q1": "A", "q2": "B", "q3": "C", "q4": "D", "q5": "A", "q99": "X"}
        answer_key = {"q1": "A", "q2": "B", "q3": "C", "q4": "D", "q5": "A"}
        ai_score, detail = auto_grade_answers(ocr_result, answer_key, total_score=100)
        # q99 不在 answer_key 中，不受影响
        assert ai_score == 100.0

    def test_detail_structure(self):
        """验证批改详情结构完整性"""
        ocr_result = {"q1": "A", "q2": "B"}
        answer_key = {"q1": "A", "q2": "B"}
        _, detail = auto_grade_answers(ocr_result, answer_key, 20)
        assert len(detail) == 2
        for d in detail:
            assert "question" in d
            assert "student_answer" in d
            assert "correct_answer" in d
            assert "is_correct" in d
            assert "score" in d

    def test_uneven_score_distribution(self):
        """非整数均分（如 150/7 ≈ 21.43）"""
        ocr_result = {f"q{i}": "A" for i in range(1, 8)}
        answer_key = {f"q{i}": "A" for i in range(1, 7)}
        answer_key["q7"] = "B"  # 第7题错
        ai_score, detail = auto_grade_answers(ocr_result, answer_key, total_score=150)
        # 6/7 正确
        assert 120 < ai_score < 135  # 大约 128.57
        assert round(ai_score, 2) == round(150 * 6 / 7, 2)

    # ---------- 复合类型答案处理 ----------

    def test_dict_value_in_answer_key(self):
        """answer_key 中包含主观题 dict（应被跳过）"""
        ocr_result = {"q1": "A", "q2": "B"}
        answer_key = {
            "q1": "A",
            "q2": "B",
            "q5": {"type": "subjective", "answer": "...", "score": 20},
        }
        ai_score, detail = auto_grade_answers(ocr_result, answer_key, 60)
        # 3题总分60，但 q5 是 dict 不是 str，should be compared as str
        # auto_grade_answers 只处理 str-vs-str 情况，dict 值会导致 is_correct = False
        assert 0 <= ai_score <= 60
