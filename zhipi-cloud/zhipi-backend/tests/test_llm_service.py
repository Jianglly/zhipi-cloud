"""
LLM 大题批改服务 — 单元测试
智批云后端 - tests/test_llm_service.py

覆盖 llm_service.py 中的核心函数：
1. split_ocr_by_questions — 按题号切分 OCR 文本
2. _build_grading_prompt — 构建 LLM Prompt
3. _extract_json — 从 LLM 回复中提取 JSON
4. grade_mixed_answers — 混合批改入口（使用 mock）
"""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.llm_service import (
    split_ocr_by_questions,
    _build_grading_prompt,
    _extract_json,
    _extract_q_num,
)

from fixtures.test_data import (
    OCR_TEXT_WITH_SUBJECTIVE,
    ANSWER_KEY_MIXED,
)

# ============================================================
# _extract_q_num — 题号提取
# ============================================================

def test_extract_q_num_normal():
    assert _extract_q_num("q5") == 5
    assert _extract_q_num("q12") == 12
    assert _extract_q_num("Q100") == 100
    assert _extract_q_num("q1") == 1


def test_extract_q_num_no_digit():
    assert _extract_q_num("q") == 9999
    assert _extract_q_num("question") == 9999


# ============================================================
# split_ocr_by_questions — 题号切分
# ============================================================

class TestOCRTextSplitting:
    """OCR 全文按题号切分"""

    def test_split_basic(self):
        """基本切分"""
        text = "1. This is answer one.\n2. This is answer two.\n3. This is answer three."
        result = split_ocr_by_questions(text, [1, 2, 3])
        assert 1 in result
        assert 2 in result
        assert 3 in result
        assert "This is answer one" in result[1]
        assert "This is answer two" in result[2]
        assert "This is answer three" in result[3]

    def test_split_chinese_punctuation(self):
        """中文标点切分"""
        text = "1、第一题答案\n2、第二题答案\n3、第三题答案"
        result = split_ocr_by_questions(text, [1, 2, 3])
        assert "第一题答案" in result[1]
        assert "第二题答案" in result[2]

    def test_split_bracket_format(self):
        """括号格式切分"""
        text = "(1) 答案A\n(2) 答案B\n(3) 答案C"
        result = split_ocr_by_questions(text, [1, 2, 3])
        assert "答案A" in result[1]
        assert "答案C" in result[3]

    def test_split_respects_number_set(self):
        """只切分指定的题号"""
        text = "1. A\n2. B\n3. C\n4. D\n5. E"
        result = split_ocr_by_questions(text, [1, 3, 5])
        assert 1 in result
        assert 3 in result
        assert 5 in result
        # 2, 4 不在指定集合中，但作为边界可能出现
        assert len(result) >= 2  # 至少找到 1, 3, 5

    def test_split_multiline_answers(self):
        """多行答案切分"""
        text = "1. Line one of answer.\n   Line two of answer.\n2. Second question answer.\n   More lines.\n3. Third answer."
        result = split_ocr_by_questions(text, [1, 2, 3])
        assert "Line one" in result[1]
        assert "Line two" in result[1]  # 多行属于同一题
        assert "Second question" in result[2]

    def test_split_empty_text(self):
        """空文本"""
        result = split_ocr_by_questions("", [1, 2, 3])
        assert result == {}

    def test_split_no_markers(self):
        """无题号标记"""
        text = "This is just plain text without any question numbers."
        result = split_ocr_by_questions(text, [1, 2])
        # fallback: 整个文本作为所有题的答案
        assert 1 in result
        assert result[1] == text.strip()

    def test_split_with_real_subjective_data(self):
        """使用真实的混合题型 OCR 文本"""
        result = split_ocr_by_questions(OCR_TEXT_WITH_SUBJECTIVE, [5, 6])
        assert 5 in result
        assert 6 in result
        # 第5题应包含完整性约束内容
        assert "实体完整性" in result[5]
        # 第6题应包含ACID内容
        assert "ACID" in result[6] or "原子性" in result[6]


# ============================================================
# _build_grading_prompt — Prompt 构建
# ============================================================

class TestPromptBuilding:
    """LLM Prompt 构建"""

    def test_build_basic_prompt(self):
        """基本 Prompt 结构"""
        items = [{
            "q_key": "q5",
            "q_num": 5,
            "answer": "参考答案",
            "score": 20,
            "keywords": ["关键词1", "关键词2"],
        }]
        student_answers = {5: "学生答案"}

        system_prompt, user_prompt = _build_grading_prompt(items, student_answers)

        # System prompt 应包含评分规则
        assert "教师阅卷助手" in system_prompt or "主观题" in user_prompt
        assert "JSON" in system_prompt

        # User prompt 应包含题目信息
        assert "q5" in user_prompt
        assert "20" in user_prompt or "20" in user_prompt.replace(" ", "")
        assert "参考答案" in user_prompt
        assert "学生答案" in user_prompt
        assert "关键词1" in user_prompt
        assert "关键词2" in user_prompt

    def test_prompt_with_multiple_items(self):
        """多题 Prompt"""
        items = [
            {"q_key": "q5", "q_num": 5, "answer": "答5", "score": 15, "keywords": []},
            {"q_key": "q6", "q_num": 6, "answer": "答6", "score": 20, "keywords": ["K1"]},
        ]
        student_answers = {5: "生5", 6: "生6"}
        _, user_prompt = _build_grading_prompt(items, student_answers)
        assert "q5" in user_prompt
        assert "q6" in user_prompt
        assert "15" in user_prompt
        assert "20" in user_prompt

    def test_prompt_with_missing_answer(self):
        """学生未作答"""
        items = [{"q_key": "q7", "q_num": 7, "answer": "参考", "score": 10, "keywords": []}]
        student_answers = {}  # 没有第7题答案
        _, user_prompt = _build_grading_prompt(items, student_answers)
        assert "未识别到答案" in user_prompt


