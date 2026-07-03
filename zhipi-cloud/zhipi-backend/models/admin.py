"""
数据模型：管理员 (Admin)
对应数据库表: admin
智批云后端 - models/admin.py
"""
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from config.database import Base


class Admin(Base):
    __tablename__ = "admin"

    admin_id = Column(String(15), primary_key=True, comment="管理员编号")
    name = Column(String(15), nullable=False, comment="管理员姓名")
    password = Column(String(255), nullable=False, comment="密码（bcrypt加密）")
    created_at = Column(DateTime, server_default=func.now())
