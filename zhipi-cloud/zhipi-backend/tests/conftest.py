"""
测试基础设施 — Fixtures、Mock 服务、测试数据库
智批云后端 - tests/conftest.py

提供的 Fixtures:
- app: FastAPI TestClient 应用实例
- client: httpx TestClient（同步）
- async_client: httpx AsyncClient（异步）
- teacher_token / student_token / admin_token: 各角色 JWT Token
- db_session: 测试数据库会话（隔离模式）
- mock_baidu_ocr: Mock 百度 OCR API
- mock_llm: Mock DeepSeek LLM API
- sample_paper_id: 预设测试试卷
"""

import os
import sys
import json
import pytest
from datetime import date
from typing import Generator, Optional
from unittest.mock import patch, MagicMock

# ===================== 路径配置 =====================
# 将后端根目录加入 Python 路径（让 import services / controllers 可用）
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

# 将 tests/ 目录加入 Python 路径（让 import fixtures.test_data 可用）
tests_dir = os.path.dirname(__file__)
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

# 设置测试环境标志
os.environ["TESTING"] = "true"


@pytest.fixture(scope="session")
def backend_env():
    """设置测试环境变量（session 级别，只执行一次）"""
    # 记录将被设置的键，便于精确恢复（不 clear 全部 env，避免 Windows PATH 超长报错）
    test_keys = [
        "TESTING", "DB_HOST", "DB_PORT", "DB_NAME",
        "BAIDU_OCR_API_KEY", "BAIDU_OCR_SECRET_KEY",
        "LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "DEBUG",
    ]
    old_values = {k: os.environ.get(k) for k in test_keys}

    os.environ["TESTING"] = "true"
    os.environ.setdefault("DB_HOST", "localhost")
    os.environ.setdefault("DB_PORT", "3307")
    os.environ.setdefault("DB_NAME", "zhipi_cloud")
    os.environ.setdefault("BAIDU_OCR_API_KEY", "test_baidu_key")
    os.environ.setdefault("BAIDU_OCR_SECRET_KEY", "test_baidu_secret")
    os.environ.setdefault("LLM_API_KEY", "test_llm_key")
    os.environ.setdefault("LLM_BASE_URL", "https://api.deepseek.com/v1")
    os.environ.setdefault("LLM_MODEL", "deepseek-chat")
    os.environ.setdefault("DEBUG", "true")
    yield
    # 精确恢复 — 只还原我们改过的键，不清空全局 env
    for k, v in old_values.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


# ===================== 应用 Fixtures =====================

@pytest.fixture(scope="session")
def db_available(backend_env):
    """检测 MySQL 是否可连接 — 不可用时自动跳过集成测试"""
    try:
        import pymysql
        conn = pymysql.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", "3307")),
            user=os.environ.get("DB_USER", "root"),
            password=os.environ.get("DB_PASSWORD", ""),
            database=os.environ.get("DB_NAME", "zhipi_cloud"),
            connect_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def app(backend_env, db_available):
    """
    创建 FastAPI 应用实例（module 级别复用）。
    使用真实的 main.py 创建 app，但挂载了测试覆盖的依赖。
    无数据库时自动跳过依赖 app 的测试。
    """
    if not db_available:
        pytest.skip("MySQL 不可用 — 跳过需要数据库的集成测试")
    from main import app as fastapi_app
    return fastapi_app


