"""
models 包初始化 - 注册所有模型
"""
from .paper import ClassInfo, Teacher, TeacherClass
from .user import Student
from .score import Score, Paper
from .admin import Admin

__all__ = ["ClassInfo", "Teacher", "TeacherClass", "Student", "Score", "Paper", "Admin"]
