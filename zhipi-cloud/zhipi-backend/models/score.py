"""
数据模型：成绩 (Score) 和 试卷 (Paper)
对应数据库表: score, paper
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, DECIMAL, JSON, ForeignKey, SmallInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


class Paper(Base):
    __tablename__ = "paper"

    paper_id = Column(Integer, primary_key=True, autoincrement=True, comment="试卷ID")
    title = Column(String(100), nullable=False, comment="试卷标题")
    subject = Column(String(15), nullable=False, comment="科目")
    class_id = Column(String(20), ForeignKey("class.class_id"), nullable=False, comment="适用班级")
    teacher_id = Column(String(15), ForeignKey("teacher.teacher_id"), nullable=False, comment="出卷教师")
    total_score = Column(DECIMAL(5, 2), nullable=False, default=150, comment="总分")
    exam_date = Column(Date, nullable=False, comment="考试日期")
    status = Column(SmallInteger, nullable=False, default=0, comment="状态:0草稿1发布2批阅中3完成")
    answer_key = Column(JSON, nullable=True, comment="客观题标准答案")
    description = Column(String(500), nullable=True, comment="试卷描述")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    scores = relationship("Score", back_populates="paper")
    teacher = relationship("Teacher", back_populates="papers")


class Score(Base):
    __tablename__ = "score"

    score_id = Column(Integer, primary_key=True, autoincrement=True, comment="成绩ID")
    student_id = Column(String(15), ForeignKey("student.student_id"), nullable=False, comment="学号")
    paper_id = Column(Integer, ForeignKey("paper.paper_id"), nullable=False, comment="试卷ID")
    subject = Column(String(15), nullable=False, comment="科目")
    class_id = Column(String(20), nullable=False, comment="班级")
    name = Column(String(15), nullable=False, comment="学生姓名（冗余）")
    score = Column(DECIMAL(5, 2), nullable=False, default=0, comment="成绩")
    rank_in_class = Column(Integer, nullable=True, comment="班级排名")
    rank_in_all = Column(Integer, nullable=True, comment="全校排名")
    exam_date = Column(Date, nullable=False, comment="考试日期")
    ai_score = Column(DECIMAL(5, 2), nullable=True, comment="AI批阅得分")
    manual_score = Column(DECIMAL(5, 2), nullable=True, comment="教师批阅得分")
    status = Column(SmallInteger, nullable=False, default=0, comment="状态:0待批阅1AI中2待审核3完成")
    answer_image = Column(String(500), nullable=True, comment="答卷图片路径")
    ai_result = Column(JSON, nullable=True, comment="AI批阅结果")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    student = relationship("Student", back_populates="scores")
    paper = relationship("Paper", back_populates="scores")
