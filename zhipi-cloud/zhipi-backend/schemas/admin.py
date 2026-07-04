"""
Pydantic 数据模型 - 管理员模块
智批云后端 - schemas/admin.py
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


# ===================== 教师 CRUD =====================

class TeacherCreate(BaseModel):
    teacher_id: Optional[str] = Field(None, max_length=15, description="教师编号（留空则自动生成）")
    name: str = Field(..., max_length=15, description="姓名")
    class_id: str = Field(..., max_length=20, description="主负责班级编号")
    class_ids: List[str] = Field(default_factory=list, max_length=3, description="任教班级编号列表，最多3个")
    subject: str = Field(..., max_length=15, description="任教科目（语文/数学/英语）")
    password: str = Field(default="123456", min_length=6, description="初始密码")
    phone: Optional[str] = Field(None, max_length=15, description="联系电话")

    @field_validator("subject")
    @classmethod
    def subject_validate(cls, v):
        if v not in ("语文", "数学", "英语"):
            raise ValueError("教师科目只能是语文/数学/英语")
        return v


class TeacherUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=15)
    class_id: Optional[str] = Field(None, max_length=20)
    class_ids: Optional[List[str]] = Field(None, max_length=3, description="任教班级编号列表，最多3个")
    subject: Optional[str] = Field(None, max_length=15)
    phone: Optional[str] = Field(None, max_length=15)


class TeacherAdminView(BaseModel):
    teacher_id: str
    name: str
    class_id: str
    subject: str
    task: int
    phone: Optional[str] = None
    created_at: Optional[datetime] = None


# ===================== 学生 CRUD =====================

class StudentCreate(BaseModel):
    student_id: Optional[str] = Field(None, max_length=15, description="学号（留空则自动生成）")
    name: str = Field(..., max_length=15, description="姓名")
    class_id: str = Field(..., max_length=20, description="班级编号")
    password: str = Field(default="123456", min_length=6, description="初始密码")
    phone: Optional[str] = Field(None, max_length=15, description="联系电话")


class StudentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=15)
    class_id: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=15)


class StudentAdminView(BaseModel):
    student_id: str
    name: str
    class_id: str
    phone: Optional[str] = None
    created_at: Optional[datetime] = None


# ===================== 班级 CRUD =====================

class ClassCreate(BaseModel):
    class_id: str = Field(..., max_length=20, description="班级编号")
    class_name: str = Field(..., max_length=50, description="班级全称")
    grade: str = Field(..., max_length=10, description="年级")
    department: Optional[str] = Field(None, max_length=50, description="院系")


class ClassUpdate(BaseModel):
    class_name: Optional[str] = Field(None, max_length=50)
    grade: Optional[str] = Field(None, max_length=10)
    department: Optional[str] = Field(None, max_length=50)


class ClassAdminView(BaseModel):
    class_id: str
    class_name: str
    grade: str
    department: Optional[str] = None
    student_count: int = 0
    teacher_count: int = 0


# ===================== 重置密码 =====================

class ResetPassword(BaseModel):
    new_password: str = Field(default="123456", min_length=6, description="新密码")


# ===================== 操作日志 =====================

class OperationLogView(BaseModel):
    log_id: int
    user_id: str
    user_type: int
    action: str
    module: str
    ip_address: Optional[str] = None
    detail: Optional[str] = None
    created_at: datetime
