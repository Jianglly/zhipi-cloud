"""
搜题服务测试套件 - DeepSeek LLM搜答案能力验证
智批云后端 - tests/test_question_search.py

测试覆盖：
- LLM搜题 prompt 构造
- JSON 响应解析
- 各种试卷文本格式
- 错误降级处理
- 三种题型混合识别
"""
import json
import pytest
from unittest.mock import patch, MagicMock
import requests as requests_lib

from services.question_search_service import (
    _build_search_prompt,
    _extract_json,
    _parse_search_result,
    call_llm_search,
    search_answers_from_image,
)


# ===================== Prompt 构建测试 =====================

class TestBuildSearchPrompt:
    """验证搜题 prompt 构造逻辑"""

    def test_build_prompt_chinese(self):
        """语文科目 prompt 应包含正确的科目名称"""
        system_prompt, user_prompt = _build_search_prompt("语文", "1. 选择题\nA. 选项1\nB. 选项2", 150)
        assert "语文教师" in system_prompt
        assert "150" in system_prompt
        assert "1. 选择题" in user_prompt

    def test_build_prompt_math(self):
        """数学科目 prompt"""
        system_prompt, user_prompt = _build_search_prompt("数学", "1. 计算下列各题", 100)
        assert "数学教师" in system_prompt
        assert "100" in system_prompt

    def test_build_prompt_english(self):
        """英语科目 prompt"""
        system_prompt, user_prompt = _build_search_prompt("英语", "1. Choose the best answer", 120)
        assert "英语教师" in system_prompt
        assert "120" in system_prompt

    def test_build_prompt_unknown_subject(self):
        """未知科目应直接使用传入值"""
        system_prompt, _ = _build_search_prompt("物理", "题目", 100)
        assert "物理" in system_prompt

    def test_build_prompt_contains_json_format(self):
        """prompt 应包含 JSON 输出格式说明"""
        system_prompt, _ = _build_search_prompt("语文", "题目", 100)
        assert '"questions"' in system_prompt
        assert '"num"' in system_prompt
        assert '"type"' in system_prompt
        assert '"answer"' in system_prompt

    def test_build_prompt_total_score_in_prompt(self):
        """总分应出现在 system_prompt 中"""
        system_prompt, _ = _build_search_prompt("语文", "题目", 150)
        assert "150" in system_prompt

    def test_ocr_text_in_user_prompt(self):
        """OCR文本应完整出现在 user_prompt 中"""
        ocr = "一、选择题（每题5分）\n1. 题目文本"
        _, user_prompt = _build_search_prompt("语文", ocr, 100)
        assert ocr in user_prompt


# ===================== JSON 提取测试 =====================

class TestExtractJson:
    """验证从 LLM 回复中提取 JSON 的能力"""

    def test_extract_json_with_markdown_wrapper(self):
        """标准 markdown 代码块包裹"""
        response = '```json\n{"questions": [{"num": 1, "type": "objective", "answer": "B"}]}\n```'
        result = _extract_json(response)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed["questions"]) == 1

    def test_extract_json_without_markdown(self):
        """裸 JSON"""
        response = '{"questions": [{"num": 1, "type": "objective", "answer": "A"}]}'
        result = _extract_json(response)
        assert result is not None
        parsed = json.loads(result)
        assert parsed["questions"][0]["answer"] == "A"

    def test_extract_json_with_preamble(self):
        """LLM回复前面有废话的情况"""
        response = '好的，这是分析结果：\n```json\n{"questions": [{"num": 1, "type": "fill_blank", "answer": "光合作用"}]}\n```'
        result = _extract_json(response)
        assert result is not None
        parsed = json.loads(result)
        assert parsed["questions"][0]["answer"] == "光合作用"

    def test_extract_json_empty_response(self):
        """空回复"""
        assert _extract_json("") is None

    def test_extract_json_gibberish(self):
        """乱码回复"""
        assert _extract_json("这是一段不是JSON的文本") is None

    def test_extract_json_partial(self):
        """不完整的JSON"""
        response = '{"questions": [{"num": 1, "type": "objective"'
        assert _extract_json(response) is None


# ===================== 搜索结果解析测试 =====================

