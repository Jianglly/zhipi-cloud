"""
数据模型：学生 (Student)
对应数据库表: student
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


class Student(Base):
    __tablename__ = "student"

    student_id = Column(String(15), primary_key=True, comment="学号")
    name = Column(String(15), nullable=False, comment="学生姓名")
    class_id = Column(String(20), ForeignKey("class.class_id"), nullable=False, comment="班级编号")
    password = Column(String(255), nullable=False, comment="密码（bcrypt加密）")
    phone = Column(String(15), nullable=True, comment="联系电话")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关系
    class_info = relationship("ClassInfo", back_populates="students")
    scores = relationship("Score", back_populates="student")
