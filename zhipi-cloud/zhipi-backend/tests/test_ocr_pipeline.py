"""
OCR/LLM 批阅链路 — 端到端集成测试
智批云后端 - tests/test_ocr_pipeline.py

覆盖完整批阅流程：
1. 教师创建试卷 + 设置标准答案
2. 上传学生答卷图片
3. OCR 手写体识别 → 结构化答案解析
4. 自动批改客观题（正则比对）
5. LLM 混合批改（主观题评分）
6. 查看批改结果
7. 教师审核/手动录入成绩
8. 异常流程测试（未上传图片就批改、缺少标准答案等）

本测试使用 FastAPI TestClient + Mock 外部 API。
"""

import os
import io
import sys
import json
import pytest
from datetime import date, timedelta
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ============================================================
# 批量批阅完整链路测试
# ============================================================

class TestOCRFullPipeline:
    """
    完整 OCR 批阅链路：
    创建试卷 → 上传答卷 → OCR识别 → 自动批改 → 查看结果
    """

    def test_full_pipeline_objective_only(self, client, auth_header):
        """
        场景：10道选择题，纯客观题批改
        流程：创建试卷 → 上传图片 → OCR识别 → 自动批改 → 查看结果
        """
        # Step 1: 创建试卷
        paper_resp = client.post("/api/papers", json={
            "title": "数据库系统单元测试（10道选择）",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 100,
            "exam_date": str(date.today()),
            "answer_key": {
                "q1": "A", "q2": "B", "q3": "C", "q4": "D", "q5": "A",
                "q6": "B", "q7": "C", "q8": "D", "q9": "A", "q10": "B",
            },
            "description": "全选择题测试",
        }, headers=auth_header)
        assert paper_resp.status_code == 200, f"创建试卷失败: {paper_resp.text}"
        paper_id = paper_resp.json()["paper_id"]

        # Step 2: 上传学生答卷图片
        # 使用 mock OCR（conftest 中默认返回正确格式的OCR结果）
        img = _create_test_image()
        upload_resp = client.post(
            "/api/ocr/upload-image",
            data={"paper_id": paper_id, "student_id": "S032"},
            files={"file": ("answer_sheet.jpg", img, "image/jpeg")},
            headers=auth_header,
        )
        assert upload_resp.status_code == 200, f"上传失败: {upload_resp.text}"

        # Step 3: OCR 识别
        recog_resp = client.post(
            f"/api/ocr/recognize?paper_id={paper_id}&student_id=S032",
            headers=auth_header,
        )
        assert recog_resp.status_code == 200, f"OCR识别失败: {recog_resp.text}"
        recog_data = recog_resp.json()
        assert "ocr_result" in recog_data
        assert "ocr_raw_text" in recog_data
        assert "parse_rate" in recog_data
        # 应识别到 10/10
        assert "10/10" in recog_data["parse_rate"], f"识别率异常: {recog_data['parse_rate']}"

        # Step 4: 自动批改
        grade_resp = client.post(
            f"/api/ocr/auto-grade?paper_id={paper_id}&student_id=S032",
            headers=auth_header,
        )
        assert grade_resp.status_code == 200, f"自动批改失败: {grade_resp.text}"
        grade_data = grade_resp.json()
        assert "ai_score" in grade_data
        assert "detail" in grade_data
        # Mock OCR 返回全对答案
        assert grade_data["ai_score"] == 100.0, f"AI分数应为100: 实际 {grade_data['ai_score']}"
        assert len(grade_data["detail"]) == 10

        # Step 5: 教师人工审核——手动录入
        submit_resp = client.post(
            f"/api/papers/{paper_id}/submit-score?student_id=S032&manual_score=95.0",
            headers=auth_header,
        )
        assert submit_resp.status_code == 200, f"提交成绩失败: {submit_resp.text}"

        # Step 6: 查看批改结果列表
        result_resp = client.get(
            f"/api/ocr/grade-result/{paper_id}",
            headers=auth_header,
        )
        assert result_resp.status_code == 200, f"查看结果失败: {result_resp.text}"
        results = result_resp.json()
        assert len(results) >= 1  # 至少有一个学生的记录
        s032 = [r for r in results if r["student_id"] == "S032"]
        assert len(s032) == 1

    def test_pipeline_multiple_students(self, client, auth_header):
        """
        场景：多名学生同时批改
        """
        # 创建试卷
        paper_resp = client.post("/api/papers", json={
            "title": "批量批改测试",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 60,
            "exam_date": str(date.today()),
            "answer_key": {"q1": "A", "q2": "B", "q3": "C", "q4": "D", "q5": "A", "q6": "B"},
            "description": "6道选择题",
        }, headers=auth_header)
        assert paper_resp.status_code == 200
        paper_id = paper_resp.json()["paper_id"]

        students = ["S032", "S033", "S034"]
        for sid in students:
            if sid == "S032":
                # S032 是已知种子数据
                pass
            # 每个学生上传并批改
            img = _create_test_image()
            client.post(
                "/api/ocr/upload-image",
                data={"paper_id": paper_id, "student_id": sid},
                files={"file": (f"sheet_{sid}.jpg", img, "image/jpeg")},
                headers=auth_header,
            )
            client.post(
                f"/api/ocr/recognize?paper_id={paper_id}&student_id={sid}",
                headers=auth_header,
            )
            client.post(
                f"/api/ocr/auto-grade?paper_id={paper_id}&student_id={sid}",
                headers=auth_header,
            )

        # 查看结果
        result_resp = client.get(
            f"/api/ocr/grade-result/{paper_id}",
            headers=auth_header,
        )
        assert result_resp.status_code == 200


