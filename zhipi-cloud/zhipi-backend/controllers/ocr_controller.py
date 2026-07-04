"""
OCR 批阅控制器 - 接入百度OCR API
智批云后端 - controllers/ocr_controller.py
"""
import sys
import os
import json
import time
import base64
import requests
from datetime import datetime
from typing import Tuple, List, Dict
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# 获取当前文件的上一级目录（即 zhipi-backend 根目录），并加入系统搜索路径
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.database import get_db
from config.settings import settings
from config.rate_limit import limiter
from models import Score, Paper
from controllers.auth_controller import require_teacher, UserInfo
from services.ocr_service import parse_ocr_text_to_answers, auto_grade_answers
from services.llm_service import grade_mixed_answers
from services.question_search_service import call_llm_search, search_answers_from_image

router = APIRouter(prefix="/api/ocr", tags=["OCR批阅"])

# 上传文件保存目录
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 百度OCR Access Token 缓存
_baidu_token_cache = {"token": None, "expires_at": 0}


# ===================== 百度OCR工具函数 =====================

def get_baidu_access_token() -> str:
    """
    获取百度OCR Access Token（带缓存）
    参考：https://cloud.baidu.com/doc/OCR/s/yk9b94v9h
    """
    global _baidu_token_cache
    
    # 如果token还有效（提前5分钟刷新），直接返回
    if _baidu_token_cache["token"] and _baidu_token_cache["expires_at"] > time.time() + 300:
        return _baidu_token_cache["token"]
    
    api_key = settings.BAIDU_OCR_API_KEY
    secret_key = settings.BAIDU_OCR_SECRET_KEY
    
    if not api_key or not secret_key or api_key == "your_api_key_here":
        raise HTTPException(
            status_code=500,
            detail="百度OCR未配置，请在 .env 中填写 BAIDU_OCR_API_KEY 和 BAIDU_OCR_SECRET_KEY"
        )
    
    token_url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": api_key,
        "client_secret": secret_key
    }
    
    try:
        resp = requests.post(token_url, params=params, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        
        if "error" in result:
            raise HTTPException(
                status_code=500,
                detail=f"获取百度OCR Token失败: {result.get('error_description', result['error'])}"
            )
        
        access_token = result["access_token"]
        expires_in = result.get("expires_in", 2592000)  # 默认30天
        
        _baidu_token_cache["token"] = access_token
        _baidu_token_cache["expires_at"] = time.time() + expires_in
        
        return access_token
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"请求百度OCR认证接口失败: {str(e)}")


def call_baidu_ocr(image_path: str) -> Tuple[str, List[Dict]]:
    """
    调用百度OCR手写体识别API（对手写答案准确率远高于通用印刷体）
    返回：(完整文本, 词级识别结果列表)
    
    词级结果每项: {"words": "A", "location": {"top": 100, "left": 200, "width": 30, "height": 40}}
    """
    access_token = get_baidu_access_token()
    
    # 手写体识别 API（专门针对手写答案优化）
    ocr_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/handwriting?access_token={access_token}"
    
    # 读取图片并base64编码
    with open(image_path, "rb") as f:
        img_data = f.read()
    
    img_base64 = base64.b64encode(img_data).decode("utf-8")
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "image": img_base64,
        "recognize_granularity": "big",
    }
    
    try:
        resp = requests.post(ocr_url, headers=headers, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        if "error_code" in result:
            # 如果手写体识别失败（如图片质量太差），降级到通用OCR
            print(f"[OCR] 手写体识别失败，降级到通用OCR: {result.get('error_msg', result['error_code'])}")
            return call_baidu_ocr_general(image_path)
        
        words_result = result.get("words_result", [])
        # 手写体API返回格式略有不同，需要拼接完整文本
        full_text = "\n".join([item["words"] for item in words_result])
        
        # 手写体API不返回词级位置信息，构造空列表
        # 如果返回了位置信息则使用
        words_with_location = []
        for item in words_result:
            loc = item.get("location")
            if loc:
                words_with_location.append({"words": item["words"], "location": loc})
            else:
                words_with_location.append({"words": item["words"], "location": {"top": 0, "left": 0, "width": 0, "height": 0}})
        
        return full_text, words_with_location
        
    except HTTPException:
        raise
    except Exception as e:
        # 降级到通用OCR
        print(f"[OCR] 手写体识别异常，降级到通用OCR: {str(e)}")
        return call_baidu_ocr_general(image_path)


def call_baidu_ocr_general(image_path: str) -> Tuple[str, List[Dict]]:
    """
    降级方案：百度OCR通用文字识别API（印刷体/通用场景）
    当手写体识别失败时使用
    """
    access_token = get_baidu_access_token()
    
    ocr_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"
    
    with open(image_path, "rb") as f:
        img_data = f.read()
    
    img_base64 = base64.b64encode(img_data).decode("utf-8")
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "image": img_base64,
        "detect_direction": "true",
        "paragraph": "true",
        "probability": "false"
    }
    
    try:
        resp = requests.post(ocr_url, headers=headers, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        if "error_code" in result:
            raise HTTPException(
                status_code=500,
                detail=f"百度OCR识别失败 [{result['error_code']}]: {result.get('error_msg', '未知错误')}"
            )
        
        words_result = result.get("words_result", [])
        full_text = "\n".join([item["words"] for item in words_result])
        return full_text, words_result
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"调用百度OCR API失败: {str(e)}")


