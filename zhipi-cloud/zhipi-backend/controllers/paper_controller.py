"""
试卷管理控制器 - 教师管理试卷、查看待批阅列表
智批云后端 - controllers/paper_controller.py
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from config.database import get_db
from models import Score, Paper, Student, ClassInfo, TeacherClass
from controllers.auth_controller import require_teacher, get_current_user
from schemas import PaperCreate, PaperUpdate, UserInfo

router = APIRouter(prefix="/api/papers", tags=["试卷管理"])


# ===================== 教师权限校验工具 =====================

def _get_teacher_class_ids(db: Session, teacher_id: str) -> set:
    """获取教师任教的班级 ID 集合（含主负责班）"""
    rows = db.query(TeacherClass.class_id).filter(TeacherClass.teacher_id == teacher_id).all()
    classes = {r[0] for r in rows}
    from models import Teacher
    t = db.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()
    if t and t.class_id:
        classes.add(t.class_id)
    return classes


def _teacher_can_access(db: Session, teacher_user: UserInfo, paper: Paper) -> bool:
    """教师能否查看/操作该试卷：科目一致且班级在任教范围内"""
    teacher_classes = _get_teacher_class_ids(db, teacher_user.user_id)
    return paper.subject == teacher_user.subject and paper.class_id in teacher_classes


# ===================== 试卷列表 / 创建 =====================

@router.get("", summary="获取试卷列表")
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
    elif current_user.role == "teacher":
        # 教师只能看任教科目 + 任教班级的试卷
        teacher_classes = _get_teacher_class_ids(db, current_user.user_id)
        query = query.filter(
            Paper.subject == current_user.subject,
            Paper.class_id.in_(teacher_classes)
        )
        if class_id:
            if class_id not in teacher_classes:
                return []
            query = query.filter(Paper.class_id == class_id)
        if subject:
            if subject != current_user.subject:
                return []
            query = query.filter(Paper.subject == subject)
    # admin 角色可查看全部（由 admin_controller 负责）

    papers = query.order_by(Paper.exam_date.desc()).all()

    # 预加载班级名称
    class_map = {c.class_id: c.class_name for c in db.query(ClassInfo).all()}

    return [
        {
            "paper_id": p.paper_id,
            "title": p.title,
            "subject": p.subject,
            "class_id": p.class_id,
            "class_name": class_map.get(p.class_id, p.class_id),
            "teacher_id": p.teacher_id,
            "total_score": float(p.total_score),
            "exam_date": p.exam_date,
            "status": p.status,
            "status_text": ["草稿", "已发布", "批阅中", "已完成"][p.status],
            "has_answer_key": bool(p.answer_key),
        }
        for p in papers
    ]


@router.post("", summary="教师：创建试卷")
def create_paper(
    data: PaperCreate,
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """教师创建新试卷（只能创建自己任教科目和任教班级的试卷）"""
    if data.subject != current_user.subject:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"您只能创建 {current_user.subject} 科目的试卷"
        )
    teacher_classes = _get_teacher_class_ids(db, current_user.user_id)
    if data.class_id not in teacher_classes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有任教该班级的权限"
        )

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
    db.flush()  # 获取 paper_id 但不提交（由 get_db() 依赖注入自动提交）
    db.refresh(paper)
    return {"message": "试卷创建成功", "paper_id": paper.paper_id}


# ===================== 命名路由（必须在 /{paper_id} 之前） =====================

@router.get("/classes", summary="获取班级列表")
def get_classes(
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取班级列表（教师仅能看到任教班级，管理员/学生可看到全部）"""
    query = db.query(ClassInfo).order_by(ClassInfo.class_id)
    if current_user.role == "teacher":
        teacher_classes = _get_teacher_class_ids(db, current_user.user_id)
        query = query.filter(ClassInfo.class_id.in_(teacher_classes))
    classes = query.all()
    return [
        {
            "class_id": c.class_id,
            "class_name": c.class_name,
            "grade": c.grade,
            "department": c.department,
        }
        for c in classes
    ]


@router.get("/pending", summary="教师：获取待批阅列表")
def get_pending_scores(
    class_id: Optional[str] = Query(None),
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """教师查看待批阅的答卷列表（仅限任教科目和任教班级）"""
    from sqlalchemy import or_, and_

    teacher_classes = _get_teacher_class_ids(db, current_user.user_id)
    target_class = class_id
    if not target_class:
        target_class = current_user.class_id
    if target_class not in teacher_classes:
        return []

    results = db.query(Score, Paper)\
        .join(Paper, Score.paper_id == Paper.paper_id)\
        .filter(Score.class_id == target_class)\
        .filter(Paper.subject == current_user.subject)\
        .filter(
            or_(
                Score.status.in_([0, 1, 2]),
                and_(Score.status == 3, Score.manual_score == None)
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
            "has_answer_key": bool(p.answer_key),
        }
        for s, p in results
    ]


@router.get("/completed", summary="教师：获取已批阅列表")
def get_completed_scores(
    class_id: Optional[str] = Query(None),
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """教师查看已批阅的答卷列表（仅限任教科目和任教班级）"""
    from sqlalchemy import or_

    teacher_classes = _get_teacher_class_ids(db, current_user.user_id)
    target_class = class_id
    if not target_class:
        target_class = current_user.class_id
    if target_class not in teacher_classes:
        return []

    results = db.query(Score, Paper)\
        .join(Paper, Score.paper_id == Paper.paper_id)\
        .filter(Score.class_id == target_class)\
        .filter(Paper.subject == current_user.subject)\
        .filter(Score.status == 3)\
        .filter(Score.manual_score != None)\
        .order_by(Score.updated_at.desc()).all()

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
            "status_text": "已完成",
            "ai_score": float(s.ai_score) if s.ai_score else None,
            "manual_score": float(s.manual_score) if s.manual_score else None,
            "total_score": float(s.score) if s.score else None,
            "answer_image": s.answer_image,
            "rank_in_class": s.rank_in_class,
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
    paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")
    if current_user.role == "teacher" and not _teacher_can_access(db, current_user, paper):
        raise HTTPException(status_code=403, detail="您没有批阅该试卷的权限")

    score_record = db.query(Score).filter(
        Score.paper_id == paper_id,
        Score.student_id == student_id
    ).first()

    if not score_record:
        # 如果不存在则创建
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

    db.flush()

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

    paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")
    if not _teacher_can_access(db, current_user, paper):
        raise HTTPException(status_code=403, detail="您没有操作该试卷的权限")

    # 只恢复状态，保留已保存的分数数据
    score_record.status = 2
    score_record.manual_score = None
    score_record.score = 0.00

    return {
        "message": "成绩已恢复到待审核状态",
        "paper_id": paper_id,
        "student_id": student_id,
        "new_status": 2,
        "status_text": "待人工审核"
    }


# ===================== 试卷详情 / 更新 / 删除（放在命名路由之后避免路由冲突） =====================

@router.get("/{paper_id}", summary="获取试卷详情（含标准答案）")
def get_paper_detail(
    paper_id: int,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取单个试卷详情，包含 answer_key"""
    paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")

    if current_user.role == "teacher" and not _teacher_can_access(db, current_user, paper):
        raise HTTPException(status_code=403, detail="您没有查看该试卷的权限")

    answer_key = paper.answer_key
    if answer_key and not isinstance(answer_key, dict):
        import json
        answer_key = json.loads(answer_key)

    # 统计题目信息
    has_subjective = False
    objective_count = 0
    subjective_count = 0
    fill_blank_count = 0
    if answer_key:
        for v in answer_key.values():
            if isinstance(v, dict):
                q_type = v.get("type", "subjective")
                if q_type == "fill_blank":
                    fill_blank_count += 1
                else:
                    has_subjective = True
                    subjective_count += 1
            else:
                objective_count += 1

    class_info = db.query(ClassInfo).filter(ClassInfo.class_id == paper.class_id).first()

    return {
        "paper_id": paper.paper_id,
        "title": paper.title,
        "subject": paper.subject,
        "class_id": paper.class_id,
        "class_name": class_info.class_name if class_info else paper.class_id,
        "teacher_id": paper.teacher_id,
        "total_score": float(paper.total_score),
        "exam_date": paper.exam_date,
        "status": paper.status,
        "status_text": ["草稿", "已发布", "批阅中", "已完成"][paper.status],
        "answer_key": answer_key,
        "description": paper.description,
        "has_answer_key": bool(answer_key),
        "has_subjective": has_subjective,
        "objective_count": objective_count,
        "subjective_count": subjective_count,
        "fill_blank_count": fill_blank_count,
        "total_questions": objective_count + subjective_count + fill_blank_count,
    }


@router.put("/{paper_id}", summary="教师：更新试卷（含录入标准答案）")
def update_paper(
    paper_id: int,
    data: PaperUpdate,
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """教师更新试卷信息，可用于录入/修改标准答案"""
    paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")

    if not _teacher_can_access(db, current_user, paper):
        raise HTTPException(status_code=403, detail="您没有修改该试卷的权限")

    # 只有出卷教师本人可以修改
    if paper.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="只能修改自己创建的试卷")

    updated_fields = []
    if data.title is not None:
        paper.title = data.title
        updated_fields.append("title")
    if data.total_score is not None:
        paper.total_score = data.total_score
        updated_fields.append("total_score")
    if data.exam_date is not None:
        paper.exam_date = data.exam_date
        updated_fields.append("exam_date")
    if data.answer_key is not None:
        paper.answer_key = data.answer_key
        updated_fields.append("answer_key")
    if data.description is not None:
        paper.description = data.description
        updated_fields.append("description")

    if not updated_fields:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    db.flush()
    return {"message": "试卷更新成功", "updated_fields": updated_fields}


@router.delete("/{paper_id}", summary="教师：删除试卷")
def delete_paper(
    paper_id: int,
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """教师删除试卷（同时删除关联的成绩记录）"""
    paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")

    if not _teacher_can_access(db, current_user, paper):
        raise HTTPException(status_code=403, detail="您没有删除该试卷的权限")

    # 只有出卷教师本人可以删除
    if paper.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="只能删除自己创建的试卷")

    # 删除关联的成绩记录
    score_count = db.query(Score).filter(Score.paper_id == paper_id).count()
    db.query(Score).filter(Score.paper_id == paper_id).delete(synchronize_session=False)

    # 删除试卷
    db.delete(paper)
    db.flush()

    return {
        "message": "试卷删除成功",
        "paper_id": paper_id,
        "deleted_scores": score_count,
    }


# ===================== 工具函数 =====================

def _recalculate_rankings(db: Session, paper_id: int):
    """重新计算某张试卷的班级排名"""
    scores = db.query(Score).filter(
        Score.paper_id == paper_id,
        Score.status == 3
    ).order_by(Score.score.desc()).all()

    for i, s in enumerate(scores, 1):
        s.rank_in_class = i
