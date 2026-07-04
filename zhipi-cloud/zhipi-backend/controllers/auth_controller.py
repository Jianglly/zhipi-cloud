"""
认证控制器 - 登录、获取当前用户信息
智批云后端 - controllers/auth_controller.py
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from config.rate_limit import limiter
from models import Student, Teacher, ClassInfo, Admin, TeacherClass
from services.security_service import verify_password, hash_password, create_access_token, decode_token
from schemas import LoginRequest, LoginResponse, UserInfo, RegisterRequest

router = APIRouter(prefix="/api/auth", tags=["认证"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ===================== 依赖注入：获取当前用户 =====================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> UserInfo:
    """从 JWT token 中获取当前登录用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的身份凭证，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    user_id: str = payload.get("sub")
    role: str = payload.get("role")
    if not user_id or not role:
        raise credentials_exception

    return UserInfo(
        user_id=user_id,
        name=payload.get("name", ""),
        role=role,
        class_id=payload.get("class_id", ""),
        subject=payload.get("subject"),
    )


def require_teacher(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """要求当前用户必须是教师"""
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该操作仅教师可用"
        )
    return current_user


def require_student(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """要求当前用户必须是学生"""
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该操作仅学生可用"
        )
    return current_user


def require_admin(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """要求当前用户必须是管理员"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该操作仅管理员可用"
        )
    return current_user


# ===================== 编号生成工具函数 =====================

SUBJECT_CODE_MAP = {"语文": "1", "数学": "2", "英语": "3"}


def _generate_teacher_id(db: Session, subject: str) -> str:
    """按科目生成新的教师编号：T + 科目码 + 2位序号"""
    code = SUBJECT_CODE_MAP.get(subject)
    if not code:
        raise ValueError(f"无效科目：{subject}")
    prefix = f"T{code}"
    # 查询同科目教师最大序号
    latest = db.query(Teacher.teacher_id)\
        .filter(Teacher.teacher_id.startswith(prefix))\
        .order_by(Teacher.teacher_id.desc()).first()
    if latest:
        try:
            seq = int(latest[0][2:])  # 去掉 T1 前缀
        except ValueError:
            seq = 0
    else:
        seq = 0
    return f"{prefix}{seq + 1:02d}"


def _generate_student_id(db: Session, class_id: str) -> str:
    """按班级生成新的学生编号：S + 班级码 + 2位班内序号"""
    cls = db.query(ClassInfo).filter(ClassInfo.class_id == class_id).first()
    if not cls or cls.class_code is None:
        raise ValueError(f"班级 {class_id} 不存在或缺少 class_code")
    prefix = f"S{cls.class_code}"
    latest = db.query(Student.student_id)\
        .filter(Student.student_id.startswith(prefix))\
        .order_by(Student.student_id.desc()).first()
    if latest:
        try:
            seq = int(latest[0][2:])
        except ValueError:
            seq = 0
    else:
        seq = 0
    return f"{prefix}{seq + 1:02d}"


# ===================== 路由处理 =====================

@router.post("/login", summary="用户登录")
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    """
    统一登录接口
    - role: "student" | "teacher"
    - user_id: 学号 或 教师编号
    - password: 密码
    """
    if body.role == "student":
        user = db.query(Student).filter(Student.student_id == body.user_id).first()
        if not user or not verify_password(body.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="学号或密码错误"
            )
        token_data = {
            "sub": user.student_id,
            "name": user.name,
            "role": "student",
            "class_id": user.class_id,
        }
        return JSONResponse(
            content={
                "access_token": create_access_token(token_data),
                "token_type": "bearer",
                "role": "student",
                "user_id": user.student_id,
                "name": user.name,
                "class_id": user.class_id,
            }
        )

    elif body.role == "teacher":
        user = db.query(Teacher).filter(Teacher.teacher_id == body.user_id).first()
        if not user or not verify_password(body.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="教师编号或密码错误"
            )
        token_data = {
            "sub": user.teacher_id,
            "name": user.name,
            "role": "teacher",
            "class_id": user.class_id,
            "subject": user.subject,
        }
        return JSONResponse(
            content={
                "access_token": create_access_token(token_data),
                "token_type": "bearer",
                "role": "teacher",
                "user_id": user.teacher_id,
                "name": user.name,
                "class_id": user.class_id,
                "subject": user.subject,
            }
        )

    elif body.role == "admin":
        user = db.query(Admin).filter(Admin.admin_id == body.user_id).first()
        if not user or not verify_password(body.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="管理员账号或密码错误"
            )
        token_data = {
            "sub": user.admin_id,
            "name": user.name,
            "role": "admin",
        }
        return JSONResponse(
            content={
                "access_token": create_access_token(token_data),
                "token_type": "bearer",
                "role": "admin",
                "user_id": user.admin_id,
                "name": user.name,
                "class_id": "",
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role 参数无效，应为 student、teacher 或 admin"
        )


@router.get("/me", summary="获取当前登录用户信息")
def get_me(current_user: UserInfo = Depends(get_current_user)):
    return JSONResponse(content=current_user.model_dump())


@router.get("/me/classes", summary="获取当前教师任教班级列表")
def get_teacher_classes(
    current_user: UserInfo = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """教师端获取自己的任教班级列表（含主负责班）"""
    rows = db.query(TeacherClass.class_id).filter(TeacherClass.teacher_id == current_user.user_id).all()
    classes = {r[0] for r in rows}
    t = db.query(Teacher).filter(Teacher.teacher_id == current_user.user_id).first()
    if t and t.class_id:
        classes.add(t.class_id)

    class_list = db.query(ClassInfo).filter(ClassInfo.class_id.in_(classes)).order_by(ClassInfo.class_id).all()
    return JSONResponse(content=[
        {
            "class_id": c.class_id,
            "class_name": c.class_name,
            "grade": c.grade,
            "department": c.department,
        }
        for c in class_list
    ])


# ===================== 注册 =====================

@router.get("/classes", summary="获取班级列表（注册页公开接口）")
def get_public_classes(db: Session = Depends(get_db)):
    """公开接口，无需登录，供注册页下拉选择班级使用"""
    classes = db.query(ClassInfo).order_by(ClassInfo.class_id).all()
    return JSONResponse(content=[
        {
            "class_id": c.class_id,
            "class_name": c.class_name,
            "grade": c.grade,
            "department": c.department,
        }
        for c in classes
    ])


@router.post("/register", summary="用户注册")
@limiter.limit("3/minute")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    """
    统一注册接口 - 系统自动生成编号
    - 学生: 填写姓名、班级、密码，系统生成 S+班级码+序号
    - 教师: 填写姓名、科目、班级(1-3个)、密码，系统生成 T+科目码+序号
    """
    primary_class_id = body.class_ids[0]

    # 1) 校验所有班级是否存在
    classes = db.query(ClassInfo).filter(ClassInfo.class_id.in_(body.class_ids)).all()
    if len(classes) != len(body.class_ids):
        found_ids = {c.class_id for c in classes}
        missing = [c for c in body.class_ids if c not in found_ids]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"班级不存在：{', '.join(missing)}",
        )

    if body.role == "student":
        # 生成学号
        new_id = _generate_student_id(db, primary_class_id)
        # 再次校验唯一（理论上不会冲突，但保险）
        if db.query(Student).filter(Student.student_id == new_id).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"学号 {new_id} 已存在，请重试",
            )
        new_user = Student(
            student_id=new_id,
            name=body.name,
            class_id=primary_class_id,
            password=hash_password(body.password),
            phone=body.phone,
        )
        pk_field = "student_id"
    else:
        # 教师：校验班级数量
        if len(body.class_ids) > 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="教师最多任教 3 个班级",
            )
        # 生成教师编号
        new_id = _generate_teacher_id(db, body.subject)
        if db.query(Teacher).filter(Teacher.teacher_id == new_id).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"教师编号 {new_id} 已存在，请重试",
            )
        new_user = Teacher(
            teacher_id=new_id,
            name=body.name,
            class_id=primary_class_id,
            subject=body.subject,
            password=hash_password(body.password),
            phone=body.phone,
            task=0,
        )
        pk_field = "teacher_id"

    db.add(new_user)
    db.flush()

    # 教师需要写入 teacher_class 映射表
    if body.role == "teacher":
        for cid in body.class_ids:
            db.add(TeacherClass(teacher_id=new_id, class_id=cid))

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "注册成功，请登录",
            "user_id": getattr(new_user, pk_field),
            "name": new_user.name,
            "role": body.role,
            "class_id": primary_class_id,
            "class_ids": body.class_ids,
        }
    )
