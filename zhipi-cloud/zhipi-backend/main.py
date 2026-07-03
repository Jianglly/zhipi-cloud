"""
智批云后端 - 主应用入口
FastAPI 应用启动入口，注册所有路由
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
import re
import time
import logging
import uuid

from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

from config import settings, Base, engine, limiter
from config.logging_config import setup_logging, get_logger
from config.exceptions import AppException, register_exception_handlers
import models  # 确保所有模型被注册

# 导入路由
from controllers.auth_controller import router as auth_router
from controllers.stats_controller import router as stats_router
from controllers.paper_controller import router as paper_router
from controllers.ocr_controller import router as ocr_router
from controllers.admin_controller import router as admin_router

# ===================== 初始化日志系统 =====================
logger = setup_logging(debug=settings.DEBUG)

# ===================== 初始化 FastAPI 应用 =====================
app = FastAPI(
    title="智批云 API",
    description="AI 智能批阅系统后端接口文档",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ===================== 请求 ID 中间件 =====================
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """为每个请求生成唯一 ID，注入到日志和响应头"""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:12])
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ===================== 请求日志中间件 =====================
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """记录所有请求的入口和出口日志（含耗时监控 P1-#12）"""
    start_time = time.perf_counter()

    response = await call_next(request)

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    status = response.status_code

    if status >= 500:
        logger.error(
            "REQUEST | %s %s | status=%d | elapsed=%.1fms",
            request.method, request.url.path, status, elapsed_ms,
        )
    elif status >= 400:
        logger.warning(
            "REQUEST | %s %s | status=%d | elapsed=%.1fms",
            request.method, request.url.path, status, elapsed_ms,
        )
    else:
        logger.info(
            "REQUEST | %s %s | status=%d | elapsed=%.1fms",
            request.method, request.url.path, status, elapsed_ms,
        )

    return response


# ===================== CORS 配置（支持内网穿透动态域名）=====================
_static_origins = settings.cors_origins_list

_TUNNEL_PATTERNS = [
    r"https?://[a-zA-Z0-9\-]+\.natapp1?\.cc",
    r"https?://[a-zA-Z0-9\-]+\.ngrok[\-\w]*\.io",
    r"https?://[a-zA-Z0-9\-]+\.ngrok\.io",
    r"https?://[a-zA-Z0-9\-]+\.loca\.lt",
    r"https?://[a-zA-Z0-9\-]+\.trycloudflare\.com",
]


def _is_allowed_origin(origin: str) -> bool:
    if origin in _static_origins:
        return True
    for pattern in _TUNNEL_PATTERNS:
        if re.match(pattern, origin):
            return True
    return False


@app.middleware("http")
async def dynamic_cors_middleware(request: Request, call_next):
    origin = request.headers.get("origin", "")
    allowed = _is_allowed_origin(origin)

    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": origin if allowed else "",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "600",
        }
        return JSONResponse(content=None, status_code=200, headers=headers)

    response = await call_next(request)

    if allowed and origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"

    return response


# ===================== API 限流中间件 (P1-#11) =====================
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


# ===================== 限流超限处理器 =====================
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "code": 429,
            "message": "请求过于频繁，请稍后再试",
            "detail": str(exc),
        },
    )


# ===================== 注册全局异常处理器 =====================
register_exception_handlers(app)

# ===================== 注册路由 =====================
app.include_router(auth_router)
app.include_router(stats_router)
app.include_router(paper_router)
app.include_router(ocr_router)
app.include_router(admin_router)

# ===================== 静态文件服务 =====================
STATIC_DIR = "static"
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ===================== 健康检查 =====================
@app.get("/health", tags=["系统"])
def health_check():
    return {"status": "ok", "service": "zhipi-cloud-backend"}


@app.get("/ready", tags=["系统"])
async def readiness_check():
    """就绪检查：验证数据库连接是否正常"""
    try:
        from config.database import engine
        with engine.connect() as conn:
            conn.execute(engine.dialect.do_ping(conn))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error("就绪检查失败: %s", str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "disconnected"},
        )


# ===================== 生产模式：托管前端 SPA（单端口部署） =====================
FRONTEND_DIST = "frontend_dist"
PRODUCTION_MODE = os.path.exists(FRONTEND_DIST)

if PRODUCTION_MODE:
    import mimetypes

    # 修复 Windows 下 StaticFiles 返回错误的 Content-Type
    # 浏览器 <script type="module"> 要求 JS 文件必须是 JavaScript MIME 类型
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("image/svg+xml", ".svg")
    mimetypes.add_type("image/png", ".png")
    mimetypes.add_type("image/jpeg", ".jpg")
    mimetypes.add_type("image/x-icon", ".ico")
    mimetypes.add_type("font/woff2", ".woff2")
    mimetypes.add_type("font/woff", ".woff")

    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="spa_assets")

    favicon_path = os.path.join(FRONTEND_DIST, "favicon.ico")
    if os.path.exists(favicon_path):
        @app.get("/favicon.ico", include_in_schema=False)
        async def spa_favicon():
            return FileResponse(favicon_path, media_type="image/x-icon")

    @app.get("/", include_in_schema=False)
    async def spa_root():
        resp = FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
        # index.html 不缓存，确保浏览器每次都拿到最新的 JS/CSS 文件名引用
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # API 路径不走 SPA fallback，避免尾斜杠差异导致 API 请求被拦截返回 HTML
        if full_path.startswith("api/"):
            return JSONResponse(
                status_code=404,
                content={"detail": f"API endpoint not found: /{full_path}"}
            )
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            resp = FileResponse(file_path, media_type=mime_type)
            # HTML 文件不缓存；带 hash 的静态资源可以长期缓存
            if mime_type == "text/html":
                resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return resp
        # SPA fallback：所有未匹配的路径返回 index.html
        resp = FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp

    logger.info("生产模式：单端口运行，前端由 FastAPI 托管")
else:
    @app.get("/", tags=["系统"])
    def root():
        return {
            "message": "智批云后端服务运行正常",
            "docs": "/docs",
            "version": "1.0.0",
        }


# ===================== 应用启动事件 =====================
@app.on_event("startup")
async def startup_event():
    """应用启动时自动创建数据库表（如果不存在）"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表初始化完成")
    except Exception as e:
        logger.error("数据库初始化失败: %s", str(e), exc_info=True)


# ===================== 应用关闭事件 =====================
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    logger.info("应用正在关闭...")
    try:
        engine.dispose()
        logger.info("数据库连接池已释放")
    except Exception as e:
        logger.error("关闭资源时出错: %s", str(e))


# ===================== 启动入口 =====================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
