"""
试卷管理控制器 - 教师管理试卷、查看待批阅列表
智批云后端 - controllers/paper_controller.py
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import date
from typing import Any, Dict

from config.database import get_db
from models import Score, Paper, Student
from controllers.auth_controller import require_teacher, require_student, get_current_user, UserInfo

router = APIRouter(prefix="/api/papers", tags=["试卷管理"])


# ===================== Pydantic 数据模型 =====================

class PaperCreate(BaseModel):
    title: str
    subject: str
    class_id: str
    total_score: float = 150.0
    exam_date: date
    answer_key: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class PaperResponse(BaseModel):
    paper_id: int
    title: str
    subject: str
    class_id: str
    teacher_id: str
    total_score: float
    exam_date: date
    status: int
    description: Optional[str]

    class Config:
        from_attributes = True


# ===================== 试卷路由 =====================

@router.get("/", summary="获取试卷列表")
def get_papers(
    class_id: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取试卷列表（学生只能看自己班级的已发布试卷，教师可看全部）"""
    query = db.query(Paper)

    if current_user.role == "student":
        # 学生只看自己班级的已发布试卷
        query = query.filter(
            Paper.class_id == current_user.class_id,
            Paper.status.in_([1, 2, 3])
        )
    else:
        # 教师可以按班级筛选
        if class_id:
            query = query.filter(Paper.class_id == class_id)
        elif current_user.role == "teacher":
            query = query.filter(Paper.teacher_id == current_user.user_id)

    if subject:
        query = query.filter(Paper.subject == subject)

    papers = query.order_by(Paper.exam_date.desc()).all()

    return [
        {
            "paper_id": p.paper_id,
            "title": p.title,
            "subject": p.subject,
            "class_id": p.class_id,
            "teacher_id": p.teacher_id,
            "total_score": float(p.total_score),
            "exam_date": p.exam_date,
            "status": p.status,
            "status_text": ["草稿", "已发布", "批阅中", "已完成"][p.status],
        }
        for p in papers
    ]


@router.post("/", summary="教师：创建试卷")
def create_paper(
    data: PaperCreate,
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """教师创建新试卷"""
    paper = Paper(
        title=data.title,
        subject=data.subject,
        class_id=data.class_id,
        teacher_id=current_user.user_id,
        total_score=data.total_score,
        exam_date=data.exam_date,
        answer_key=data.answer_key,
        description=data.description,
        status=1,  # 直接发布
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return {"message": "试卷创建成功", "paper_id": paper.paper_id}


@router.get("/pending", summary="教师：获取待批阅列表")
def get_pending_scores(
    class_id: Optional[str] = Query(None),
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """教师查看待批阅的答卷列表（含安全恢复：状态异常但未完成批阅的记录也会显示）"""
    from sqlalchemy import or_, and_
    
    target_class = class_id or current_user.class_id
    results = db.query(Score, Paper)\
        .join(Paper, Score.paper_id == Paper.paper_id)\
        .filter(Score.class_id == target_class)\
        .filter(
            or_(
                Score.status.in_([0, 1, 2]),                    # 正常待批阅状态
                and_(Score.status == 3, Score.manual_score == None)  # 异常完成但未手动批阅
            )
        )\
        .order_by(Score.status.asc(), Score.created_at.desc()).all()

    return [
        {
            "score_id": s.score_id,
            "paper_id": s.paper_id,
            "student_id": s.student_id,
            "name": s.name,
            "subject": s.subject,
            "paper_title": p.title,
            "exam_date": s.exam_date,
            "status": s.status,
            "status_text": (["待批阅", "AI批阅中", "待人工审核", "已完成"][s.status] 
                           if s.status != 3 else "已完成（待审核）"),
            "ai_score": float(s.ai_score) if s.ai_score else None,
            "answer_image": s.answer_image,
        }
        for s, p in results
    ]


@router.post("/{paper_id}/submit-score", summary="教师：手动录入/审核成绩")
def submit_score(
    paper_id: int,
    student_id: str,
    manual_score: float,
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """教师手动批阅或审核AI批阅结果"""
    score_record = db.query(Score).filter(
        Score.paper_id == paper_id,
        Score.student_id == student_id
    ).first()

    if not score_record:
        # 如果不存在则创建
        paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="试卷不存在")
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="学生不存在")

        score_record = Score(
            student_id=student_id,
            paper_id=paper_id,
            subject=paper.subject,
            class_id=paper.class_id,
            name=student.name,
            score=manual_score,
            manual_score=manual_score,
            exam_date=paper.exam_date,
            status=3,
        )
        db.add(score_record)
    else:
        score_record.manual_score = manual_score
        score_record.score = (
            float(score_record.ai_score or 0) + manual_score
        )
        score_record.status = 3

    db.commit()

    # 重新计算班级排名
    _recalculate_rankings(db, paper_id)

    return {"message": "成绩录入成功"}


@router.post("/{paper_id}/recover-score", summary="教师：恢复已完成成绩到待审核状态")
def recover_score(
    paper_id: int,
    student_id: str,
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """将意外提交/状态异常的成绩恢复到待人工审核状态（status=2），防止试卷丢失"""
    score_record = db.query(Score).filter(
        Score.paper_id == paper_id,
        Score.student_id == student_id
    ).first()
    
    if not score_record:
        raise HTTPException(status_code=404, detail="成绩记录不存在")
    
    # 只恢复状态，保留已保存的分数数据
    score_record.status = 2
    score_record.manual_score = None
    score_record.score = 0.00
    db.commit()
    
    return {
        "message": "成绩已恢复到待审核状态",
        "paper_id": paper_id,
        "student_id": student_id,
        "new_status": 2,
        "status_text": "待人工审核"
    }


def _recalculate_rankings(db: Session, paper_id: int):
    """重新计算某张试卷的班级排名"""
    scores = db.query(Score).filter(
        Score.paper_id == paper_id,
        Score.status == 3
    ).order_by(Score.score.desc()).all()

    for i, s in enumerate(scores, 1):
        s.rank_in_class = i

    db.commit()