# ===================== 路由 =====================

@router.post("/upload-image", summary="教师：上传学生答卷图片")
@limiter.limit("10/minute")
async def upload_answer_image(
    request: Request,
    paper_id: int = Form(...),
    student_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """上传学生答卷图片，保存到本地"""
    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只支持图片文件")
    
    # 保存文件
    file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"paper{paper_id}_{student_id}_{timestamp}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    
    # 更新数据库中的 answer_image 字段
    score_record = db.query(Score).filter(
        Score.paper_id == paper_id,
        Score.student_id == student_id
    ).first()
    
    if score_record:
        score_record.answer_image = file_path.replace("\\", "/")
        db.flush()
    
    return JSONResponse(
        content={
            "message": "上传成功",
            "file_path": file_path.replace("\\", "/"),
            "url": f"/static/uploads/{filename}"
        }
    )


@router.post("/recognize", summary="OCR识别学生答案（百度OCR）")
def ocr_recognize(
    paper_id: int,
    student_id: str,
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """
    调用百度OCR识别学生答卷，解析出各题答案
    需要先在 .env 中配置百度OCR的 API Key 和 Secret Key
    """
    # 获取试卷和标准答案
    paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")
    
    if not paper.answer_key:
        return {"message": "该试卷未设置标准答案，无法识别", "result": {}}
    
    answer_key = paper.answer_key if isinstance(paper.answer_key, dict) else json.loads(paper.answer_key)
    
    # 获取学生答卷图片路径
    score_record = db.query(Score).filter(
        Score.paper_id == paper_id,
        Score.student_id == student_id
    ).first()
    
    if not score_record or not score_record.answer_image:
        raise HTTPException(status_code=400, detail="该学生尚未上传答卷图片")
    
    image_path = score_record.answer_image
    
    # 调用百度OCR识别
    try:
        ocr_raw_text, words_result = call_baidu_ocr(image_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR识别失败: {str(e)}")
    
    # 解析OCR文本为结构化答案（传入词级结果用于位置排序）
    ocr_result = parse_ocr_text_to_answers(ocr_raw_text, answer_key, words_result)
    
    # 更新数据库中的 ai_result 字段
    if score_record:
        score_record.ai_result = ocr_result
        score_record.status = 1  # AI批阅中
        db.flush()
    
    return {
        "message": "OCR识别完成（百度OCR）",
        "student_id": student_id,
        "ocr_raw_text": ocr_raw_text,   # OCR原始文本（用于调试）
        "ocr_result": ocr_result,         # 解析后的答案
        "answer_key": answer_key,
        "parse_rate": f"{sum(1 for v in ocr_result.values() if v)}/{len(ocr_result)}"  # 识别到答案的题数
    }


@router.post("/auto-grade", summary="自动批改客观题")
def auto_grade_api(
    paper_id: int,
    student_id: str,
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """根据 OCR 识别结果自动批改，返回AI分数"""
    paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")
    
    score_record = db.query(Score).filter(
        Score.paper_id == paper_id,
        Score.student_id == student_id
    ).first()
    
    if not score_record:
        raise HTTPException(status_code=404, detail="成绩记录不存在，请先上传答卷")
    
    if not paper.answer_key:
        raise HTTPException(status_code=400, detail="该试卷未设置标准答案")
    
    answer_key = paper.answer_key if isinstance(paper.answer_key, dict) else json.loads(paper.answer_key)
    ocr_result = score_record.ai_result if score_record.ai_result else {}
    
    # 如果没有OCR结果，先执行识别
    if not ocr_result:
        if not score_record.answer_image:
            raise HTTPException(status_code=400, detail="该学生尚未上传答卷图片，请先上传")
        
        ocr_raw_text, words_result = call_baidu_ocr(score_record.answer_image)
        ocr_result = parse_ocr_text_to_answers(ocr_raw_text, answer_key, words_result)
        score_record.ai_result = ocr_result
        score_record.status = 1
    
    # 自动批改
    ai_score, detail_list = auto_grade_answers(ocr_result, answer_key, float(paper.total_score))
    
    # 更新数据库
    score_record.ai_score = ai_score
    score_record.status = 2  # 待人工审核
    db.flush()
    
    return {
        "message": "自动批改完成",
        "student_id": student_id,
        "ai_score": ai_score,
        "total_score": float(paper.total_score),
        "detail": detail_list,
        "ocr_result": ocr_result,
        "answer_key": answer_key
    }


@router.get("/grade-result/{paper_id}", summary="查看试卷所有学生的AI批改结果")
def get_grade_results(
    paper_id: int,
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """查看某张试卷所有学生的AI批改结果"""
    results = db.query(Score).filter(
        Score.paper_id == paper_id,
        Score.status.in_([1, 2, 3])
    ).all()
    
    return [
        {
            "score_id": s.score_id,
            "student_id": s.student_id,
            "name": s.name,
            "ai_score": float(s.ai_score) if s.ai_score else None,
            "manual_score": float(s.manual_score) if s.manual_score else None,
            "total_score": float(s.score) if s.score else None,
            "status": s.status,
            "status_text": ["", "AI批阅中", "待人工审核", "已完成"][s.status],
            "answer_image": s.answer_image,
            "ai_result": s.ai_result
        }
        for s in results
    ]


# ===================== LLM 大题批改路由 =====================

@router.post("/llm-grade", summary="AI批改大题（客观题正则+主观题LLM）")
@limiter.limit("5/minute")
def llm_grade_api(
    request: Request,
    paper_id: int,
    student_id: str,
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """
    混合批改：客观题用正则比对，主观题用 LLM 评分。
    需要在 .env 中配置 LLM_API_KEY（DeepSeek / 通义千问 / OpenAI 均可）。
    """
    paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")

    if not paper.answer_key:
        raise HTTPException(status_code=400, detail="该试卷未设置标准答案")

    answer_key = paper.answer_key if isinstance(paper.answer_key, dict) else json.loads(paper.answer_key)

    score_record = db.query(Score).filter(
        Score.paper_id == paper_id,
        Score.student_id == student_id
    ).first()

    if not score_record or not score_record.answer_image:
        raise HTTPException(status_code=400, detail="该学生尚未上传答卷图片")

    # 检查是否存在主观题
    has_subjective = any(
        isinstance(v, dict) and v.get("type") == "subjective"
        for v in answer_key.values()
    )

    # 调用 OCR 识别
    try:
        ocr_raw_text, words_result = call_baidu_ocr(score_record.answer_image)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR识别失败: {str(e)}")

    # 解析客观题答案
    from services.ocr_service import parse_ocr_text_to_answers
    ocr_result = parse_ocr_text_to_answers(ocr_raw_text, answer_key, words_result)

    # 保存 OCR 结果
    score_record.ai_result = ocr_result
    score_record.status = 1
    db.flush()

    if not has_subjective:
        # 没有主观题，走纯客观题批改
        from services.ocr_service import auto_grade_answers
        ai_score, detail_list = auto_grade_answers(ocr_result, answer_key, float(paper.total_score))

        score_record.ai_score = ai_score
        score_record.status = 2
        db.flush()

        return {
            "message": "客观题批改完成（无主观题）",
            "student_id": student_id,
            "ai_score": ai_score,
            "total_score": float(paper.total_score),
            "detail": detail_list,
            "ocr_result": ocr_result,
            "ocr_raw_text": ocr_raw_text,
            "answer_key": answer_key,
            "has_subjective": False,
        }

    # 有主观题 → 混合批改
    try:
        ai_score, detail_list = grade_mixed_answers(
            ocr_raw_text, answer_key, float(paper.total_score), ocr_result
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM批改失败: {str(e)}")

    # 更新数据库
    score_record.ai_score = ai_score
    score_record.status = 2  # 待人工审核
    db.flush()

    return {
        "message": "AI批改完成（客观题+主观题）",
        "student_id": student_id,
        "ai_score": ai_score,
        "total_score": float(paper.total_score),
        "detail": detail_list,
        "ocr_result": ocr_result,
        "ocr_raw_text": ocr_raw_text,
        "answer_key": answer_key,
        "has_subjective": True,
    }


# ===================== LLM 搜题批改路由 =====================

@router.post("/search-answers", summary="教师上传试卷图片→DeepSeek搜答案")
@limiter.limit("5/minute")
async def search_answers(
    request: Request,
    file: UploadFile = File(...),
    subject: str = Form(...),
    total_score: float = Form(100),
    paper_id: int = Form(None),
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """
    上传试卷原题图片，DeepSeek自动识别题目并给出标准答案。

    — 无需手动录入 answer_key，拍照即可
    — 支持选择题（ABCD）、填空题、主观题（含评分要点）
    — 可选传入 paper_id，自动将搜到的答案保存到试卷

    返回 format:
        {"answer_key": {"q1": "A", ...}, "ocr_text": "...", "question_count": 15}
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只支持图片文件")

    # 保存临时文件
    file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"search_{current_user.user_id}_{timestamp}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    # OCR + LLM搜题
    try:
        answer_key = search_answers_from_image(file_path, subject, total_score)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜题失败: {str(e)}")

    # 统计题目数量
    obj_count = sum(1 for v in answer_key.values() if isinstance(v, str))
    subj_count = sum(1 for v in answer_key.values()
                     if isinstance(v, dict) and v.get("type") == "subjective")
    fill_count = sum(1 for v in answer_key.values()
                     if isinstance(v, dict) and v.get("type") == "fill_blank")

    # 如果传了 paper_id，自动保存 answer_key
    saved = False
    if paper_id:
        paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()
        if paper:
            paper.answer_key = answer_key
            paper.status = 1  # 已发布
            db.flush()
            saved = True

    return JSONResponse(content={
        "message": "搜题完成",
        "subject": subject,
        "answer_key": answer_key,
        "question_count": len(answer_key),
        "objective_count": obj_count,
        "subjective_count": subj_count,
        "fill_blank_count": fill_count,
        "saved_to_paper": saved,
        "paper_id": paper_id if saved else None,
    })


@router.post("/search-grade", summary="搜题+保存answer_key+自动批改全链路")
@limiter.limit("3/minute")
async def search_and_grade_all(
    request: Request,
    file: UploadFile = File(...),
    paper_id: int = Form(...),
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """
    一键搜题批改：上传试卷图片 → OCR → DeepSeek搜答案 → 存answer_key → 批改所有学生。

    这是最方便的全自动入口：
    教师只需要拍一张试卷原题图 + 指定 paper_id，系统自动完成搜题、存答案、批全班的流程。

    前置条件：学生答卷图片已上传（通过 POST /api/ocr/upload-image）
    """
    paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")

    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只支持图片文件")

    # 保存图片
    file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"paper_{paper_id}_{timestamp}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    total_score = float(paper.total_score)

    # ===== 步骤1: 搜题 =====
    try:
        answer_key = search_answers_from_image(file_path, paper.subject, total_score)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"搜题失败: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"答案解析失败: {str(e)}")

    # ===== 步骤2: 保存 answer_key =====
    paper.answer_key = answer_key
    paper.status = 2  # 批阅中
    db.flush()

    # ===== 步骤3: 获取所有待批阅学生 =====
    score_records = db.query(Score).filter(
        Score.paper_id == paper_id,
        Score.status.in_([0, 1])
    ).all()

    if not score_records:
        return JSONResponse(content={
            "message": "搜题完成，但该试卷下没有待批阅的学生答卷",
            "paper_id": paper_id,
            "answer_key": answer_key,
            "question_count": len(answer_key),
            "graded_count": 0,
        })

    # ===== 步骤4: 逐个批改 =====
    graded_count = 0
    errors = []

    for score_record in score_records:
        try:
            if not score_record.answer_image:
                errors.append({
                    "student_id": score_record.student_id,
                    "name": score_record.name,
                    "error": "未上传答卷图片",
                })
                continue

            # OCR识别学生答案
            ocr_raw_text, words_result = call_baidu_ocr(score_record.answer_image)
            ocr_result = parse_ocr_text_to_answers(ocr_raw_text, answer_key, words_result)

            # 判断是否包含主观题
            has_subjective = any(
                isinstance(v, dict) and v.get("type") == "subjective"
                for v in answer_key.values()
            )

            if has_subjective:
                # 混合批改（客观题正则 + 主观题LLM）
                ai_score, detail_list = grade_mixed_answers(
                    ocr_raw_text, answer_key, total_score, ocr_result
                )
            else:
                # 纯客观题批改
                ai_score, detail_list = auto_grade_answers(
                    ocr_result, answer_key, total_score
                )

            score_record.ai_result = ocr_result
            score_record.ai_score = ai_score
            score_record.status = 2  # 待人工审核
            graded_count += 1

        except HTTPException:
            raise
        except Exception as e:
            errors.append({
                "student_id": score_record.student_id,
                "name": score_record.name,
                "error": str(e),
            })

    db.flush()

    return JSONResponse(content={
        "message": f"搜题批改完成: {graded_count}/{len(score_records)} 名学生已批改",
        "paper_id": paper_id,
        "subject": paper.subject,
        "total_score": total_score,
        "answer_key": answer_key,
        "question_count": len(answer_key),
        "total_students": len(score_records),
        "graded_count": graded_count,
        "error_count": len(errors),
        "errors": errors,
    })

