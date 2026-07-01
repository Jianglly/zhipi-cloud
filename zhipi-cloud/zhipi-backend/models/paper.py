"""
数据模型：教师 (Teacher) 和 班级 (ClassInfo)
对应数据库表: teacher, class
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


class ClassInfo(Base):
    __tablename__ = "class"

    class_id = Column(String(20), primary_key=True, comment="班级编号")
    class_name = Column(String(50), nullable=False, comment="班级全称")
    grade = Column(String(10), nullable=False, comment="年级")
    department = Column(String(50), nullable=True, comment="院系")
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    students = relationship("Student", back_populates="class_info")
    teachers = relationship("Teacher", back_populates="class_info")


class Teacher(Base):
    __tablename__ = "teacher"

    teacher_id = Column(String(15), primary_key=True, comment="教师编号")
    name = Column(String(15), nullable=False, comment="教师姓名")
    class_id = Column(String(20), ForeignKey("class.class_id"), nullable=False, comment="负责班级")
    subject = Column(String(15), nullable=False, comment="任教科目")
    password = Column(String(255), nullable=False, comment="密码（bcrypt加密）")
    task = Column(Integer, nullable=False, default=0, comment="累计批阅任务数")
    phone = Column(String(15), nullable=True, comment="联系电话")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    class_info = relationship("ClassInfo", back_populates="teachers")
    papers = relationship("Paper", back_populates="teacher")