@pytest.fixture
def client(app):
    """
    FastAPI TestClient — 同步 HTTP 客户端。
    TestClient 不经过真实网络，直接从 ASGI 应用层调用。
    """
    from fastapi.testclient import TestClient
    with TestClient(app, base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def async_client(app):
    """
    ASGI 异步客户端 — 用于异步并发测试。
    """
    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


# ===================== 认证 Fixtures =====================

def _get_auth_token(client, login_data: dict) -> Optional[str]:
    """通用登录辅助函数"""
    resp = client.post("/api/auth/login", json=login_data)
    if resp.status_code == 200:
        return resp.json().get("access_token")
    return None


@pytest.fixture
def teacher_token(client) -> Optional[str]:
    """教师 JWT Token — 使用种子数据 T007"""
    return _get_auth_token(client, {
        "user_id": "T007",
        "password": "123456",
        "role": "teacher",
    })


@pytest.fixture
def student_token(client) -> Optional[str]:
    """学生 JWT Token — 使用种子数据 S032"""
    return _get_auth_token(client, {
        "user_id": "S032",
        "password": "123456",
        "role": "student",
    })


@pytest.fixture
def admin_token(client) -> Optional[str]:
    """管理员 JWT Token — 使用种子数据 admin"""
    return _get_auth_token(client, {
        "user_id": "admin",
        "password": "123456",
        "role": "admin",
    })


@pytest.fixture
def auth_header(teacher_token):
    """带教师 Token 的认证请求头"""
    return {"Authorization": f"Bearer {teacher_token}"}


@pytest.fixture
def student_auth_header(student_token):
    """带学生 Token 的认证请求头"""
    return {"Authorization": f"Bearer {student_token}"}


@pytest.fixture
def admin_auth_header(admin_token):
    """带管理员 Token 的认证请求头"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def expired_token():
    """过期 Token — 用于测试令牌过期处理"""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJUMDA3IiwibmFtZSI6IuW8oOiAgeW4iCIsInJvbGUiOiJ0ZWFjaGVyIiwiY2xhc3NfaWQiOiJDUzIwMjQtMDEiLCJleHAiOjE1MDAwMDAwMDB9.mock_expired_signature"


@pytest.fixture
def tampered_token(teacher_token):
    """篡改后的 Token — 用于测试签名验证"""
    if teacher_token:
        parts = teacher_token.split(".")
        if len(parts) == 3:
            # 修改 payload 但签名不变
            return parts[0] + "." + "dGFtcGVyZWRfcGF5bG9hZA==" + "." + parts[2]
    return None


# ===================== 外部 API Mock Fixtures =====================

@pytest.fixture
def mock_baidu_ocr(monkeypatch):
    """
    Mock 百度 OCR API — 拦截所有百度 API 的 HTTP 调用。

    使用方法：
        mock_baidu_ocr.return_value = (full_text, words_result)

    或设置自定义响应：
        mock_baidu_ocr.side_effect = custom_function
    """
    from services.ocr_service import parse_ocr_text_to_answers  # noqa: F401

    def mock_call_baidu_ocr(image_path: str):
        """默认返回结构化格式的 OCR 结果"""
        words_result = [
            {"words": "1. A", "location": {"top": 100, "left": 200, "width": 30, "height": 40}},
            {"words": "2. B", "location": {"top": 150, "left": 200, "width": 30, "height": 40}},
            {"words": "3. C", "location": {"top": 200, "left": 200, "width": 30, "height": 40}},
            {"words": "4. D", "location": {"top": 250, "left": 200, "width": 30, "height": 40}},
            {"words": "5. A", "location": {"top": 300, "left": 200, "width": 30, "height": 40}},
            {"words": "6. B", "location": {"top": 350, "left": 200, "width": 30, "height": 40}},
            {"words": "7. C", "location": {"top": 400, "left": 200, "width": 30, "height": 40}},
            {"words": "8. D", "location": {"top": 450, "left": 200, "width": 30, "height": 40}},
            {"words": "9. A", "location": {"top": 500, "left": 200, "width": 30, "height": 40}},
            {"words": "10. B", "location": {"top": 550, "left": 200, "width": 30, "height": 40}},
        ]
        full_text = "\n".join([item["words"] for item in words_result])
        return full_text, words_result

    # Patch 百度 OCR 的两个调用函数
    monkeypatch.setattr(
        "controllers.ocr_controller.call_baidu_ocr",
        mock_call_baidu_ocr,
    )
    monkeypatch.setattr(
        "controllers.ocr_controller.call_baidu_ocr_general",
        mock_call_baidu_ocr,
    )
    # Mock get_baidu_access_token 避免真实 API 调用
    monkeypatch.setattr(
        "controllers.ocr_controller.get_baidu_access_token",
        lambda: "mock_baidu_token",
    )

    return mock_call_baidu_ocr


@pytest.fixture
def mock_llm(monkeypatch):
    """Mock LLM API — 返回预设的评分结果"""
    def mock_call_llm_grade(subjective_items, student_answers):
        """返回模拟的 LLM 批改结果"""
        results = []
        for item in subjective_items:
            results.append({
                "question": item["q_key"],
                "score": round(item["score"] * 0.85, 2),  # 模拟85%得分率
                "max_score": item["score"],
                "feedback": "整体回答正确，个别细节可以补充完善。",
            })
        return results

    monkeypatch.setattr(
        "services.llm_service.call_llm_grade",
        mock_call_llm_grade,
    )
    return mock_call_llm_grade


@pytest.fixture
def mock_llm_error(monkeypatch):
    """Mock LLM API 错误 — 模拟 API 调用失败"""
    def mock_call_llm_error(subjective_items, student_answers):
        raise RuntimeError("调用 LLM API 失败: Connection timeout")

    monkeypatch.setattr(
        "services.llm_service.call_llm_grade",
        mock_call_llm_error,
    )
    return mock_call_llm_error


# ===================== 测试数据 Fixtures =====================

@pytest.fixture
def sample_paper_id(client, auth_header):
    """创建一个测试试卷并返回 paper_id"""
    resp = client.post(
        "/api/papers",
        json={
            "title": "测试试卷-API测试",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 100,
            "exam_date": str(date.today()),
            "answer_key": {
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
            },
            "description": "自动化测试创建",
        },
        headers=auth_header,
    )
    if resp.status_code == 200:
        return resp.json().get("paper_id")
    return None


@pytest.fixture
def sample_mixed_paper_id(client, auth_header):
    """创建一个混合题型测试试卷"""
    resp = client.post(
        "/api/papers",
        json={
            "title": "测试试卷-混合题型",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 100,
            "exam_date": str(date.today()),
            "answer_key": {
                "q1": "A",
                "q2": "B",
                "q3": "C",
                "q4": "D",
                "q5": {
                    "type": "subjective",
                    "answer": "数据库完整性约束包括实体完整性、参照完整性和用户定义完整性。",
                    "score": 20,
                    "keywords": ["实体完整性", "参照完整性", "用户定义完整性"],
                },
                "q6": {
                    "type": "subjective",
                    "answer": "ACID：原子性、一致性、隔离性、持久性。",
                    "score": 20,
                    "keywords": ["原子性", "一致性", "隔离性", "持久性"],
                },
            },
            "description": "含主观题测试",
        },
        headers=auth_header,
    )
    if resp.status_code == 200:
        return resp.json().get("paper_id")
    return None


@pytest.fixture
def dummy_image():
    """生成一个 1x1 像素的 JPEG 测试图片"""
    from PIL import Image
    import io
    img = Image.new("RGB", (1, 1), color="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


# ===================== 性能测试辅助 =====================

@pytest.fixture
def timer():
    """计时器 — 用于测量操作耗时"""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def __enter__(self):
            self.start_time = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.end_time = time.perf_counter()

        @property
        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return 0

    return Timer