class TestParseSearchResult:
    """验证 LLM JSON → answer_key 的转换"""

    def test_parse_objective_only(self):
        """纯客观题"""
        parsed = {
            "questions": [
                {"num": 1, "type": "objective", "question": "题目1", "answer": "B", "score": 5},
                {"num": 2, "type": "objective", "question": "题目2", "answer": "A", "score": 5},
                {"num": 3, "type": "objective", "question": "题目3", "answer": "C", "score": 5},
            ]
        }
        result = _parse_search_result(parsed, "语文")
        assert result == {"q1": "B", "q2": "A", "q3": "C"}

    def test_parse_subjective_only(self):
        """纯主观题"""
        parsed = {
            "questions": [
                {
                    "num": 1, "type": "subjective", "question": "作文",
                    "answer": "观点明确，论证充分，语言流畅",
                    "score": 60, "keywords": ["立意", "结构", "语言"]
                },
            ]
        }
        result = _parse_search_result(parsed, "语文")
        assert "q1" in result
        assert result["q1"]["type"] == "subjective"
        assert result["q1"]["answer"] == "观点明确，论证充分，语言流畅"
        assert result["q1"]["score"] == 60
        assert "立意" in result["q1"]["keywords"]

    def test_parse_mixed_types(self):
        """客观题 + 填空 + 主观题混合"""
        parsed = {
            "questions": [
                {"num": 1, "type": "objective", "answer": "A", "score": 3},
                {"num": 2, "type": "fill_blank", "answer": "42", "score": 2},
                {"num": 3, "type": "subjective", "answer": "解答过程", "score": 15, "keywords": ["步骤1", "步骤2"]},
            ]
        }
        result = _parse_search_result(parsed, "数学")
        assert result["q1"] == "A"
        assert result["q2"]["type"] == "fill_blank"
        assert result["q2"]["answer"] == "42"
        assert result["q3"]["type"] == "subjective"
        assert result["q3"]["score"] == 15

    def test_parse_multi_select(self):
        """多选题（逗号分隔）"""
        parsed = {
            "questions": [
                {"num": 1, "type": "objective", "answer": "A,D", "score": 5},
            ]
        }
        result = _parse_search_result(parsed, "英语")
        assert result["q1"] == "A,D"

    def test_parse_lowercase_answer(self):
        """小写答案应转大写"""
        parsed = {
            "questions": [
                {"num": 1, "type": "objective", "answer": "b", "score": 5},
            ]
        }
        result = _parse_search_result(parsed, "英语")
        assert result["q1"] == "B"

    def test_parse_empty_questions(self):
        """空题目列表"""
        assert _parse_search_result({}, "语文") == {}
        assert _parse_search_result({"questions": []}, "语文") == {}

    def test_parse_missing_questions_key(self):
        """缺少 questions 键"""
        assert _parse_search_result({"other": "data"}, "语文") == {}

    def test_parse_unknown_type(self):
        """未知题型降级为客观题"""
        parsed = {
            "questions": [
                {"num": 1, "type": "unknown_type", "answer": "X", "score": 5},
            ]
        }
        result = _parse_search_result(parsed, "语文")
        assert result["q1"] == "X"

    def test_parse_skip_invalid_items(self):
        """跳过非dict格式的题目"""
        parsed = {
            "questions": [
                {"num": 1, "type": "objective", "answer": "A"},
                "invalid_string_item",
                {"num": 2, "type": "objective", "answer": "B"},
            ]
        }
        result = _parse_search_result(parsed, "语文")
        assert len(result) == 2
        assert result["q1"] == "A"
        assert result["q2"] == "B"


# ===================== LLM 调用 Mock 测试 =====================

