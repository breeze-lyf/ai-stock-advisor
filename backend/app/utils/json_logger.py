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
        
        # 排除标准属性，将所有额外的 (extra) 字段动态添加到 log_data
        # 标准属性列表参考：https://docs.python.org/3/library/logging.html#logrecord-attributes
        standard_attrs = {
            'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
            'funcName', 'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'msg', 'name', 'pathname', 'process', 'processName',
            'relativeCreated', 'stack_info', 'thread', 'threadName'
        }
        
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith('_'):
                log_data[key] = value
        
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

    策略：
    - 控制台 (stderr): 仅显示 WARNING 及以上，使用简洁文本格式，减少终端噪音
    - 文件 (app.log): 所有 INFO+ 日志，保留完整 JSON 格式，供 Loki/Grafana 聚合
    - 文件 (ai_calls.log): AI 调用专用日志，包含完整 prompt 和分段计时
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.handlers.clear()

    json_formatter = JSONFormatter(service_name, environment)
    text_formatter = StandardFormatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S"
    )

    # ── 控制台：仅 WARNING+ 使用简洁文本 ──────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(text_formatter)
    root_logger.addHandler(console_handler)

    # ── 主文件：INFO+ 完整 JSON，供 Loki ────────────────────────────
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        root_logger.warning(f"Failed to setup file logging: {e}")

    # ── AI 调用专用日志文件 ───────────────────────────────────────────
    ai_log_path = os.path.join(os.path.dirname(log_file) or ".", "ai_calls.log")
    try:
        ai_file_handler = logging.FileHandler(ai_log_path, encoding="utf-8")
        ai_file_handler.setLevel(logging.DEBUG)
        ai_file_handler.setFormatter(json_formatter)
        ai_logger = logging.getLogger("app.ai_calls")
        ai_logger.addHandler(ai_file_handler)
        ai_logger.propagate = False  # 不向上传播，避免写入 app.log
    except Exception as e:
        root_logger.warning(f"Failed to setup AI call logging: {e}")

    # ── 第三方库降噪 ──────────────────────────────────────────────────
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    # 调度器心跳日志只写文件，不打终端
    logging.getLogger("app.services.scheduler_jobs").setLevel(logging.INFO)
    logging.getLogger("app.services.market_data_fetcher").setLevel(logging.INFO)

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
