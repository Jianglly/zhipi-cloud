"""
应用配置管理
智批云后端 - config/settings.py
使用 pydantic-settings 从 .env 文件读取配置，启动时验证，缺少必要配置则快速失败
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "zhipi_cloud"

    # JWT 配置
    JWT_SECRET_KEY: str = ""          # 生产环境必须通过环境变量设置
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    @property
    def jwt_secret_key(self) -> str:
        """确保 JWT 密钥在生产环境不为空"""
        key = self.JWT_SECRET_KEY
        if not key or key == "dev_secret_key_change_in_production":
            if not self.DEBUG:
                raise ValueError(
                    "JWT_SECRET_KEY 未设置！生产环境必须通过环境变量或 .env 文件设置安全的密钥。"
                    "运行: python -c \"import secrets; print(secrets.token_urlsafe(32))\" 生成一个"
                )
            key = "dev_secret_key_change_in_production"
        return key

    # 应用配置
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # CORS 配置
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # 百度OCR配置
    BAIDU_OCR_API_KEY: str = ""
    BAIDU_OCR_SECRET_KEY: str = ""

    # LLM 大题批改配置（OpenAI 兼容接口，默认 DeepSeek）
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()
