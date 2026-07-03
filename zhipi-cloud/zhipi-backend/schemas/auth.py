"""
Pydantic 数据模型 - 认证模块
智批云后端 - schemas/auth.py
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal


class LoginRequest(BaseModel):
    """登录请求 - 包含字段级验证约束"""
    user_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="学号或教师编号",
        examples=["2414100311"],
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="登录密码",
    )
    role: Literal["student", "teacher", "admin"] = Field(
        ...,
        description="角色：student(学生) / teacher(教师) / admin(管理员)",
    )

    @field_validator("user_id")
    @classmethod
    def user_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("user_id 不能为空")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("密码不能为空")
        return v


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


# ===================== 注册 =====================

class RegisterRequest(BaseModel):
    """注册请求"""
    role: Literal["student", "teacher"] = Field(
        ..., description="角色：student(学生) 或 teacher(教师)",
    )
    user_id: str = Field(
        ..., min_length=2, max_length=15,
        description="学号或教师编号",
        examples=["2414100311", "T008"],
    )
    name: str = Field(
        ..., min_length=2, max_length=15,
        description="真实姓名",
        examples=["张三"],
    )
    class_id: str = Field(
        ..., min_length=1, max_length=20,
        description="班级编号（需在 class 表中存在）",
    )
    subject: Optional[str] = Field(
        None, max_length=15,
        description="任教科目（仅教师必填）",
    )
    password: str = Field(
        ..., min_length=6, max_length=128,
        description="登录密码（至少6位）",
    )
    confirm_password: str = Field(
        ..., min_length=6, max_length=128,
        description="确认密码（须与 password 一致）",
    )
    phone: Optional[str] = Field(
        None, max_length=15,
        description="联系电话（可选）",
    )

    @field_validator("user_id")
    @classmethod
    def user_id_clean(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("编号不能为空")
        return v

    @field_validator("name")
    @classmethod
    def name_clean(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("姓名不能为空")
        return v

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("密码不能为空")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("两次输入的密码不一致")
        return v

    @field_validator("subject")
    @classmethod
    def teacher_must_have_subject(cls, v, info):
        """教师注册时 subject 必填"""
        if info.data.get("role") == "teacher" and not v:
            raise ValueError("教师注册必须填写任教科目")
        return v


class RegisterResponse(BaseModel):
    """注册成功响应"""
    message: str
    user_id: str
    name: str
    role: str
    class_id: str
