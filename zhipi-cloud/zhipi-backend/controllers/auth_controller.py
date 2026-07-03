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
from models import Student, Teacher, ClassInfo, Admin
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
    统一注册接口
    - role: "student" | "teacher"
    - 学生: user_id=学号, name, class_id, password
    - 教师: user_id=教师编号, name, class_id, subject, password
    """
    # 1) 校验班级是否存在
    cls = db.query(ClassInfo).filter(ClassInfo.class_id == body.class_id).first()
    if not cls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"班级编号 {body.class_id} 不存在，请重新选择",
        )

    # 2) 校验编号是否已被注册
    if body.role == "student":
        existing = db.query(Student).filter(Student.student_id == body.user_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"学号 {body.user_id} 已注册，请直接登录或更换编号",
            )
        # 3) 创建学生
        new_user = Student(
            student_id=body.user_id,
            name=body.name,
            class_id=body.class_id,
            password=hash_password(body.password),
            phone=body.phone,
        )
        pk_field = "student_id"
    else:
        # 教师注册 — subject 由 Pydantic 校验器保证非空
        existing = db.query(Teacher).filter(Teacher.teacher_id == body.user_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"教师编号 {body.user_id} 已注册，请直接登录或更换编号",
            )
        new_user = Teacher(
            teacher_id=body.user_id,
            name=body.name,
            class_id=body.class_id,
            subject=body.subject,
            password=hash_password(body.password),
            phone=body.phone,
            task=0,
        )
        pk_field = "teacher_id"

    db.add(new_user)
    db.flush()

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "注册成功，请登录",
            "user_id": getattr(new_user, pk_field),
            "name": new_user.name,
            "role": body.role,
            "class_id": new_user.class_id,
        }
    )
