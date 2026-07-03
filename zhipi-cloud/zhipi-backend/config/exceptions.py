"""
自定义异常类与全局异常处理器
智批云后端 - config/exceptions.py

定义类型化的异常层次结构，提供统一的错误响应格式。
所有业务异常应继承 AppException，而非直接使用 HTTPException。
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from typing import Any, Dict, List, Optional
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


# ===================== 异常类层次结构 =====================

class AppException(Exception):
    """应用级异常基类 — 所有业务异常应继承此类"""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        detail: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


class NotFoundError(AppException):
    """资源未找到"""

    def __init__(self, resource: str, identifier: Any = ""):
        super().__init__(
            message=f"{resource} 不存在" + (f": {identifier}" if identifier else ""),
            code="NOT_FOUND",
            status_code=404,
        )


class ValidationError(AppException):
    """输入数据验证失败"""

    def __init__(self, message: str = "输入数据验证失败", errors: Optional[List[Dict[str, str]]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            detail={"errors": errors or []},
        )


class UnauthorizedError(AppException):
    """未认证"""

    def __init__(self, message: str = "请先登录"):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
        )


class ForbiddenError(AppException):
    """无权限"""

    def __init__(self, message: str = "无权限执行此操作"):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
        )


class ConflictError(AppException):
    """资源冲突（如重复创建）"""

    def __init__(self, message: str = "资源已存在"):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
        )


class ExternalServiceError(AppException):
    """外部服务调用失败（如百度OCR）"""

    def __init__(self, service: str, message: str = ""):
        super().__init__(
            message=f"{service} 服务异常: {message}" if message else f"{service} 服务暂不可用",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            detail={"service": service},
        )


# ===================== 全局异常处理器 =====================

def register_exception_handlers(app: FastAPI):
    """向 FastAPI 应用注册所有全局异常处理器"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """处理所有应用级异常"""
        logger.warning(
            "业务异常 | %s %s | code=%s status=%d | %s",
            request.method,
            request.url.path,
            exc.code,
            exc.status_code,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
                "request_id": getattr(request.state, "request_id", "-"),
            },
        )

    @app.exception_handler(status.HTTP_401_UNAUTHORIZED)
    async def unauthorized_handler(request: Request, exc: Exception):
        """FastAPI 原生 401 异常"""
        return JSONResponse(
            status_code=401,
            content={
                "code": "UNAUTHORIZED",
                "message": str(exc.detail) if hasattr(exc, "detail") else "请先登录",
                "request_id": getattr(request.state, "request_id", "-"),
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """兜底：捕获所有未处理的异常，返回 500"""
        logger.error(
            "未处理异常 | %s %s | %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                # 开发模式返回真实错误，生产模式返回泛化错误
                "message": str(exc) if settings.DEBUG else "服务器内部错误，请稍后重试",
                "type": type(exc).__name__ if settings.DEBUG else None,
                "request_id": getattr(request.state, "request_id", "-"),
            },
        )
