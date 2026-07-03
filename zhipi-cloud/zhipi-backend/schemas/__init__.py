"""
Pydantic 数据模型集中导出
智批云后端 - schemas/__init__.py

使用方式：
    from schemas import LoginRequest, LoginResponse, UserInfo, PaperCreate
"""
from schemas.auth import LoginRequest, LoginResponse, UserInfo, RegisterRequest, RegisterResponse
from schemas.paper import PaperCreate, PaperUpdate, PaperResponse
from schemas.admin import (
    TeacherCreate, TeacherUpdate, TeacherAdminView,
    StudentCreate, StudentUpdate, StudentAdminView,
    ClassCreate, ClassUpdate, ClassAdminView,
    ResetPassword, OperationLogView,
)

__all__ = [
    "LoginRequest",
    "LoginResponse",
    "UserInfo",
    "RegisterRequest",
    "RegisterResponse",
    "PaperCreate",
    "PaperUpdate",
    "PaperResponse",
    "TeacherCreate", "TeacherUpdate", "TeacherAdminView",
    "StudentCreate", "StudentUpdate", "StudentAdminView",
    "ClassCreate", "ClassUpdate", "ClassAdminView",
    "ResetPassword", "OperationLogView",
]
