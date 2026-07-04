"""
测试数据常量与辅助函数
智批云后端 - tests/fixtures/test_data.py
"""

from datetime import date

# ===================== 演示账号（与种子数据一致）=====================
DEMO_TEACHER = {
    "user_id": "T007",
    "password": "123456",
    "name": "张老师",
    "role": "teacher",
    "class_id": "CS2024-01",
    "subject": "数据库系统",
}

DEMO_STUDENT = {
    "user_id": "S032",
    "password": "123456",
    "name": "李同学",
    "role": "student",
    "class_id": "CS2024-01",
}

DEMO_ADMIN = {
    "user_id": "admin",
    "password": "123456",
    "name": "系统管理员",
    "role": "admin",
    "class_id": "",
}

# ===================== 试卷标准答案样例 =====================
# 纯客观题（选择题/填空题）
ANSWER_KEY_OBJECTIVE_ONLY = {
    "q1": "A",
    "q2": "B",
    "q3": "C",
    "q4": "D",
    "q5": "A",
    "q6": "B",
    "q7": "C",
    "q8": "D",
    "q9": "A",
    "q10": "B",
}

# 混合题型（客观+主观）
ANSWER_KEY_MIXED = {
    "q1": "A",
    "q2": "B",
    "q3": "C",
    "q4": "D",
    "q5": {
        "type": "subjective",
        "answer": "数据库的完整性约束包括：实体完整性、参照完整性和用户定义完整性。实体完整性要求主键不能为空；参照完整性要求外键必须匹配主表中的主键值。",
        "score": 20,
        "keywords": ["实体完整性", "参照完整性", "用户定义完整性", "主键", "外键"],
    },
    "q6": {
        "type": "subjective",
        "answer": "事务具有ACID特性：原子性(Atomicity)、一致性(Consistency)、隔离性(Isolation)、持久性(Durability)。",
        "score": 15,
        "keywords": ["原子性", "一致性", "隔离性", "持久性", "ACID"],
    },
}

# 多选题答案
ANSWER_KEY_MULTI_CHOICE = {
    "q1": "A,B",
    "q2": "B,C,D",
    "q3": "A,C",
    "q4": "A,B,C,D",
    "q5": "C,D",
}

# ===================== OCR 模拟文本 =====================
# 模式A：结构化格式
OCR_TEXT_STRUCTURED = """1. A
2. B
3. C
4. D
5. A
6. B
7. C
8. D
9. A
10. B"""

# 模式B：纯字母序列
OCR_TEXT_LETTER_SEQUENCE = "A B C D A B C D A B"

# 模式A 多选格式
OCR_TEXT_MULTI_CHOICE = """1. A,B
2. B,C,D
3. A,C
4. A,B,C,D
5. C,D"""

# 带主观题的 OCR 文本
OCR_TEXT_WITH_SUBJECTIVE = """1. A
2. B
3. C
4. D

5. 数据库的完整性约束主要包括实体完整性、参照完整性和用户定义完整性。实体完整性要求每个表必须定义主键且主键值不能为空；参照完整性要求外键值必须匹配参照表的主键值或为空值。

6. 事务具有ACID特性：原子性保证事务要么全部执行要么全部不执行，一致性保证事务执行前后数据库保持一致状态，隔离性保证并发事务互不干扰，持久性保证提交的事务结果永久保存。"""

# OCR 识别为空
OCR_TEXT_EMPTY = ""

# OCR 识别乱码/噪声
OCR_TEXT_GARBLED = """%%%???#$@!
---NOISE LINE---
()()()()()"""

# ===================== 百度 OCR API Mock 响应 =====================
BAIDU_OCR_HANDWRITING_RESPONSE = {
    "words_result": [
        {"words": "1. A"},
        {"words": "2. B"},
        {"words": "3. C"},
        {"words": "4. D"},
        {"words": "5. A"},
        {"words": "6. B"},
        {"words": "7. C"},
        {"words": "8. D"},
        {"words": "9. A"},
        {"words": "10. B"},
    ],
    "words_result_num": 10,
    "log_id": 123456789,
}

BAIDU_OCR_GENERAL_RESPONSE = {
    "words_result": [
        {"words": "1. A"},
        {"words": "2. B"},
        {"words": "3. C"},
        {"words": "4. D"},
    ],
    "words_result_num": 4,
    "log_id": 987654321,
}

BAIDU_OCR_TOKEN_RESPONSE = {
    "access_token": "mock_access_token_for_testing_12345",
    "expires_in": 2592000,
    "session_key": "mock_session",
}

BAIDU_OCR_EMPTY_RESPONSE = {
    "words_result": [],
    "words_result_num": 0,
    "log_id": 111111,
}

BAIDU_OCR_ERROR_RESPONSE = {
    "error_code": 216201,
    "error_msg": "image format error",
}

# ===================== LLM (DeepSeek) Mock 响应 =====================
LLM_GRADING_RESPONSE = {
    "id": "chatcmpl-mock-001",
    "object": "chat.completion",
    "created": 1718000000,
    "model": "deepseek-chat",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": """```json
[
  {
    "question": "q5",
    "score": 18,
    "max_score": 20,
    "feedback": "完整性约束描述基本正确，但遗漏了用户定义完整性的示例说明。"
  },
  {
    "question": "q6",
    "score": 14,
    "max_score": 15,
    "feedback": "ACID特性描述完整准确，对持久性的解释可以更具体一些。"
  }
]
```"""
            },
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 500,
        "completion_tokens": 150,
        "total_tokens": 650,
    },
}

LLM_ERROR_RESPONSE = {
    "error": {
        "message": "Insufficient balance",
        "type": "insufficient_quota",
        "code": "insufficient_quota",
    }
}

# ===================== 试卷创建数据 =====================
PAPER_CREATE_DATA = {
    "title": "2024-2025学年第一学期数据库系统期末考试",
    "subject": "数据库系统",
    "class_id": "CS2024-01",
    "total_score": 100,
    "exam_date": str(date.today()),
    "answer_key": ANSWER_KEY_OBJECTIVE_ONLY,
    "description": "本试卷共10道选择题",
}

PAPER_MIXED_DATA = {
    "title": "数据库系统期中测试（含主观题）",
    "subject": "数据库系统",
    "class_id": "CS2024-01",
    "total_score": 100,
    "exam_date": str(date.today()),
    "answer_key": ANSWER_KEY_MIXED,
    "description": "含4道选择题和2道主观题",
}

# ===================== 边界值数据 =====================
EDGE_CASES = {
    "empty_paper_title": "",
    "extremely_long_title": "A" * 201,  # 超过 200 字符限制
    "negative_score": -10,
    "zero_score": 0,
    "excessive_score": 1001,  # 超过 1000 上限
    "future_date": "2099-12-31",
    "sql_injection": "'; DROP TABLE papers; --",
    "xss_payload": "<script>alert('xss')</script>",
    "unicode_payload": "试卷\x00null",
}