class TestCallLlmSearch:
    """Mock DeepSeek API 验证搜题流程"""

    @patch("services.question_search_service.requests.post")
    def test_call_llm_search_success(self, mock_post, monkeypatch):
        """正常搜题返回"""
        # 模拟 settings 中有 API Key
        monkeypatch.setattr("services.question_search_service.settings.LLM_API_KEY", "test_key")
        monkeypatch.setattr("services.question_search_service.settings.LLM_BASE_URL", "https://api.deepseek.com/v1")
        monkeypatch.setattr("services.question_search_service.settings.LLM_MODEL", "deepseek-chat")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '```json\n{"questions": [{"num": 1, "type": "objective", "answer": "B", "score": 5}, {"num": 2, "type": "objective", "answer": "C", "score": 5}]}\n```'
                }
            }]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = call_llm_search("1. 题目1\n2. 题目2", "语文", 100)
        assert result["q1"] == "B"
        assert result["q2"] == "C"
        assert len(result) == 2

    @patch("services.question_search_service.requests.post")
    def test_call_llm_search_no_api_key(self, mock_post, monkeypatch):
        """未配置 LLM API Key"""
        monkeypatch.setattr("services.question_search_service.settings.LLM_API_KEY", "your_llm_api_key_here")

        with pytest.raises(RuntimeError, match="LLM 未配置"):
            call_llm_search("题目", "语文", 100)

    @patch("services.question_search_service.requests.post")
    def test_call_llm_search_api_error(self, mock_post, monkeypatch):
        """LLM API 调用失败"""
        monkeypatch.setattr("services.question_search_service.settings.LLM_API_KEY", "test_key")
        monkeypatch.setattr("services.question_search_service.settings.LLM_BASE_URL", "https://api.deepseek.com/v1")
        monkeypatch.setattr("services.question_search_service.settings.LLM_MODEL", "deepseek-chat")

        mock_post.side_effect = requests_lib.ConnectionError("Connection refused")

        with pytest.raises(RuntimeError, match="调用 LLM API 失败"):
            call_llm_search("题目", "语文", 100)

    @patch("services.question_search_service.requests.post")
    def test_call_llm_search_empty_questions(self, mock_post, monkeypatch):
        """LLM未识别到题目"""
        monkeypatch.setattr("services.question_search_service.settings.LLM_API_KEY", "test_key")
        monkeypatch.setattr("services.question_search_service.settings.LLM_BASE_URL", "https://api.deepseek.com/v1")
        monkeypatch.setattr("services.question_search_service.settings.LLM_MODEL", "deepseek-chat")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '```json\n{"questions": []}\n```'
                }
            }]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        with pytest.raises(ValueError, match="未识别到任何题目"):
            call_llm_search("模糊文本", "语文", 100)

    @patch("services.question_search_service.requests.post")
    def test_call_llm_search_invalid_json_response(self, mock_post, monkeypatch):
        """LLM返回无法解析的内容"""
        monkeypatch.setattr("services.question_search_service.settings.LLM_API_KEY", "test_key")
        monkeypatch.setattr("services.question_search_service.settings.LLM_BASE_URL", "https://api.deepseek.com/v1")
        monkeypatch.setattr("services.question_search_service.settings.LLM_MODEL", "deepseek-chat")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "这道题我不会做。"
                }
            }]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        with pytest.raises(ValueError, match="无法解析为 JSON"):
            call_llm_search("题目", "语文", 100)

    @patch("services.question_search_service.requests.post")
    def test_call_llm_search_no_choices(self, mock_post, monkeypatch):
        """LLM响应缺少 choices 字段"""
        monkeypatch.setattr("services.question_search_service.settings.LLM_API_KEY", "test_key")
        monkeypatch.setattr("services.question_search_service.settings.LLM_BASE_URL", "https://api.deepseek.com/v1")
        monkeypatch.setattr("services.question_search_service.settings.LLM_MODEL", "deepseek-chat")

        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Internal server error"}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError):
            call_llm_search("题目", "语文", 100)


# ===================== OCR+LLM 完整链路测试 =====================

class TestSearchAnswersFromImage:
    """集成测试: OCR → LLM 搜题"""

    @patch("controllers.ocr_controller.call_baidu_ocr")
    @patch("services.question_search_service.call_llm_search")
    def test_search_answers_from_image_success(self, mock_llm, mock_ocr):
        """正常流程：OCR成功 + LLM搜题成功"""
        mock_ocr.return_value = ("1. 选择题 A. 选项 B. 选项\n2. 填空题 ___", [])
        mock_llm.return_value = {"q1": "A", "q2": {"type": "fill_blank", "answer": "42", "score": 3}}

        result = search_answers_from_image("/fake/path.jpg", "数学", 100)
        assert result["q1"] == "A"
        assert result["q2"]["type"] == "fill_blank"
        assert len(result) == 2

    @patch("controllers.ocr_controller.call_baidu_ocr")
    def test_search_answers_ocr_empty(self, mock_ocr):
        """OCR识别为空"""
        mock_ocr.return_value = ("", [])

        with pytest.raises(RuntimeError, match="OCR识别为空"):
            search_answers_from_image("/fake/path.jpg", "语文", 100)

    @patch("controllers.ocr_controller.call_baidu_ocr")
    @patch("services.question_search_service.call_llm_search")
    def test_search_answers_with_existing_key(self, mock_llm, mock_ocr):
        """已有部分答案，增量补充"""
        mock_ocr.return_value = ("1. 题目1\n2. 题目2\n3. 题目3", [])
        mock_llm.return_value = {"q1": "A", "q2": "B", "q3": "C"}

        existing = {"q1": "A"}  # 第1题已有答案
        result = search_answers_from_image("/fake/path.jpg", "语文", 100, answer_key=existing)

        # 验证 call_llm_search 被调用时 ocr_text 包含了 existing 提示
        call_args = mock_llm.call_args[0]
        assert 'q1' in call_args[0]  # ocr_text 中应包含已有答案信息


# ===================== 真实试卷场景模拟测试 =====================

