"""
数据库连接配置
智批云后端 - config/database.py
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .settings import settings

# 数据库连接URL
DATABASE_URL = (
    f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    f"?charset=utf8mb4"
)

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    pool_size=10,          # 连接池大小
    max_overflow=20,       # 超出pool_size时最多再创建的连接数
    pool_recycle=3600,     # 连接回收时间（秒）
    pool_pre_ping=True,    # 每次获取连接前检测连接是否有效
    echo=settings.DEBUG,   # 开发模式下输出SQL语句
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()


def get_db():
    """
    FastAPI 依赖注入：获取数据库会话

    自动管理事务生命周期：
    - 正常完成：提交事务
    - 发生异常：回滚事务
    - 无论如何：关闭会话，归还连接到连接池
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
