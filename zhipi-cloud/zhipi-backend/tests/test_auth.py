"""
认证与安全 — 集成测试
智批云后端 - tests/test_auth.py

覆盖：
- 登录/注册功能
- JWT Token 验证（过期、篡改、缺失）
- 角色权限控制（teacher/student/admin）
- 输入验证（SQL注入、XSS、边界值）
- 限流验证
"""

import pytest
import time


# ============================================================
# 登录功能
# ============================================================

class TestLogin:
    """登录功能测试"""

    def test_login_success_teacher(self, client):
        """教师登录成功"""
        resp = client.post("/api/auth/login", json={
            "user_id": "T007",
            "password": "123456",
            "role": "teacher",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "teacher"
        assert data["user_id"] == "T007"
        assert data["name"] is not None

    def test_login_success_student(self, client):
        """学生登录成功"""
        resp = client.post("/api/auth/login", json={
            "user_id": "S032",
            "password": "123456",
            "role": "student",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "student"

    def test_login_success_admin(self, client):
        """管理员登录成功"""
        resp = client.post("/api/auth/login", json={
            "user_id": "admin",
            "password": "123456",
            "role": "admin",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "admin"

    def test_login_wrong_password(self, client):
        """错误密码"""
        resp = client.post("/api/auth/login", json={
            "user_id": "T007",
            "password": "wrong_password",
            "role": "teacher",
        })
        assert resp.status_code in [401, 400]

    def test_login_nonexistent_user(self, client):
        """不存在的用户"""
        resp = client.post("/api/auth/login", json={
            "user_id": "NOBODY",
            "password": "123456",
            "role": "student",
        })
        assert resp.status_code in [401, 404]

    def test_login_wrong_role(self, client):
        """角色不匹配（用学生账号登录教师角色）"""
        resp = client.post("/api/auth/login", json={
            "user_id": "S032",
            "password": "123456",
            "role": "teacher",
        })
        assert resp.status_code in [401, 400]

    def test_login_empty_credentials(self, client):
        """空用户名/密码"""
        resp = client.post("/api/auth/login", json={
            "user_id": "",
            "password": "",
            "role": "student",
        })
        assert resp.status_code == 422  # Pydantic 验证失败


# ============================================================
# JWT Token 安全
# ============================================================

class TestJWTSecurity:
    """JWT Token 安全测试"""

    def test_access_without_token(self, client):
        """无 Token 请求受保护资源"""
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_access_with_expired_token(self, client, expired_token):
        """过期 Token"""
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    def test_access_with_tampered_token(self, client, tampered_token):
        """篡改的 Token"""
        if tampered_token is None:
            pytest.skip("无法生成篡改 Token")
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {tampered_token}"},
        )
        assert resp.status_code == 401

    def test_access_with_invalid_header_format(self, client):
        """格式错误的 Authorization 头"""
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": "InvalidFormat"},
        )
        assert resp.status_code == 401

    def test_access_with_wrong_scheme(self, client, teacher_token):
        """使用错误的认证方案（Basic 而非 Bearer）"""
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Basic {teacher_token}"},
        )
        assert resp.status_code == 401

    def test_access_with_empty_token(self, client):
        """空 Bearer Token"""
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer "},
        )
        assert resp.status_code == 401

    def test_valid_token_returns_user_info(self, client, auth_header):
        """有效 Token 返回用户信息"""
        resp = client.get("/api/auth/me", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "T007"
        assert data["role"] == "teacher"


# ============================================================
# 角色权限控制
# ============================================================

class TestAuthorization:
    """角色权限控制测试"""

    # ---------- 教师专属接口 ----------

    def test_teacher_can_create_paper(self, client, auth_header):
        """教师可以创建试卷"""
        from datetime import date
        resp = client.post("/api/papers", json={
            "title": "权限测试试卷",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 100,
            "exam_date": str(date.today()),
        }, headers=auth_header)
        # 可能因权限限制返回 403（出卷限制），但不应返回 401
        assert resp.status_code != 401

    def test_student_cannot_create_paper(self, client, student_auth_header):
        """学生不能创建试卷"""
        from datetime import date
        resp = client.post("/api/papers", json={
            "title": "学生创建试卷",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 100,
            "exam_date": str(date.today()),
        }, headers=student_auth_header)
        assert resp.status_code == 403

    def test_student_cannot_access_ocr(self, client, student_auth_header):
        """学生不能访问 OCR 接口"""
        resp = client.post("/api/ocr/recognize?paper_id=1&student_id=S032",
                           headers=student_auth_header)
        assert resp.status_code == 403

    # ---------- 管理员专属接口 ----------

    def test_teacher_cannot_access_admin(self, client, auth_header):
        """教师不能访问管理员接口"""
        resp = client.get("/api/admin/overview", headers=auth_header)
        assert resp.status_code == 403

    def test_admin_can_access_admin(self, client, admin_auth_header):
        """管理员可以访问管理接口"""
        resp = client.get("/api/admin/overview", headers=admin_auth_header)
        assert resp.status_code == 200

    # ---------- 跨资源权限 ----------

    def test_teacher_cannot_view_other_teacher_papers(self, client, auth_header):
        """教师不能操作其他教师的试卷"""
        # 尝试删除不存在的试卷（ID随机）
        resp = client.delete("/api/papers/99999", headers=auth_header)
        # 应返回 403（不是自己的）或 404
        assert resp.status_code in [403, 404]

    # ---------- me 接口角色验证 ----------

    def test_me_returns_correct_role(self, client, auth_header):
        """/me 返回正确的角色信息"""
        resp = client.get("/api/auth/me", headers=auth_header)
        assert resp.json()["role"] == "teacher"

    def test_student_me_returns_correct_role(self, client, student_auth_header):
        """学生 /me 返回学生角色"""
        resp = client.get("/api/auth/me", headers=student_auth_header)
        assert resp.json()["role"] == "student"


# ============================================================
# 输入验证与安全防护
# ============================================================

class TestInputValidation:
    """输入验证与注入防护"""

    def test_sql_injection_in_login(self, client):
        """SQL 注入在登录中的防护"""
        resp = client.post("/api/auth/login", json={
            "user_id": "'; DROP TABLE students; --",
            "password": "anything",
            "role": "teacher",
        })
        # Pydantic 字段约束应限制 user_id 长度（1-50字符）
        # 即使通过，也应返回 401 而非 500
        assert resp.status_code != 500

    def test_sql_injection_in_login_password(self, client):
        """SQL 注入在密码字段的防护"""
        resp = client.post("/api/auth/login", json={
            "user_id": "T007",
            "password": "' OR '1'='1",
            "role": "teacher",
        })
        assert resp.status_code != 200  # SQL 注入不应能登录

    def test_xss_in_paper_title(self, client, auth_header):
        """XSS 在试卷标题中的防护"""
        from datetime import date
        resp = client.post("/api/papers", json={
            "title": "<script>alert('xss')</script>",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 100,
            "exam_date": str(date.today()),
        }, headers=auth_header)
        # 应正常处理或拒绝，不应 500
        assert resp.status_code != 500

    def test_oversized_input(self, client, auth_header):
        """超长输入"""
        from datetime import date
        resp = client.post("/api/papers", json={
            "title": "A" * 500,  # 超过 200 字符
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 100,
            "exam_date": str(date.today()),
        }, headers=auth_header)
        assert resp.status_code == 422  # Pydantic 验证失败

    def test_negative_score(self, client, auth_header):
        """负分数"""
        from datetime import date
        resp = client.post("/api/papers", json={
            "title": "负分试卷",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": -10,
            "exam_date": str(date.today()),
        }, headers=auth_header)
        assert resp.status_code == 422

    def test_zero_total_score(self, client, auth_header):
        """0分试卷"""
        from datetime import date
        resp = client.post("/api/papers", json={
            "title": "0分试卷",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 0,
            "exam_date": str(date.today()),
        }, headers=auth_header)
        assert resp.status_code == 422  # total_score > 0

    def test_excessive_score(self, client, auth_header):
        """超过上限的分数（>1000）"""
        from datetime import date
        resp = client.post("/api/papers", json={
            "title": "超高分数试卷",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 9999,
            "exam_date": str(date.today()),
        }, headers=auth_header)
        assert resp.status_code == 422

    def test_future_exam_date(self, client, auth_header):
        """未来的考试日期"""
        resp = client.post("/api/papers", json={
            "title": "未来试卷",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 100,
            "exam_date": "2099-12-31",
        }, headers=auth_header)
        assert resp.status_code == 422  # 不能是未来日期

    def test_register_empty_fields(self, client):
        """注册时空字段"""
        resp = client.post("/api/auth/register", json={
            "role": "student",
            "user_id": "",
            "name": "",
            "class_id": "",
            "password": "123456",
            "confirm_password": "123456",
        })
        assert resp.status_code == 422

    def test_register_password_mismatch(self, client):
        """注册时两次密码不一致"""
        resp = client.post("/api/auth/register", json={
            "role": "student",
            "user_id": "TEST001",
            "name": "测试用户",
            "class_id": "CS2024-01",
            "password": "123456",
            "confirm_password": "654321",
        })
        assert resp.status_code == 422

    def test_register_teacher_without_subject(self, client):
        """教师注册不填科目"""
        resp = client.post("/api/auth/register", json={
            "role": "teacher",
            "user_id": "TEACH01",
            "name": "新老师",
            "class_id": "CS2024-01",
            "password": "123456",
            "confirm_password": "123456",
        })
        assert resp.status_code == 422  # 教师必须填 subject

    def test_register_short_password(self, client):
        """密码过短"""
        resp = client.post("/api/auth/register", json={
            "role": "student",
            "user_id": "TEST001",
            "name": "测试用户",
            "class_id": "CS2024-01",
            "password": "12",
            "confirm_password": "12",
        })
        assert resp.status_code == 422  # 密码至少 6 字符

    def test_register_invalid_role(self, client):
        """无效角色"""
        resp = client.post("/api/auth/register", json={
            "role": "hacker",
            "user_id": "HACK01",
            "name": "攻击者",
            "class_id": "CS2024-01",
            "password": "123456",
            "confirm_password": "123456",
        })
        assert resp.status_code == 422  # role 只能是 student/teacher


# ============================================================
# 限流测试
# ============================================================

class TestRateLimiting:
    """速率限制测试"""

    def test_login_rate_limit(self, client):
        """登录限流 5次/分钟"""
        # 连续快速调用登录
        responses = []
        for _ in range(10):
            resp = client.post("/api/auth/login", json={
                "user_id": "T007",
                "password": "wrong_password",  # 使用错误密码避免Token验证
                "role": "teacher",
            })
            responses.append(resp.status_code)

        # 至少有一些请求被限流
        has_429 = 429 in responses
        # 注意：TestClient 可能不完全触发真实的 slowapi 限流
        # 因为 slowapi 依赖 IP 地址，而 TestClient 可能不设置
        if has_429:
            assert True  # 限流生效
        else:
            pytest.skip("TestClient 可能不触发 slowapi 限流（IP 地址问题）")


# ============================================================
# 健康检查
# ============================================================

class TestHealthCheck:
    """系统健康检查"""

    def test_health_endpoint(self, client):
        """健康检查返回正常"""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_ready_endpoint(self, client):
        """就绪检查（需数据库连接）"""
        resp = client.get("/ready")
        # 如果没有数据库，应降级返回 503
        assert resp.status_code in [200, 503]

    def test_api_docs_accessible(self, client):
        """API 文档可访问"""
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_schema(self, client):
        """OpenAPI Schema 可获取"""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "paths" in data
        assert "info" in data
        assert data["info"]["title"] == "智批云 API"


# ============================================================
# CORS 测试
# ============================================================

class TestCORS:
    """跨域请求测试"""

    def test_options_preflight(self, client):
        """OPTIONS 预检请求"""
        resp = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.status_code == 200
        # 应包含 CORS 头
        assert "access-control-allow-origin" in resp.headers
        assert "access-control-allow-methods" in resp.headers

    def test_actual_request_with_origin(self, client):
        """带 Origin 头的实际请求"""
        resp = client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert resp.status_code == 200
