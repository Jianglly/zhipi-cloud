"""
models 包初始化 - 注册所有模型
"""
from .paper import ClassInfo, Teacher
from .user import Student
from .score import Score, Paper

__all__ = ["ClassInfo", "Teacher", "Student", "Score", "Paper"]
