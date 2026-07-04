"""
性能测试与负载验证
智批云后端 - tests/test_performance.py

覆盖：
- API 响应时间 SLA 验证（核心接口 < 200ms）
- 并发请求测试
- 数据库查询性能
- 文件上传性能
"""

import os
import sys
import time
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ============================================================
# SLA 响应时间验证
# ============================================================

class TestResponseTimeSLA:
    """
    核心接口响应时间 SLA 验证。
    目标：95th percentile < 200ms（Mock 模式下应远低于此）
    实际网络环境可能更慢，以下为宽松的基准阈值。
    """

    # 不同类别的 SLA 阈值（毫秒）
    SLA_HEALTH = 50       # 健康检查
    SLA_QUERY = 200       # 查询类
    SLA_WRITE = 300       # 写入类
    SLA_OCR = 500         # OCR 链路（无外部 API）
    SLA_UPLOAD = 300      # 文件上传

    def _measure(self, client, method, url, **kwargs):
        """测量单次请求耗时"""
        start = time.perf_counter()
        if method == "GET":
            resp = client.get(url, **kwargs)
        elif method == "POST":
            resp = client.post(url, **kwargs)
        elif method == "PUT":
            resp = client.put(url, **kwargs)
        elif method == "DELETE":
            resp = client.delete(url, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return resp, elapsed_ms

    def _measure_n(self, client, method, url, n=5, **kwargs):
        """多次测量，返回 (avg_ms, p95_ms, max_ms)"""
        times = []
        for _ in range(n):
            _, elapsed = self._measure(client, method, url, **kwargs)
            times.append(elapsed)
        times.sort()
        avg = sum(times) / len(times)
        p95 = times[int(len(times) * 0.95)] if len(times) > 1 else times[-1]
        return avg, p95, max(times)

    def test_health_check_performance(self, client):
        """GET /health 响应时间"""
        avg, p95, max_t = self._measure_n(client, "GET", "/health", n=10)
        assert max_t < self.SLA_HEALTH, f"health 最慢 {max_t:.1f}ms > {self.SLA_HEALTH}ms"
        print(f"  /health: avg={avg:.1f}ms, p95={p95:.1f}ms, max={max_t:.1f}ms")

    def test_auth_me_performance(self, client, auth_header):
        """GET /api/auth/me 响应时间"""
        avg, p95, max_t = self._measure_n(
            client, "GET", "/api/auth/me", n=5,
            headers=auth_header,
        )
        assert max_t < self.SLA_QUERY, f"auth/me 最慢 {max_t:.1f}ms > {self.SLA_QUERY}ms"
        print(f"  /api/auth/me: avg={avg:.1f}ms, p95={p95:.1f}ms, max={max_t:.1f}ms")

    def test_paper_list_performance(self, client, auth_header):
        """GET /api/papers 响应时间"""
        avg, p95, max_t = self._measure_n(
            client, "GET", "/api/papers", n=5,
            headers=auth_header,
        )
        assert max_t < self.SLA_QUERY, f"papers 最慢 {max_t:.1f}ms > {self.SLA_QUERY}ms"
        print(f"  /api/papers: avg={avg:.1f}ms, p95={p95:.1f}ms, max={max_t:.1f}ms")

    def test_stats_performance(self, client, student_auth_header):
        """GET /api/stats/student/scores 响应时间"""
        avg, p95, max_t = self._measure_n(
            client, "GET", "/api/stats/student/scores", n=5,
            headers=student_auth_header,
        )
        assert max_t < self.SLA_QUERY, f"stats 最慢 {max_t:.1f}ms > {self.SLA_QUERY}ms"
        print(f"  /api/stats/student/scores: avg={avg:.1f}ms, p95={p95:.1f}ms, max={max_t:.1f}ms")

    def test_admin_overview_performance(self, client, admin_auth_header):
        """GET /api/admin/overview 响应时间"""
        avg, p95, max_t = self._measure_n(
            client, "GET", "/api/admin/overview", n=3,
            headers=admin_auth_header,
        )
        assert max_t < self.SLA_QUERY, f"admin/overview 最慢 {max_t:.1f}ms > {self.SLA_QUERY}ms"
        print(f"  /api/admin/overview: avg={avg:.1f}ms, p95={p95:.1f}ms, max={max_t:.1f}ms")

    def test_login_performance(self, client):
        """POST /api/auth/login 响应时间"""
        avg, p95, max_t = self._measure_n(
            client, "POST", "/api/auth/login", n=3,
            json={"user_id": "T007", "password": "123456", "role": "teacher"},
        )
        assert max_t < self.SLA_WRITE, f"login 最慢 {max_t:.1f}ms > {self.SLA_WRITE}ms"
        print(f"  /api/auth/login: avg={avg:.1f}ms, p95={p95:.1f}ms, max={max_t:.1f}ms")

    def test_ocr_upload_performance(self, client, auth_header):
        """POST /api/ocr/upload-image 响应时间"""
        from datetime import date
        from PIL import Image
        import io

        # 创建测试用试卷
        paper_resp = client.post("/api/papers", json={
            "title": "上传性能测试",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 50,
            "exam_date": str(date.today()),
        }, headers=auth_header)
        if paper_resp.status_code != 200:
            pytest.skip("创建试卷失败")
        paper_id = paper_resp.json()["paper_id"]

        # 生成测试图片
        img = Image.new("RGB", (800, 600), "white")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        # 多次上传测试
        times = []
        for i in range(3):
            start = time.perf_counter()
            client.post(
                "/api/ocr/upload-image",
                data={"paper_id": paper_id, "student_id": f"S032"},
                files={"file": (f"perf_{i}.jpg", buf, "image/jpeg")},
                headers=auth_header,
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            buf.seek(0)  # 重置文件指针

        avg = sum(times) / len(times)
        max_t = max(times)
        assert max_t < self.SLA_UPLOAD, f"upload 最慢 {max_t:.1f}ms > {self.SLA_UPLOAD}ms"
        print(f"  /api/ocr/upload-image: avg={avg:.1f}ms, max={max_t:.1f}ms")


# ============================================================
# 并发测试
# ============================================================

class TestConcurrency:
    """并发请求测试"""

    def test_health_concurrent(self, client):
        """健康检查并发 50 请求"""
        n_requests = 50

        def do_health():
            return client.get("/health").status_code

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(do_health) for _ in range(n_requests)]
            results = [f.result() for f in as_completed(futures)]

        success_count = sum(1 for r in results if r == 200)
        success_rate = success_count / n_requests
        assert success_rate >= 0.95, f"并发成功率 {success_rate:.1%} < 95%"
        print(f"  /health 并发 {n_requests}: 成功率 {success_rate:.1%}")

    def test_auth_concurrent(self, client):
        """登录并发 20 请求"""
        n_requests = 20

        def do_login(i):
            return client.post("/api/auth/login", json={
                "user_id": "T007",
                "password": "123456",
                "role": "teacher",
            }).status_code

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(do_login, i) for i in range(n_requests)]
            results = [f.result() for f in as_completed(futures)]

        success_count = sum(1 for r in results if r == 200)
        success_rate = success_count / n_requests
        assert success_rate >= 0.9, f"并发登录成功率 {success_rate:.1%} < 90%"
        print(f"  /auth/login 并发 {n_requests}: 成功率 {success_rate:.1%}")

    def test_list_papers_concurrent(self, client, auth_header):
        """试卷列表并发 30 请求"""
        n_requests = 30

        def do_list():
            return client.get("/api/papers", headers=auth_header).status_code

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(do_list) for _ in range(n_requests)]
            results = [f.result() for f in as_completed(futures)]

        success_count = sum(1 for r in results if r == 200)
        success_rate = success_count / n_requests
        assert success_rate >= 0.95, f"并发列表成功率 {success_rate:.1%} < 95%"
        print(f"  /api/papers 并发 {n_requests}: 成功率 {success_rate:.1%}")