# ============================================================
# _extract_json — JSON 提取
# ============================================================

class TestJSONExtraction:
    """从 LLM 回复中提取 JSON"""

    def test_extract_markdown_wrapped(self):
        """```json...``` 包裹"""
        text = '这是一段文字\n```json\n[{"question": "q5", "score": 15}]\n```\n更多文字'
        result = _extract_json(text)
        assert result is not None
        parsed = json.loads(result)
        assert parsed[0]["question"] == "q5"

    def test_extract_bare_json(self):
        """裸 JSON 数组"""
        text = '[{"question": "q5", "score": 15, "max_score": 20}]'
        result = _extract_json(text)
        assert result is not None
        parsed = json.loads(result)
        assert parsed[0]["score"] == 15

    def test_extract_multiple_items(self):
        """多项 JSON"""
        text = '[{"question": "q5", "score": 15}, {"question": "q6", "score": 18}]'
        result = _extract_json(text)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_extract_no_json(self):
        """无 JSON 文本"""
        assert _extract_json("纯文本回复，不包含JSON") is None

    def test_extract_empty_string(self):
        """空字符串"""
        assert _extract_json("") is None

    def test_extract_with_newlines(self):
        """带换行的 JSON"""
        text = """```json
[
  {"question": "q5", "score": 18, "max_score": 20, "feedback": "不错"},
  {"question": "q6", "score": 14, "max_score": 15, "feedback": "可以补充"}
]
```"""
        result = _extract_json(text)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["feedback"] == "不错"


# ============================================================
# grade_mixed_answers — 混合批改（使用 mock LLM）
# ============================================================

class TestMixedGrading:
    """混合批改入口函数"""

    def test_grade_mixed_objective_only(self, monkeypatch, mock_llm):
        """纯客观题批改"""
        from services.llm_service import grade_mixed_answers

        answer_key = {"q1": "A", "q2": "B", "q3": "C", "q4": "D"}
        ocr_text = "1. A\n2. B\n3. C\n4. D"
        ai_score, detail = grade_mixed_answers(ocr_text, answer_key, total_score=100)

        assert ai_score == 100.0
        assert len(detail) == 4
        assert all(d["type"] == "objective" for d in detail)
        assert all(d["is_correct"] for d in detail)

    def test_grade_mixed_with_subjective(self, monkeypatch, mock_llm):
        """混合题型（客观+主观）"""
        from services.llm_service import grade_mixed_answers

        ai_score, detail = grade_mixed_answers(
            OCR_TEXT_WITH_SUBJECTIVE,
            ANSWER_KEY_MIXED,
            total_score=100,
        )

        # 4道客观题全对(60分) + 2道主观题(约30分) = 约90分
        assert 70 <= ai_score <= 100
        # 应有4客观+2主观
        assert len(detail) == 6
        obj_items = [d for d in detail if d.get("type") == "objective"]
        sub_items = [d for d in detail if d.get("type") == "subjective"]
        assert len(obj_items) == 4
        assert len(sub_items) == 2

    def test_grade_mixed_llm_errors_preserved(self, mock_llm):
        """使用 mock LLM 时的分数合理性"""
        from services.llm_service import grade_mixed_answers

        ai_score, detail = grade_mixed_answers(
            OCR_TEXT_WITH_SUBJECTIVE,
            ANSWER_KEY_MIXED,
            total_score=100,
        )

        for d in detail:
            if d.get("type") == "subjective":
                assert "feedback" in d
                # 分数不能超过最大分
                assert d["score"] <= d["max_score"]
                # 分数不能为负
                assert d["score"] >= 0

    def test_grade_mixed_with_precomputed_ocr_result(self, mock_llm):
        """使用预计算的OCR结果跳过重新解析"""
        from services.llm_service import grade_mixed_answers

        # 预计算OCR结果（客观题错误）
        precomputed = {"q1": "B", "q2": "B", "q3": "C", "q4": "D"}
        ai_score, detail = grade_mixed_answers(
            OCR_TEXT_WITH_SUBJECTIVE,
            ANSWER_KEY_MIXED,
            total_score=100,
            ocr_result=precomputed,
        )
        # q1应判断为错误
        q1_detail = next((d for d in detail if d["question"] == "q1"), None)
        assert q1_detail is not None
        assert q1_detail["is_correct"] is False

    def test_grade_mixed_scores_within_bounds(self, mock_llm):
        """分数边界检查"""
        from services.llm_service import grade_mixed_answers

        # 学生全错
        wrong_text = "1. Z\n2. Z\n3. Z\n4. Z\n5. wrong\n6. wrong"
        ai_score, detail = grade_mixed_answers(
            wrong_text, ANSWER_KEY_MIXED, total_score=100
        )
        # 客观题全错，主观题由LLM评
        assert ai_score >= 0
        assert ai_score <= 100

    def test_grade_mixed_empty_answer_key(self, mock_llm):
        """空标准答案"""
        from services.llm_service import grade_mixed_answers
        ai_score, detail = grade_mixed_answers("some text", {}, 100)
        assert ai_score == 0.0
        assert detail == []
