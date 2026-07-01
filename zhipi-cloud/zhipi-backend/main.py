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

from config import settings, Base, engine
import models  # 确保所有模型被注册

# 导入路由
from controllers.auth_controller import router as auth_router
from controllers.stats_controller import router as stats_router
from controllers.paper_controller import router as paper_router
from controllers.ocr_controller import router as ocr_router

# ===================== 初始化 FastAPI 应用 =====================
app = FastAPI(
    title="智批云 API",
    description="AI 智能批阅系统后端接口文档",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ===================== CORS 配置（支持内网穿透动态域名）=====================
# 固定允许的 origins（本地开发）
_static_origins = settings.cors_origins_list

# 穿透服务域名模式（natapp / ngrok / frp 等）
_TUNNEL_PATTERNS = [
    r"https?://[a-zA-Z0-9\-]+\.natapp1?\.cc",     # natapp
    r"https?://[a-zA-Z0-9\-]+\.ngrok[\-\w]*\.io", # ngrok v3
    r"https?://[a-zA-Z0-9\-]+\.ngrok\.io",         # ngrok v2
    r"https?://[a-zA-Z0-9\-]+\.loca\.lt",          # localtunnel
    r"https?://[a-zA-Z0-9\-]+\.trycloudflare\.com",# cloudflare tunnel
]

def _is_allowed_origin(origin: str) -> bool:
    if origin in _static_origins:
        return True
    for pattern in _TUNNEL_PATTERNS:
        if re.match(pattern, origin):
            return True
    return False

# 使用动态 CORS 中间件
@app.middleware("http")
async def dynamic_cors_middleware(request: Request, call_next):
    origin = request.headers.get("origin", "")
    allowed = _is_allowed_origin(origin)

    # 处理 OPTIONS 预检请求
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

# ===================== 注册路由 =====================
app.include_router(auth_router)
app.include_router(stats_router)
app.include_router(paper_router)
app.include_router(ocr_router)

# ===================== 静态文件服务 =====================
STATIC_DIR = "static"
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ===================== 健康检查 =====================
@app.get("/health", tags=["系统"])
def health_check():
    return {"status": "ok", "service": "zhipi-cloud-backend"}


# ===================== 生产模式：托管前端 SPA（单端口部署） =====================
FRONTEND_DIST = "frontend_dist"
PRODUCTION_MODE = os.path.exists(FRONTEND_DIST)

if PRODUCTION_MODE:
    import mimetypes

    # 静态资源（JS / CSS / 图片）
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="spa_assets")

    # favicon
    favicon_path = os.path.join(FRONTEND_DIST, "favicon.ico")
    if os.path.exists(favicon_path):
        @app.get("/favicon.ico", include_in_schema=False)
        async def spa_favicon():
            return FileResponse(favicon_path, media_type="image/x-icon")

    # SPA 首页
    @app.get("/", include_in_schema=False)
    async def spa_root():
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

    # SPA 路由回退（所有非 API 路径返回 index.html）
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # 排除 API / docs 等路径 —— 已由上方路由匹配，这里只处理前端路由
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            return FileResponse(file_path, media_type=mime_type)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

    print("🌐 生产模式：单端口运行，前端由 FastAPI 托管")
else:
    @app.get("/", tags=["系统"])
    def root():
        return {
            "message": "智批云后端服务运行正常",
            "docs": "/docs",
            "version": "1.0.0"
        }


# ===================== 应用启动事件 =====================
@app.on_event("startup")
async def startup_event():
    """应用启动时自动创建数据库表（如果不存在）"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表初始化完成")
    except Exception as e:
        print(f"⚠️ 数据库初始化失败（请检查数据库配置）: {e}")


# ===================== 启动入口 =====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )
