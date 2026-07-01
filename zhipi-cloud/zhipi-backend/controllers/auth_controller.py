"""
认证控制器 - 登录、获取当前用户信息
智批云后端 - controllers/auth_controller.py
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from config.database import get_db
from models import Student, Teacher
from services.security_service import verify_password, create_access_token, decode_token

router = APIRouter(prefix="/api/auth", tags=["认证"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ===================== Pydantic 数据模型 =====================

class LoginRequest(BaseModel):
    user_id: str
    password: str
    role: str  # "student" | "teacher"


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    name: str
    class_id: str


class UserInfo(BaseModel):
    user_id: str
    name: str
    role: str
    class_id: str
    subject: Optional[str] = None


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


# ===================== 路由处理 =====================

@router.post("/login", response_model=LoginResponse, summary="用户登录")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    统一登录接口
    - role: "student" | "teacher"
    - user_id: 学号 或 教师编号
    - password: 密码
    """
    if request.role == "student":
        user = db.query(Student).filter(Student.student_id == request.user_id).first()
        if not user or not verify_password(request.password, user.password):
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
        return LoginResponse(
            access_token=create_access_token(token_data),
            role="student",
            user_id=user.student_id,
            name=user.name,
            class_id=user.class_id,
        )

    elif request.role == "teacher":
        user = db.query(Teacher).filter(Teacher.teacher_id == request.user_id).first()
        if not user or not verify_password(request.password, user.password):
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
        return LoginResponse(
            access_token=create_access_token(token_data),
            role="teacher",
            user_id=user.teacher_id,
            name=user.name,
            class_id=user.class_id,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role 参数无效，应为 student 或 teacher"
        )


@router.get("/me", response_model=UserInfo, summary="获取当前登录用户信息")
def get_me(current_user: UserInfo = Depends(get_current_user)):
    return current_user
