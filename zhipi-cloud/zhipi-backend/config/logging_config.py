"""
结构化日志配置
智批云后端 - config/logging_config.py

提供请求级别的结构化 JSON 日志，支持：
- 请求 ID 自动生成和传播
- 按日志级别分离输出
- 开发模式下的彩色控制台输出
- 生产模式下的 JSON 格式输出
"""
import logging
import logging.config
import sys
import json
import uuid
from datetime import datetime, timezone
from typing import Optional


class RequestIdFilter(logging.Filter):
    """注入 request_id 到每条日志记录"""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = getattr(record, "request_id", "-")
        return True


class JsonFormatter(logging.Formatter):
    """JSON 格式的日志格式化器（生产环境用）"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "module": record.module,
            "funcName": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }
        return json.dumps(log_entry, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """开发环境彩色控制台格式化器"""

    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        record.request_id_str = getattr(record, "request_id", "-")[:8]
        return super().format(record)


def setup_logging(debug: bool = True, log_level: str = "INFO"):
    """
    配置全局日志系统

    Args:
        debug: 是否开发模式（控制台彩色输出）
        log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
    """
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {
                "()": RequestIdFilter,
            },
        },
        "formatters": {
            "json": {
                "()": JsonFormatter,
            },
            "colored": {
                "()": ColoredFormatter,
                "format": "%(asctime)s | %(levelname)s | [%(request_id_str)s] %(name)s:%(funcName)s:%(lineno)d | %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "colored" if debug else "json",
                "filters": ["request_id"],
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "INFO" if debug and log_level == "DEBUG" else "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(config)

    logger = logging.getLogger(__name__)
    logger.info("日志系统初始化完成 | debug=%s level=%s", debug, log_level)

    return logger


def get_logger(name: str) -> logging.Logger:
    """获取命名日志记录器（推荐在模块中使用此函数）"""
    return logging.getLogger(name)