# ============================================================
# 负载测试（轻量级，避免真实环境压力）
# ============================================================

class TestLoadBaseline:
    """基准负载测试"""

    def test_baseline_throughput(self, client):
        """健康检查吞吐量基准"""
        n_requests = 100
        start = time.perf_counter()

        for _ in range(n_requests):
            client.get("/health")

        elapsed = time.perf_counter() - start
        rps = n_requests / elapsed
        print(f"  /health 吞吐量: {rps:.1f} req/s ({n_requests} 请求, {elapsed:.2f}s)")
        # 基准：TestClient 模式下应 > 100 req/s
        assert rps > 50, f"吞吐量 {rps:.1f} req/s 低于 50 req/s 基准"

    def test_sequence_add_then_delete(self, client, auth_header):
        """顺序 CRUD 测试（验证数据库连接池稳定性）"""
        from datetime import date

        # 创建10个试卷
        paper_ids = []
        for i in range(10):
            resp = client.post("/api/papers", json={
                "title": f"负载测试试卷_{i}",
                "subject": "数据库系统",
                "class_id": "CS2024-01",
                "total_score": 50,
                "exam_date": str(date.today()),
            }, headers=auth_header)
            if resp.status_code == 200:
                paper_ids.append(resp.json()["paper_id"])

        # 验证可以查看
        for pid in paper_ids:
            resp = client.get(f"/api/papers/{pid}", headers=auth_header)
            assert resp.status_code == 200

        # 清理（教师只能删除自己的）
        for pid in paper_ids:
            client.delete(f"/api/papers/{pid}", headers=auth_header)

        print(f"  顺序 CRUD: 创建+读取+删除 {len(paper_ids)} 个试卷")


# ============================================================
# 内存/资源泄漏检查（基础）
# ============================================================

class TestResourceStability:
    """资源稳定性检查"""

    def test_long_running_sequence(self, client, auth_header):
        """长时间运行序列（模拟持续使用）"""
        from datetime import date
        import gc

        error_count = 0
        for i in range(50):
            try:
                # 健康检查 + 登录 + 查询
                client.get("/health")
                resp = client.post("/api/auth/login", json={
                    "user_id": "T007", "password": "123456", "role": "teacher",
                })
                token = resp.json().get("access_token", "")
                client.get(
                    "/api/papers",
                    headers={"Authorization": f"Bearer {token}"},
                )
            except Exception:
                error_count += 1
                if error_count > 5:
                    break

            if i % 20 == 0:
                gc.collect()  # 提示 GC

        assert error_count == 0, f"50次循环中出现 {error_count} 个错误"
        print(f"  稳定性: 50次循环 0 错误")