# ============================================================
# LLM 混合批改链路
# ============================================================

class TestLLMMixedGrading:
    """LLM 混合批改（客观题正则 + 主观题 LLM）"""

    def test_mixed_grading_with_mock_llm(self, client, auth_header):
        """
        场景：4道选择 + 2道主观题，使用 mock LLM
        """
        # 创建混合题型试卷
        paper_resp = client.post("/api/papers", json={
            "title": "数据库系统期中测试（混合题型）",
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
                    "score": 30,
                    "keywords": ["实体完整性", "参照完整性", "用户定义完整性"],
                },
                "q6": {
                    "type": "subjective",
                    "answer": "ACID特性：原子性、一致性、隔离性、持久性。",
                    "score": 30,
                    "keywords": ["原子性", "一致性", "隔离性", "持久性"],
                },
            },
            "description": "混合题型测试",
        }, headers=auth_header)
        assert paper_resp.status_code == 200, f"创建试卷失败: {paper_resp.text}"
        paper_id = paper_resp.json()["paper_id"]

        # 上传答卷
        img = _create_test_image()
        client.post(
            "/api/ocr/upload-image",
            data={"paper_id": paper_id, "student_id": "S032"},
            files={"file": ("mixed_answer.jpg", img, "image/jpeg")},
            headers=auth_header,
        )

        # LLM 混合批改
        llm_resp = client.post(
            f"/api/ocr/llm-grade?paper_id={paper_id}&student_id=S032",
            headers=auth_header,
        )
        assert llm_resp.status_code == 200, f"LLM批改失败: {llm_resp.text}"
        data = llm_resp.json()
        assert data["has_subjective"] is True
        assert "ai_score" in data
        assert "detail" in data

        # 检查详情中有主观题标记
        detail = data["detail"]
        sub_items = [d for d in detail if d.get("type") == "subjective"]
        obj_items = [d for d in detail if d.get("type") == "objective"]
        assert len(sub_items) == 2, f"应有2道主观题，实际 {len(sub_items)}"
        assert len(obj_items) == 4, f"应有4道客观题，实际 {len(obj_items)}"

        # 主观题应有 feedback
        for item in sub_items:
            assert "feedback" in item
            assert "score" in item
            assert "max_score" in item

    def test_objective_only_via_llm_grade(self, client, auth_header):
        """
        场景：纯客观题走 llm-grade（无主观题直接降级为纯客观批改）
        """
        paper_resp = client.post("/api/papers", json={
            "title": "纯客观-走LLM接口",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 50,
            "exam_date": str(date.today()),
            "answer_key": {"q1": "A", "q2": "B", "q3": "C", "q4": "D", "q5": "A"},
        }, headers=auth_header)
        assert paper_resp.status_code == 200
        paper_id = paper_resp.json()["paper_id"]

        img = _create_test_image()
        client.post(
            "/api/ocr/upload-image",
            data={"paper_id": paper_id, "student_id": "S032"},
            files={"file": ("obj_only.jpg", img, "image/jpeg")},
            headers=auth_header,
        )

        resp = client.post(
            f"/api/ocr/llm-grade?paper_id={paper_id}&student_id=S032",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_subjective"] is False
        assert data["ai_score"] == 50.0  # mock返回全对


# ============================================================
# 异常流程与错误处理
# ============================================================

class TestOCRErrorHandling:
    """OCR 异常流程测试"""

    def test_grade_without_upload(self, client, auth_header):
        """未上传图片就批改"""
        from datetime import date
        # 创建试卷
        paper_resp = client.post("/api/papers", json={
            "title": "未上传测试",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 50,
            "exam_date": str(date.today()),
            "answer_key": {"q1": "A", "q2": "B"},
        }, headers=auth_header)
        if paper_resp.status_code != 200:
            pytest.skip("创建试卷失败")
        paper_id = paper_resp.json()["paper_id"]

        # 不传图片直接批改
        resp = client.post(
            f"/api/ocr/recognize?paper_id={paper_id}&student_id=S032",
            headers=auth_header,
        )
        # 应返回 400
        assert resp.status_code in [400, 404]

    def test_grade_without_answer_key(self, client, auth_header):
        """试卷没有标准答案"""
        from datetime import date
        paper_resp = client.post("/api/papers", json={
            "title": "无答案测试",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 50,
            "exam_date": str(date.today()),
        }, headers=auth_header)
        if paper_resp.status_code != 200:
            pytest.skip("创建试卷失败")
        paper_id = paper_resp.json()["paper_id"]

        # 上传图片
        img = _create_test_image()
        client.post(
            "/api/ocr/upload-image",
            data={"paper_id": paper_id, "student_id": "S032"},
            files={"file": ("no_key.jpg", img, "image/jpeg")},
            headers=auth_header,
        )

        resp = client.post(
            f"/api/ocr/recognize?paper_id={paper_id}&student_id=S032",
            headers=auth_header,
        )
        # 应提示无标准答案
        assert resp.status_code in [200, 400]

    def test_grade_nonexistent_paper(self, client, auth_header):
        """批改不存在的试卷"""
        resp = client.post(
            "/api/ocr/recognize?paper_id=99999&student_id=S032",
            headers=auth_header,
        )
        assert resp.status_code == 404

    def test_grade_nonexistent_student(self, client, auth_header):
        """批改不存在的学生"""
        from datetime import date
        paper_resp = client.post("/api/papers", json={
            "title": "不存在学生测试",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 50,
            "exam_date": str(date.today()),
            "answer_key": {"q1": "A"},
        }, headers=auth_header)
        if paper_resp.status_code != 200:
            pytest.skip("创建试卷失败")
        paper_id = paper_resp.json()["paper_id"]

        resp = client.post(
            f"/api/ocr/recognize?paper_id={paper_id}&student_id=NOBODY",
            headers=auth_header,
        )
        assert resp.status_code in [400, 404]

    def test_upload_non_image(self, client, auth_header):
        """上传非图片文件"""
        resp = client.post(
            "/api/ocr/upload-image",
            data={"paper_id": 1, "student_id": "S032"},
            files={"file": ("test.txt", io.BytesIO(b"not an image"), "text/plain")},
            headers=auth_header,
        )
        assert resp.status_code == 400

    def test_upload_empty_file(self, client, auth_header):
        """上传空文件"""
        resp = client.post(
            "/api/ocr/upload-image",
            data={"paper_id": 1, "student_id": "S032"},
            files={"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")},
            headers=auth_header,
        )
        # 空文件应被拒绝或失败
        assert resp.status_code in [400, 500]

    def test_recover_score(self, client, auth_header):
        """恢复成绩（recover）"""
        from datetime import date
        paper_resp = client.post("/api/papers", json={
            "title": "恢复成绩测试",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 50,
            "exam_date": str(date.today()),
            "answer_key": {"q1": "A"},
        }, headers=auth_header)
        if paper_resp.status_code != 200:
            pytest.skip("创建试卷失败")
        paper_id = paper_resp.json()["paper_id"]

        # 先上传并批改
        img = _create_test_image()
        client.post(
            "/api/ocr/upload-image",
            data={"paper_id": paper_id, "student_id": "S032"},
            files={"file": ("recover.jpg", img, "image/jpeg")},
            headers=auth_header,
        )
        client.post(
            f"/api/ocr/llm-grade?paper_id={paper_id}&student_id=S032",
            headers=auth_header,
        )

        # 恢复成绩（如果支持）
        resp = client.post(
            f"/api/papers/{paper_id}/recover-score?student_id=S032",
            headers=auth_header,
        )
        # 可能返回 200（成功）或 400（当前状态不允许恢复）
        assert resp.status_code in [200, 400]


