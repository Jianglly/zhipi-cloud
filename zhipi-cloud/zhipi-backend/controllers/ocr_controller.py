"""
OCR 批阅控制器 - 接入百度OCR API
智批云后端 - controllers/ocr_controller.py
"""
import os
import json
import time
import base64
import requests
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Tuple

from config.database import get_db
from config.settings import settings
from models import Score, Paper
from controllers.auth_controller import require_teacher, get_current_user, UserInfo

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
    调用百度OCR通用文字识别API
    返回：(完整文本, 词级识别结果列表)
    
    词级结果每项: {"words": "A", "location": {"top": 100, "left": 200, "width": 30, "height": 40}}
    """
    access_token = get_baidu_access_token()
    
    # 读取图片并base64编码
    with open(image_path, "rb") as f:
        img_data = f.read()
    
    img_base64 = base64.b64encode(img_data).decode("utf-8")
    
    # 百度OCR通用文字识别API（标准版）
    ocr_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"
    
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


def parse_ocr_text_to_answers(ocr_text: str, answer_key: Dict, words_result: List[Dict] = None) -> Dict:
    """
    将OCR识别的文本解析为结构化答案。
    
    针对手写选择题答卷优化，支持三种模式：
    
    模式A — 结构化答卷（如 "1. A / 2. D"）：
      按题号+空格/标点+字母的正则匹配提取
    
    模式B — 纯字母列表（如 "A D D C"）：
      检测到连续字母时按顺序分配给各题
    
    模式C — 位置排序兜底：
      利用OCR返回的词坐标，从上到下从左到右排序，
      筛选出单个A-D字母，按题号顺序分配
    """
    import re
    
    result = {}
    if not answer_key:
        return result
    
    question_count = len(answer_key)
    
    # 构建有序题号列表
    q_items = []
    for q_key in answer_key.keys():
        q_num = q_key.replace("q", "").replace("Q", "")
        try:
            q_items.append((int(q_num), q_key))
        except ValueError:
            q_items.append((9999, q_key))
    q_items.sort()
    ordered_keys = [k for _, k in q_items]
    
    lines = [line.strip() for line in ocr_text.strip().split("\n") if line.strip()]
    
    # ========== 模式A：结构化匹配 — 找 "题号 + 字母" ==========
    found_structured = 0
    ocr_upper = ocr_text.upper()
    for idx, q_key in enumerate(ordered_keys):
        q_num = str(idx + 1)
        student_ans = ""
        
        # 多种题号格式
        patterns_a = [
            rf"(?<!\d){q_num}\s*[.、,:：)\]]\s*([A-D])(?!\s*[a-z])",
            rf"第\s*{q_num}\s*题\s*[:：]?\s*([A-D])",
            rf"\(\s*{q_num}\s*\)\s*([A-D])",
            rf"(?<!\d){q_num}\s+([A-D])\b",
        ]
        for pat in patterns_a:
            m = re.search(pat, ocr_upper)
            if m:
                student_ans = m.group(1)
                break
        
        # 弱匹配：数字后紧跟字母 "1A" "2D"
        if not student_ans:
            m = re.search(rf"(?<!\d){q_num}([A-D])(?!\s*[a-z])", ocr_upper)
            if m:
                student_ans = m.group(1)
        
        result[q_key] = student_ans
        if student_ans:
            found_structured += 1
    
    # 模式A成功率高 → 直接返回
    if found_structured >= question_count * 0.5:
        return result
    
    # ========== 模式B：纯字母序列 ==========
    # 检测行中是否全是单个字母（手写答卷常见格式："A D C B" 每行几个字母）
    letter_sequence = []
    for line in lines:
        stripped = line.strip().upper()
        # 去除常见分隔符
        clean = re.sub(r'[\s.、,，;；()（）\[\]{}|/\\\-_=+*&^%$#@!~`\'"]', '', stripped)
        if clean and all(c in 'ABCD' for c in clean) and len(clean) <= 4:
            letter_sequence.extend(list(clean))
    
    # 如果找到足够多的纯字母，按顺序分配
    if len(letter_sequence) >= question_count * 0.6:
        for i, q_key in enumerate(ordered_keys):
            if i < len(letter_sequence):
                result[q_key] = letter_sequence[i]
            else:
                result[q_key] = result.get(q_key, "")
        return result
    
    # ========== 模式C：位置排序兜底 ==========
    if words_result:
        # 提取所有单字母（A-D）并按坐标排序
        letter_items = []
        for item in words_result:
            word = item.get("words", "").strip().upper()
            loc = item.get("location", {})
            # 筛选：长度1-2的字母字符串（手写可能被误加空格或粘连）
            clean_word = re.sub(r'[^A-D]', '', word)
            if len(clean_word) == 1 and clean_word in 'ABCD':
                top = loc.get("top", 0)
                left = loc.get("left", 0)
                letter_items.append({
                    "letter": clean_word,
                    "y": top,
                    "x": left
                })
        
        if letter_items:
            # 按行分组（y坐标相近的视为同一行），行内按x排序
            letter_items.sort(key=lambda it: it["y"])
            rows = []
            current_row = [letter_items[0]]
            for item in letter_items[1:]:
                if abs(item["y"] - current_row[-1]["y"]) < 30:  # 同一行阈值
                    current_row.append(item)
                else:
                    rows.append(current_row)
                    current_row = [item]
            rows.append(current_row)
            
            # 每行内按x排序
            for row in rows:
                row.sort(key=lambda it: it["x"])
            
            # 展平为有序字母列表
            ordered_letters = []
            for row in rows:
                ordered_letters.extend([it["letter"] for it in row])
            
            # 过滤掉可能是题目文字的字母（按位置启发式过滤）
            # 如果一行中有超过4个字母，可能是题目文本而非答案
            filtered_letters = []
            for row in rows:
                if len(row) <= 4:
                    filtered_letters.extend([it["letter"] for it in row])
            
            # 用过滤后的，如果不够再用未过滤的
            source = filtered_letters if len(filtered_letters) >= question_count * 0.4 else ordered_letters
            
            for i, q_key in enumerate(ordered_keys):
                if not result.get(q_key) and i < len(source):
                    result[q_key] = source[i]
                elif not result.get(q_key):
                    result[q_key] = ""
    
    # 确保所有题都有值
    for q_key in ordered_keys:
        if q_key not in result:
            result[q_key] = ""
    
    return result


def auto_grade(ocr_result: dict, answer_key: dict, total_score: float) -> tuple:
    """
    自动批改：比对 OCR 识别结果和标准答案
    返回：(ai_score, detail_list)
    """
    if not answer_key:
        return 0.0, []
    
    total_questions = len(answer_key)
    ai_score = 0.0
    detail_list = []
    
    # 每题分值（简化：平均分配）
    per_question_score = total_score / total_questions if total_questions > 0 else 0
    
    for q_key, correct_ans in answer_key.items():
        student_ans = ocr_result.get(q_key, "")
        is_correct = False
        
        # 判断答案是否正确（支持多选）
        if isinstance(correct_ans, str) and isinstance(student_ans, str):
            if not student_ans:
                is_correct = False  # 未识别到答案
            elif "，" in student_ans or "," in student_ans:
                # 多选
                student_set = set(student_ans.replace(" ", "").split(","))
                correct_set = set(correct_ans.replace(" ", "").split(","))
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
            "score": round(earned_score, 2)
        })
    
    return round(ai_score, 2), detail_list


# ===================== 路由 =====================

@router.post("/upload-image", summary="教师：上传学生答卷图片")
async def upload_answer_image(
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
        db.commit()
    
    return {
        "message": "上传成功",
        "file_path": file_path.replace("\\", "/"),
        "url": f"/static/uploads/{filename}"
    }


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
        db.commit()
    
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
    ai_score, detail_list = auto_grade(ocr_result, answer_key, float(paper.total_score))
    
    # 更新数据库
    score_record.ai_score = ai_score
    score_record.status = 2  # 待人工审核
    db.commit()
    
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
