"""
Pydantic 数据模型 - 试卷管理模块
智批云后端 - schemas/paper.py
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import date


class PaperCreate(BaseModel):
    """创建试卷 - 包含字段级验证"""
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="试卷标题",
    )
    subject: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="考试科目",
    )
    class_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="班级编号",
    )
    total_score: float = Field(
        default=150.0,
        gt=0,
        le=1000,
        description="试卷总分",
    )
    exam_date: date = Field(
        ...,
        description="考试日期",
    )
    answer_key: Optional[Dict[str, Any]] = Field(
        default=None,
        description="标准答案（题目编号 -> 正确答案）",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="试卷描述/备注",
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("试卷标题不能为空")
        return v.strip()

    @field_validator("exam_date")
    @classmethod
    def exam_date_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("考试日期不能是未来日期")
        return v

    @field_validator("answer_key")
    @classmethod
    def validate_answer_key_format(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is not None:
            for key in v:
                if not isinstance(key, str) or not key.strip():
                    raise ValueError("答案键(题号)必须是非空字符串")
        return v


class PaperUpdate(BaseModel):
    """更新试卷 - 所有字段可选，至少传一个"""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200, description="试卷标题")
    total_score: Optional[float] = Field(default=None, gt=0, le=1000, description="试卷总分")
    exam_date: Optional[date] = Field(default=None, description="考试日期")
    answer_key: Optional[Dict[str, Any]] = Field(default=None, description="标准答案")
    description: Optional[str] = Field(default=None, max_length=500, description="试卷描述/备注")

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError("试卷标题不能为空")
        return v.strip() if v else v

    @field_validator("answer_key")
    @classmethod
    def validate_answer_key_format(cls, v):
        if v is not None:
            for key in v:
                if not isinstance(key, str) or not key.strip():
                    raise ValueError("答案键(题号)必须是非空字符串")
        return v


class PaperResponse(BaseModel):
    paper_id: int
    title: str
    subject: str
    class_id: str
    teacher_id: str
    total_score: float
    exam_date: date
    status: int
    description: Optional[str]
    answer_key: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
