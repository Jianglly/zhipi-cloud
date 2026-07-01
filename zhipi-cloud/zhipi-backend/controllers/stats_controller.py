"""
统计分析控制器 - 成绩统计、排名、学情分析
智批云后端 - controllers/stats_controller.py
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Optional
from pydantic import BaseModel
from datetime import date

from config.database import get_db
from models import Score, Student, Paper
from controllers.auth_controller import get_current_user, require_teacher, require_student, UserInfo

router = APIRouter(prefix="/api/stats", tags=["统计分析"])


# ===================== Pydantic 数据模型 =====================

class ScoreItem(BaseModel):
    score_id: int
    student_id: str
    name: str
    subject: str
    class_id: str
    score: float
    rank_in_class: Optional[int]
    exam_date: date
    paper_title: Optional[str] = None
    total_score: Optional[float] = None
    status: int

    class Config:
        from_attributes = True


class ClassOverview(BaseModel):
    subject: str
    exam_date: date
    paper_title: str
    student_count: int
    avg_score: float
    max_score: float
    min_score: float
    excellent_count: int  # 90分以上（按满分比例）
    good_count: int       # 75-90
    pass_count: int       # 60-75
    fail_count: int       # 60以下


class TrendPoint(BaseModel):
    subject: str
    score: float
    exam_date: date
    rank_in_class: Optional[int]
    total_score: float


# ===================== 学生路由 =====================

@router.get("/student/scores", response_model=List[ScoreItem], summary="学生：查询自己的成绩列表")
def get_student_scores(
    subject: Optional[str] = Query(None, description="按科目筛选"),
    current_user: UserInfo = Depends(require_student),
    db: Session = Depends(get_db)
):
    """学生查询自己的全部成绩（子模式：只返回自己的数据）"""
    query = db.query(Score, Paper).join(Paper, Score.paper_id == Paper.paper_id)\
        .filter(Score.student_id == current_user.user_id)\
        .filter(Score.status == 3)

    if subject:
        query = query.filter(Score.subject == subject)

    results = query.order_by(Score.exam_date.desc()).all()

    return [
        ScoreItem(
            score_id=s.score_id,
            student_id=s.student_id,
            name=s.name,
            subject=s.subject,
            class_id=s.class_id,
            score=float(s.score),
            rank_in_class=s.rank_in_class,
            exam_date=s.exam_date,
            paper_title=p.title,
            total_score=float(p.total_score),
            status=s.status,
        )
        for s, p in results
    ]


@router.get("/student/trend", response_model=List[TrendPoint], summary="学生：成绩趋势（用于折线图）")
def get_student_trend(
    subject: Optional[str] = Query(None, description="按科目筛选"),
    current_user: UserInfo = Depends(require_student),
    db: Session = Depends(get_db)
):
    """学生成绩趋势数据，用于前端折线图"""
    query = db.query(Score, Paper).join(Paper, Score.paper_id == Paper.paper_id)\
        .filter(Score.student_id == current_user.user_id)\
        .filter(Score.status == 3)

    if subject:
        query = query.filter(Score.subject == subject)

    results = query.order_by(Score.exam_date.asc()).all()
    return [
        TrendPoint(
            subject=s.subject,
            score=float(s.score),
            exam_date=s.exam_date,
            rank_in_class=s.rank_in_class,
            total_score=float(p.total_score),
        )
        for s, p in results
    ]


@router.get("/student/ranking", summary="学生：查看自己的班级排名")
def get_student_ranking(
    subject: Optional[str] = Query(None),
    exam_date: Optional[date] = Query(None),
    current_user: UserInfo = Depends(require_student),
    db: Session = Depends(get_db)
):
    """学生查看自己在班级中的排名（子模式限制）"""
    query = db.query(Score).filter(
        Score.student_id == current_user.user_id,
        Score.status == 3
    )
    if subject:
        query = query.filter(Score.subject == subject)
    if exam_date:
        query = query.filter(Score.exam_date == exam_date)

    scores = query.all()
    return [
        {
            "subject": s.subject,
            "score": float(s.score),
            "rank_in_class": s.rank_in_class,
            "exam_date": s.exam_date,
        }
        for s in scores
    ]


# ===================== 教师路由 =====================

@router.get("/teacher/class-overview", summary="教师：班级成绩概览")
def get_class_overview(
    class_id: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """教师查看班级整体成绩概况（教师子模式）"""
    # 如果未指定班级，默认查自己负责的班级
    target_class = class_id or current_user.class_id

    query = db.query(
        Score.subject,
        Score.exam_date,
        Score.class_id,
        Paper.title,
        Paper.total_score,
        func.count(Score.score_id).label("student_count"),
        func.round(func.avg(Score.score), 2).label("avg_score"),
        func.max(Score.score).label("max_score"),
        func.min(Score.score).label("min_score"),
    ).join(Paper, Score.paper_id == Paper.paper_id)\
     .filter(Score.class_id == target_class)\
     .filter(Score.status == 3)

    if subject:
        query = query.filter(Score.subject == subject)

    results = query.group_by(
        Score.subject, Score.exam_date, Score.class_id, Paper.title, Paper.total_score
    ).order_by(Score.exam_date.desc()).all()

    return [
        {
            "subject": r.subject,
            "exam_date": r.exam_date,
            "class_id": r.class_id,
            "paper_title": r.title,
            "total_score": float(r.total_score),
            "student_count": r.student_count,
            "avg_score": float(r.avg_score) if r.avg_score else 0,
            "max_score": float(r.max_score) if r.max_score else 0,
            "min_score": float(r.min_score) if r.min_score else 0,
        }
        for r in results
    ]


@router.get("/teacher/class-ranking", summary="教师：班级成绩排名")
def get_class_ranking(
    subject: str = Query(..., description="科目"),
    exam_date: Optional[date] = Query(None),
    class_id: Optional[str] = Query(None),
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """教师查看班级学生成绩排名"""
    target_class = class_id or current_user.class_id

    query = db.query(Score, Paper)\
        .join(Paper, Score.paper_id == Paper.paper_id)\
        .filter(Score.class_id == target_class)\
        .filter(Score.subject == subject)\
        .filter(Score.status == 3)

    if exam_date:
        query = query.filter(Score.exam_date == exam_date)

    results = query.order_by(Score.rank_in_class.asc()).all()

    return [
        {
            "rank": s.rank_in_class,
            "student_id": s.student_id,
            "name": s.name,
            "score": float(s.score),
            "total_score": float(p.total_score),
            "percent": round(float(s.score) / float(p.total_score) * 100, 1),
            "grade_level": (
                "优秀" if s.score >= p.total_score * 0.9 else
                "良好" if s.score >= p.total_score * 0.75 else
                "及格" if s.score >= p.total_score * 0.6 else "不及格"
            ),
            "exam_date": s.exam_date,
        }
        for s, p in results
    ]


@router.get("/teacher/students", summary="教师：查询班级学生列表")
def get_class_students(
    class_id: Optional[str] = Query(None),
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """教师查询班级学生名单"""
    target_class = class_id or current_user.class_id
    students = db.query(Student).filter(Student.class_id == target_class).all()
    return [
        {
            "student_id": s.student_id,
            "name": s.name,
            "class_id": s.class_id,
        }
        for s in students
    ]


@router.get("/teacher/score-distribution", summary="教师：成绩分布（用于柱状图）")
def get_score_distribution(
    subject: str = Query(...),
    exam_date: Optional[date] = Query(None),
    class_id: Optional[str] = Query(None),
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """教师查看成绩分布区间，用于前端柱状图"""
    target_class = class_id or current_user.class_id

    query = db.query(Score, Paper)\
        .join(Paper, Score.paper_id == Paper.paper_id)\
        .filter(Score.class_id == target_class)\
        .filter(Score.subject == subject)\
        .filter(Score.status == 3)

    if exam_date:
        query = query.filter(Score.exam_date == exam_date)

    results = query.all()

    # 计算成绩分布
    distribution = {"90-100": 0, "75-89": 0, "60-74": 0, "0-59": 0}
    for s, p in results:
        pct = float(s.score) / float(p.total_score) * 100
        if pct >= 90:
            distribution["90-100"] += 1
        elif pct >= 75:
            distribution["75-89"] += 1
        elif pct >= 60:
            distribution["60-74"] += 1
        else:
            distribution["0-59"] += 1

    return {
        "distribution": distribution,
        "labels": ["优秀(90+)", "良好(75-89)", "及格(60-74)", "不及格(0-59)"],
        "values": list(distribution.values()),
    }
