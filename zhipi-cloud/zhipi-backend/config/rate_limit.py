"""
API 限流配置 — 使用 slowapi 实现基于 IP 的请求频率限制

智批云后端 - config/rate_limit.py

限流策略：
- 全局默认：200 次/分钟/IP
- 登录接口：5 次/分钟/IP（防暴力破解）
- OCR 接口：10 次/分钟/IP（资源保护）
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
    headers_enabled=True,  # 响应头返回限流状态 (X-RateLimit-*)
)
