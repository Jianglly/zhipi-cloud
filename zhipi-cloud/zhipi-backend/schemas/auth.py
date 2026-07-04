"""
Pydantic 数据模型 - 认证模块
智批云后端 - schemas/auth.py
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, List


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
    """注册请求 - 系统自动生成编号"""
    role: Literal["student", "teacher"] = Field(
        ..., description="角色：student(学生) 或 teacher(教师)",
    )
    name: str = Field(
        ..., min_length=2, max_length=15,
        description="真实姓名",
        examples=["张三"],
    )
    class_ids: List[str] = Field(
        ..., min_length=1, max_length=3,
        description="任教/所在班级编号列表，学生1个，教师最多3个",
    )
    subject: Optional[str] = Field(
        None, max_length=15,
        description="任教科目（仅教师必填：语文/数学/英语）",
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

    @field_validator("class_ids")
    @classmethod
    def class_ids_validate(cls, v: List[str], info) -> List[str]:
        cleaned = [c.strip() for c in v if c.strip()]
        if not cleaned:
            raise ValueError("至少选择一个班级")
        if info.data.get("role") == "student" and len(cleaned) > 1:
            raise ValueError("学生只能选择一个班级")
        if info.data.get("role") == "teacher" and len(cleaned) > 3:
            raise ValueError("教师最多选择三个班级")
        return cleaned

    @field_validator("subject")
    @classmethod
    def teacher_subject_validate(cls, v, info):
        """教师注册时 subject 必填且必须是三科之一"""
        if info.data.get("role") == "teacher":
            if not v:
                raise ValueError("教师注册必须填写任教科目")
            if v not in ("语文", "数学", "英语"):
                raise ValueError("教师科目只能是语文/数学/英语")
        return v


class RegisterResponse(BaseModel):
    """注册成功响应"""
    message: str
    user_id: str
    name: str
    role: str
    class_id: str
    class_ids: List[str]
