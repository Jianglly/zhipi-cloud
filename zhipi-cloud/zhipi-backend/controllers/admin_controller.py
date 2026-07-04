"""
管理员控制器 - 系统管理、用户管理、日志审计
智批云后端 - controllers/admin_controller.py
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from config.database import get_db
from models import Student, Teacher, ClassInfo, Paper, Score, Admin, TeacherClass
from schemas import (
    TeacherCreate, TeacherUpdate,
    StudentCreate, StudentUpdate,
    ClassCreate, ClassUpdate,
    ResetPassword,
)
from controllers.auth_controller import require_admin, _generate_teacher_id, _generate_student_id
from services.security_service import hash_password

router = APIRouter(prefix="/api/admin", tags=["管理员"])


# ===================== 系统总览 =====================

@router.get("/overview", summary="系统总览统计")
def get_overview(
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """系统全局统计数据（对应 v_system_stats 视图）"""
    total_students = db.query(func.count(Student.student_id)).scalar() or 0
    total_teachers = db.query(func.count(Teacher.teacher_id)).scalar() or 0
    total_papers = db.query(func.count(Paper.paper_id)).scalar() or 0
    total_scores = db.query(func.count(Score.score_id)).scalar() or 0
    completed_scores = db.query(func.count(Score.score_id)).filter(Score.status == 3).scalar() or 0
    pending_scores = db.query(func.count(Score.score_id)).filter(Score.status.in_([0, 1, 2])).scalar() or 0
    total_classes = db.query(func.count(ClassInfo.class_id)).scalar() or 0

    # 试卷状态分布
    status_dist = (
        db.query(Paper.status, func.count(Paper.paper_id))
        .group_by(Paper.status)
        .all()
    )
    status_map = {0: "草稿", 1: "已发布", 2: "批阅中", 3: "已完成"}
    paper_status_dist = [
        {"status": status_map.get(s, str(s)), "count": c}
        for s, c in status_dist
    ]

    # 科目分布
    subject_dist = (
        db.query(Paper.subject, func.count(Paper.paper_id))
        .group_by(Paper.subject)
        .all()
    )
    paper_subject_dist = [
        {"subject": s, "count": c} for s, c in subject_dist
    ]

    return JSONResponse(content={
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_classes": total_classes,
        "total_papers": total_papers,
        "total_scores": total_scores,
        "completed_scores": completed_scores,
        "pending_scores": pending_scores,
        "paper_status_dist": paper_status_dist,
        "paper_subject_dist": paper_subject_dist,
    })


# ===================== 教师管理 =====================

@router.get("/teachers", summary="获取教师列表")
def list_teachers(
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
    keyword: str = Query(default="", description="搜索姓名或编号"),
):
    query = db.query(Teacher)
    if keyword:
        query = query.filter(
            Teacher.name.contains(keyword) | Teacher.teacher_id.contains(keyword)
        )
    teachers = query.order_by(Teacher.teacher_id).all()
    result = []
    for t in teachers:
        class_ids = [r[0] for r in db.query(TeacherClass.class_id).filter(TeacherClass.teacher_id == t.teacher_id).all()]
        result.append({
            "teacher_id": t.teacher_id,
            "name": t.name,
            "class_id": t.class_id,
            "class_ids": class_ids,
            "subject": t.subject,
            "task": t.task,
            "phone": t.phone,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return JSONResponse(content=result)


@router.post("/teachers", summary="新增教师")
def create_teacher(
    body: TeacherCreate,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    # 自动生成编号（如果未指定）
    teacher_id = body.teacher_id
    if not teacher_id:
        teacher_id = _generate_teacher_id(db, body.subject)

    if db.query(Teacher).filter(Teacher.teacher_id == teacher_id).first():
        raise HTTPException(400, detail=f"教师编号 {teacher_id} 已存在")
    if not db.query(ClassInfo).filter(ClassInfo.class_id == body.class_id).first():
        raise HTTPException(400, detail=f"班级 {body.class_id} 不存在")

    # 校验任教班级
    class_ids = list(dict.fromkeys([body.class_id] + (body.class_ids or [])))[:3]
    valid_classes = db.query(ClassInfo.class_id).filter(ClassInfo.class_id.in_(class_ids)).count()
    if valid_classes != len(class_ids):
        raise HTTPException(400, detail="存在无效的任教班级")

    teacher = Teacher(
        teacher_id=teacher_id,
        name=body.name,
        class_id=body.class_id,
        subject=body.subject,
        password=hash_password(body.password),
        phone=body.phone,
    )
    db.add(teacher)
    db.flush()

    for cid in class_ids:
        db.add(TeacherClass(teacher_id=teacher.teacher_id, class_id=cid))

    db.commit()
    return JSONResponse(content={"message": "教师创建成功", "teacher_id": teacher.teacher_id})


@router.put("/teachers/{teacher_id}", summary="修改教师信息")
def update_teacher(
    teacher_id: str,
    body: TeacherUpdate,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    teacher = db.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()
    if not teacher:
        raise HTTPException(404, detail="教师不存在")

    if body.class_id and not db.query(ClassInfo).filter(ClassInfo.class_id == body.class_id).first():
        raise HTTPException(400, detail=f"班级 {body.class_id} 不存在")

    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(teacher, k, v)
    db.commit()
    return JSONResponse(content={"message": "修改成功"})


@router.delete("/teachers/{teacher_id}", summary="删除教师")
def delete_teacher(
    teacher_id: str,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    teacher = db.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()
    if not teacher:
        raise HTTPException(404, detail="教师不存在")
    # 检查是否有关联试卷
    paper_count = db.query(func.count(Paper.paper_id)).filter(Paper.teacher_id == teacher_id).scalar()
    if paper_count > 0:
        raise HTTPException(400, detail=f"该教师关联 {paper_count} 张试卷，无法删除")
    db.delete(teacher)
    db.commit()
    return JSONResponse(content={"message": "删除成功"})


@router.post("/teachers/{teacher_id}/reset-password", summary="重置教师密码")
def reset_teacher_password(
    teacher_id: str,
    body: ResetPassword,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    teacher = db.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()
    if not teacher:
        raise HTTPException(404, detail="教师不存在")
    teacher.password = hash_password(body.new_password)
    db.commit()
    return JSONResponse(content={"message": f"密码已重置为 {body.new_password}"})


# ===================== 学生管理 =====================

@router.get("/students", summary="获取学生列表")
def list_students(
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
    class_id: str = Query(default="", description="按班级筛选"),
    keyword: str = Query(default="", description="搜索姓名或学号"),
):
    query = db.query(Student)
    if class_id:
        query = query.filter(Student.class_id == class_id)
    if keyword:
        query = query.filter(
            Student.name.contains(keyword) | Student.student_id.contains(keyword)
        )
    students = query.order_by(Student.class_id, Student.student_id).all()
    return JSONResponse(content=[
        {
            "student_id": s.student_id,
            "name": s.name,
            "class_id": s.class_id,
            "phone": s.phone,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in students
    ])


@router.post("/students", summary="新增学生")
def create_student(
    body: StudentCreate,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    # 自动生成编号（如果未指定）
    student_id = body.student_id
    if not student_id:
        student_id = _generate_student_id(db, body.class_id)

    if db.query(Student).filter(Student.student_id == student_id).first():
        raise HTTPException(400, detail=f"学号 {student_id} 已存在")
    if not db.query(ClassInfo).filter(ClassInfo.class_id == body.class_id).first():
        raise HTTPException(400, detail=f"班级 {body.class_id} 不存在")

    student = Student(
        student_id=student_id,
        name=body.name,
        class_id=body.class_id,
        password=hash_password(body.password),
        phone=body.phone,
    )
    db.add(student)
    db.commit()
    return JSONResponse(content={"message": "学生创建成功", "student_id": student.student_id})


@router.put("/students/{student_id}", summary="修改学生信息")
def update_student(
    student_id: str,
    body: StudentUpdate,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(404, detail="学生不存在")

    if body.class_id and not db.query(ClassInfo).filter(ClassInfo.class_id == body.class_id).first():
        raise HTTPException(400, detail=f"班级 {body.class_id} 不存在")

    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(student, k, v)
    db.commit()
    return JSONResponse(content={"message": "修改成功"})


@router.delete("/students/{student_id}", summary="删除学生")
def delete_student(
    student_id: str,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(404, detail="学生不存在")
    # 检查是否有关联成绩
    score_count = db.query(func.count(Score.score_id)).filter(Score.student_id == student_id).scalar()
    if score_count > 0:
        raise HTTPException(400, detail=f"该学生关联 {score_count} 条成绩记录，无法删除")
    db.delete(student)
    db.commit()
    return JSONResponse(content={"message": "删除成功"})


@router.post("/students/{student_id}/reset-password", summary="重置学生密码")
def reset_student_password(
    student_id: str,
    body: ResetPassword,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(404, detail="学生不存在")
    student.password = hash_password(body.new_password)
    db.commit()
    return JSONResponse(content={"message": f"密码已重置为 {body.new_password}"})


# ===================== 班级管理 =====================

@router.get("/classes", summary="获取班级列表")
def list_classes(
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    classes = db.query(ClassInfo).order_by(ClassInfo.class_id).all()
    result = []
    for c in classes:
        student_count = db.query(func.count(Student.student_id)).filter(Student.class_id == c.class_id).scalar()
        teacher_count = db.query(func.count(TeacherClass.teacher_id)).filter(TeacherClass.class_id == c.class_id).scalar()
        result.append({
            "class_id": c.class_id,
            "class_name": c.class_name,
            "grade": c.grade,
            "department": c.department,
            "student_count": student_count,
            "teacher_count": teacher_count,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return JSONResponse(content=result)


@router.post("/classes", summary="新增班级")
def create_class(
    body: ClassCreate,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(ClassInfo).filter(ClassInfo.class_id == body.class_id).first():
        raise HTTPException(400, detail=f"班级编号 {body.class_id} 已存在")

    cls = ClassInfo(
        class_id=body.class_id,
        class_name=body.class_name,
        grade=body.grade,
        department=body.department,
    )
    db.add(cls)
    db.commit()
    return JSONResponse(content={"message": "班级创建成功", "class_id": cls.class_id})


@router.put("/classes/{class_id}", summary="修改班级信息")
def update_class(
    class_id: str,
    body: ClassUpdate,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    cls = db.query(ClassInfo).filter(ClassInfo.class_id == class_id).first()
    if not cls:
        raise HTTPException(404, detail="班级不存在")

    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(cls, k, v)
    db.commit()
    return JSONResponse(content={"message": "修改成功"})


@router.delete("/classes/{class_id}", summary="删除班级")
def delete_class(
    class_id: str,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    cls = db.query(ClassInfo).filter(ClassInfo.class_id == class_id).first()
    if not cls:
        raise HTTPException(404, detail="班级不存在")
    student_count = db.query(func.count(Student.student_id)).filter(Student.class_id == class_id).scalar()
    teacher_count = db.query(func.count(TeacherClass.teacher_id)).filter(TeacherClass.class_id == class_id).scalar()
    if student_count > 0 or teacher_count > 0:
        raise HTTPException(400, detail=f"该班级仍有 {student_count} 名学生和 {teacher_count} 名教师，无法删除")
    db.delete(cls)
    db.commit()
    return JSONResponse(content={"message": "删除成功"})


# ===================== 试卷总览 =====================

@router.get("/papers", summary="获取所有试卷列表")
def list_all_papers(
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
    subject: str = Query(default="", description="按科目筛选"),
    status_filter: int = Query(default=-1, description="按状态筛选(-1=全部)"),
):
    query = db.query(Paper)
    if subject:
        query = query.filter(Paper.subject == subject)
    if status_filter >= 0:
        query = query.filter(Paper.status == status_filter)

    papers = query.order_by(Paper.created_at.desc()).all()
    status_map = {0: "草稿", 1: "已发布", 2: "批阅中", 3: "已完成"}
    result = []
    for p in papers:
        score_count = db.query(func.count(Score.score_id)).filter(Score.paper_id == p.paper_id).scalar()
        result.append({
            "paper_id": p.paper_id,
            "title": p.title,
            "subject": p.subject,
            "class_id": p.class_id,
            "teacher_id": p.teacher_id,
            "teacher_name": p.teacher.name if p.teacher else "",
            "total_score": float(p.total_score),
            "exam_date": p.exam_date.isoformat() if p.exam_date else None,
            "status": p.status,
            "status_text": status_map.get(p.status, str(p.status)),
            "score_count": score_count,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
    return JSONResponse(content=result)


# ===================== 成绩总览 =====================

@router.get("/scores", summary="获取全校成绩列表")
def list_all_scores(
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
    class_id: str = Query(default="", description="按班级筛选"),
    subject: str = Query(default="", description="按科目筛选"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    query = db.query(Score).filter(Score.status == 3)  # 只看已完成的
    if class_id:
        query = query.filter(Score.class_id == class_id)
    if subject:
        query = query.filter(Score.subject == subject)

    total = query.count()
    scores = query.order_by(Score.score.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return JSONResponse(content={
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "score_id": s.score_id,
                "student_id": s.student_id,
                "name": s.name,
                "class_id": s.class_id,
                "subject": s.subject,
                "score": float(s.score),
                "rank_in_class": s.rank_in_class,
                "rank_in_all": s.rank_in_all,
                "exam_date": s.exam_date.isoformat() if s.exam_date else None,
                "ai_score": float(s.ai_score) if s.ai_score else None,
                "manual_score": float(s.manual_score) if s.manual_score else None,
            }
            for s in scores
        ],
    })


# ===================== 操作日志 =====================

@router.get("/logs", summary="查询操作日志")
def list_logs(
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: str = Query(default="", description="按用户ID筛选"),
    module: str = Query(default="", description="按模块筛选"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    """查询系统操作日志（operation_log 表）"""
    sql = "SELECT * FROM operation_log WHERE 1=1"
    params = {}

    if user_id:
        sql += " AND user_id = :user_id"
        params["user_id"] = user_id
    if module:
        sql += " AND module = :module"
        params["module"] = module

    # 总数
    count_sql = f"SELECT COUNT(*) FROM ({sql}) AS cnt"
    total = db.execute(text(count_sql), params).scalar()

    # 分页
    sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size

    rows = db.execute(text(sql), params).fetchall()

    user_type_map = {0: "学生", 1: "教师", 2: "管理员"}
    items = []
    for r in rows:
        items.append({
            "log_id": r.log_id,
            "user_id": r.user_id,
            "user_type": r.user_type,
            "user_type_text": user_type_map.get(r.user_type, str(r.user_type)),
            "action": r.action,
            "module": r.module,
            "ip_address": r.ip_address,
            "detail": r.detail,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return JSONResponse(content={
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    })