class TestRealWorldScenarios:
    """模拟真实试卷场景"""

    @patch("services.question_search_service.requests.post")
    def test_chinese_paper_search(self, mock_post, monkeypatch):
        """语文试卷：客观题+主观题+作文"""
        monkeypatch.setattr("services.question_search_service.settings.LLM_API_KEY", "test_key")
        monkeypatch.setattr("services.question_search_service.settings.LLM_BASE_URL", "https://api.deepseek.com/v1")
        monkeypatch.setattr("services.question_search_service.settings.LLM_MODEL", "deepseek-chat")

        llm_reply = json.dumps({
            "questions": [
                {"num": 1, "type": "objective", "answer": "B", "score": 3},
                {"num": 2, "type": "objective", "answer": "A", "score": 3},
                {"num": 3, "type": "objective", "answer": "C", "score": 3},
                {"num": 4, "type": "subjective", "answer": "表达了作者思乡之情", "score": 10, "keywords": ["思乡", "孤独", "月色"]},
                {"num": 5, "type": "subjective", "answer": "立意深刻，结构完整", "score": 60, "keywords": ["立意", "论据", "文采"]},
            ]
        }, ensure_ascii=False)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": f"```json\n{llm_reply}\n```"}}]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        ocr_text = """一、选择题
        1. 下列词语中加点字读音完全正确的一项是 A. 踌躇 B. 踌躇 C. 踌躇 D. 踌躇
        2. 登鹳雀楼的作者 A. 李白 B. 杜甫 C. 王之涣 D. 白居易
        3. 乃不知有汉下一句 A. 无论魏晋 B. 自云先世 C. 便舍船 D. 不足为外人道也
        二、阅读理解
        4. 请分析文中主人公的情感变化
        三、作文
        5. 以"我的理想"为题写一篇作文"""

        result = call_llm_search(ocr_text, "语文", 100)

        assert result["q1"] == "B"
        assert result["q4"]["type"] == "subjective"
        assert result["q4"]["score"] == 10
        assert "思乡" in result["q4"]["keywords"]
        assert result["q5"]["type"] == "subjective"
        assert result["q5"]["score"] == 60

    @patch("services.question_search_service.requests.post")
    def test_math_paper_search(self, mock_post, monkeypatch):
        """数学试卷：选择+填空+解答"""
        monkeypatch.setattr("services.question_search_service.settings.LLM_API_KEY", "test_key")
        monkeypatch.setattr("services.question_search_service.settings.LLM_BASE_URL", "https://api.deepseek.com/v1")
        monkeypatch.setattr("services.question_search_service.settings.LLM_MODEL", "deepseek-chat")

        llm_reply = json.dumps({
            "questions": [
                {"num": 1, "type": "objective", "answer": "C", "score": 5},
                {"num": 2, "type": "fill_blank", "answer": "x=3", "score": 5},
                {"num": 3, "type": "subjective", "answer": "证明：设f(x)...", "score": 15, "keywords": ["求导", "单调性", "极值点"]},
            ]
        }, ensure_ascii=False)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": f"```json\n{llm_reply}\n```"}}]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = call_llm_search("1. 计算题\n2. 填空题\n3. 解答题", "数学", 100)

        assert result["q1"] == "C"
        assert result["q2"]["type"] == "fill_blank"
        assert result["q2"]["answer"] == "x=3"
        assert result["q3"]["type"] == "subjective"

    @patch("services.question_search_service.requests.post")
    def test_english_paper_search(self, mock_post, monkeypatch):
        """英语试卷：单选+完形+翻译"""
        monkeypatch.setattr("services.question_search_service.settings.LLM_API_KEY", "test_key")
        monkeypatch.setattr("services.question_search_service.settings.LLM_BASE_URL", "https://api.deepseek.com/v1")
        monkeypatch.setattr("services.question_search_service.settings.LLM_MODEL", "deepseek-chat")

        llm_reply = json.dumps({
            "questions": [
                {"num": 1, "type": "objective", "answer": "B", "score": 2},
                {"num": 2, "type": "objective", "answer": "D", "score": 2},
                {"num": 3, "type": "fill_blank", "answer": "arrived", "score": 2},
                {"num": 4, "type": "subjective", "answer": "The teacher asked us to finish homework on time.", "score": 5, "keywords": ["teacher", "homework", "on time"]},
            ]
        }, ensure_ascii=False)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": f"```json\n{llm_reply}\n```"}}]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = call_llm_search("I. Multiple Choice\n1. A B C D\nII. Cloze\nIII. Translation", "英语", 100)

        assert result["q1"] == "B"
        assert result["q2"] == "D"
        assert result["q3"]["type"] == "fill_blank"
        assert result["q4"]["type"] == "subjective"