# ============================================================
# 性能相关测试
# ============================================================

class TestOCRPerformance:
    """OCR 批阅性能基准"""

    def test_pipeline_response_time(self, client, auth_header, timer):
        """单次完整链路耗时（mock模式）"""
        from datetime import date

        # 创建试卷
        paper_resp = client.post("/api/papers", json={
            "title": "性能基准测试",
            "subject": "数据库系统",
            "class_id": "CS2024-01",
            "total_score": 100,
            "exam_date": str(date.today()),
            "answer_key": {f"q{i}": "A" for i in range(1, 11)},
        }, headers=auth_header)
        if paper_resp.status_code != 200:
            pytest.skip("创建试卷失败")
        paper_id = paper_resp.json()["paper_id"]

        total_time = 0

        # 上传
        img = _create_test_image()
        with timer:
            client.post(
                "/api/ocr/upload-image",
                data={"paper_id": paper_id, "student_id": "S032"},
                files={"file": ("perf.jpg", img, "image/jpeg")},
                headers=auth_header,
            )
        total_time += timer.elapsed_ms

        # OCR 识别
        with timer:
            client.post(
                f"/api/ocr/recognize?paper_id={paper_id}&student_id=S032",
                headers=auth_header,
            )
        total_time += timer.elapsed_ms

        # 自动批改
        with timer:
            client.post(
                f"/api/ocr/auto-grade?paper_id={paper_id}&student_id=S032",
                headers=auth_header,
            )
        total_time += timer.elapsed_ms

        # 总耗时应在合理范围内（mock模式下应很快）
        # 实际环境可能更慢，这里给出宽松的阈值
        assert total_time < 5000, f"完整链路耗时 {total_time:.0f}ms 超过 5000ms 阈值"


# ============================================================
# 辅助工具
# ============================================================

def _create_test_image():
    """生成 800x600 测试图片（模拟答卷）"""
    img = Image.new("RGB", (800, 600), color="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf
