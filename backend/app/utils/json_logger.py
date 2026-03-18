# JSON 日志格式化器 (JSON Log Formatter)
# 职责：将日志输出格式化为结构化JSON，便于Loki解析和检索

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """
    结构化JSON日志格式化器
    
    输出示例:
    {
        "timestamp": "2024-01-15T10:30:45.123456+08:00",
        "level": "INFO",
        "logger": "api_logger",
        "message": "Request completed",
        "request_id": "abc-123",
        "user_id": "user-456",
        "duration_ms": 45.67,
        "status_code": 200,
        "method": "GET",
        "path": "/api/v1/portfolio",
        "service": "ai-stock-advisor",
        "environment": "production"
    }
    """
    
    def __init__(self, service_name: str = "ai-stock-advisor", environment: str = "production"):
        super().__init__()
        self.service_name = service_name
        self.environment = environment
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为JSON字符串"""
        
        # 基础字段
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "environment": self.environment,
        }
        
        # 添加位置信息 (文件、行号、函数名)
        log_data["file"] = record.filename
        log_data["line"] = record.lineno
        log_data["function"] = record.funcName
        
        # 如果有额外字段，添加到日志中
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "ticker"):
            log_data["ticker"] = record.ticker
        if hasattr(record, "error_type"):
            log_data["error_type"] = record.error_type
        if hasattr(record, "stack_trace"):
            log_data["stack_trace"] = record.stack_trace
        
        # 异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            log_data["exception_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class StandardFormatter(logging.Formatter):
    """
    标准文本格式化器 (用于开发环境)
    
    输出示例:
    2024-01-15 10:30:45 - api_logger - INFO - Request completed [user_id=user-456]
    """
    
    def format(self, record: logging.LogRecord) -> str:
        # 基础格式
        base = f"{self.formatTime(record)} - {record.name} - {record.levelname} - {record.getMessage()}"
        
        # 添加额外字段
        extras = []
        for attr in ["request_id", "user_id", "duration_ms", "status_code", "method", "path", "ticker"]:
            if hasattr(record, attr):
                extras.append(f"{attr}={getattr(record, attr)}")
        
        if extras:
            base += f" [{', '.join(extras)}]"
        
        # 异常信息
        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"
        
        return base


def setup_logging(
    log_format: str = "json",
    log_level: str = "INFO",
    service_name: str = "ai-stock-advisor",
    environment: str = "production",
    log_file: str = "app.log"
) -> logging.Logger:
    """
    配置日志系统
    
    Args:
        log_format: 日志格式 ("json" 或 "standard")
        log_level: 日志级别
        service_name: 服务名称
        environment: 环境标识
        log_file: 日志文件路径
    
    Returns:
        配置好的Logger实例
    """
    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 选择格式化器
    if log_format.lower() == "json":
        formatter = JSONFormatter(service_name, environment)
    else:
        formatter = StandardFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        root_logger.warning(f"Failed to setup file logging: {e}")
    
    # 降低第三方库的日志级别
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    return logging.getLogger("api_logger")


class LogContext:
    """
    日志上下文管理器，用于添加额外字段
    
    Usage:
        with LogContext(logger, user_id="user-123", request_id="req-456"):
            logger.info("Processing request")
    """
    
    def __init__(self, logger: logging.Logger, **kwargs):
        self.logger = logger
        self.extra = kwargs
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def info(self, msg: str, **kwargs):
        self._log(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        self._log(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        self._log(logging.ERROR, msg, **kwargs)
    
    def debug(self, msg: str, **kwargs):
        self._log(logging.DEBUG, msg, **kwargs)
    
    def _log(self, level: int, msg: str, **kwargs):
        extra = {**self.extra, **kwargs}
        self.logger.log(level, msg, extra=extra)
