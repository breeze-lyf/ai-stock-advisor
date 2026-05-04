# JSON 日志格式化器 (JSON Log Formatter)
# 职责：将日志输出格式化为结构化JSON，便于Loki解析和检索

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional

from app.utils.time import utc_now_naive


class JSONFormatter(logging.Formatter):
    """结构化JSON日志格式化器"""

    def __init__(self, service_name: str = "ai-stock-advisor", environment: str = "production"):
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": utc_now_naive().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "environment": self.environment,
        }

        log_data["file"] = record.filename
        log_data["line"] = record.lineno
        log_data["function"] = record.funcName

        standard_attrs = {
            'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
            'funcName', 'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'msg', 'name', 'pathname', 'process', 'processName',
            'relativeCreated', 'stack_info', 'thread', 'threadName'
        }

        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith('_'):
                log_data[key] = value

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            log_data["exception_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None

        return json.dumps(log_data, ensure_ascii=False, default=str)


class StandardFormatter(logging.Formatter):
    """标准文本格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        base = f"{self.formatTime(record)} - {record.name} - {record.levelname} - {record.getMessage()}"

        extras = []
        for attr in ["request_id", "user_id", "duration_ms", "status_code", "method", "path", "ticker"]:
            if hasattr(record, attr):
                extras.append(f"{attr}={getattr(record, attr)}")

        if extras:
            base += f" [{', '.join(extras)}]"

        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"

        return base


def setup_logging(
    log_format: str = "json",
    log_level: str = "INFO",
    service_name: str = "ai-stock-advisor",
    environment: str = "production",
    log_file: str = "app.log",
    max_bytes: int = 50 * 1024 * 1024,   # 50 MB per file
    backup_count: int = 5,                 # keep 5 rotated files
) -> logging.Logger:
    """
    配置日志系统

    策略：
    - 控制台 (stderr): dev 模式输出 INFO+（文本），prod 仅 WARNING+
    - 文件 (app.log): 所有 INFO+ 日志，使用 RotatingFileHandler 自动轮转
    - 文件 (ai_calls.log): AI 调用专用日志，同样轮转
    """
    is_dev = environment.lower() == "development"

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.handlers.clear()

    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    json_formatter = JSONFormatter(service_name, environment)
    text_formatter = StandardFormatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S"
    )

    # ── 控制台 ─────────────────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO if is_dev else logging.WARNING)
    console_handler.setFormatter(text_formatter)
    root_logger.addHandler(console_handler)

    # ── 主文件：INFO+ JSON，自动轮转 ───────────────────────────────────
    try:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        root_logger.warning(f"Failed to setup file logging: {e}")

    # ── AI 调用专用日志文件，同样轮转 ──────────────────────────────────
    ai_log_path = os.path.join(log_dir or ".", "ai_calls.log")
    try:
        ai_file_handler = RotatingFileHandler(
            ai_log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        ai_file_handler.setLevel(logging.DEBUG)
        ai_file_handler.setFormatter(json_formatter)
        ai_logger = logging.getLogger("app.ai_calls")
        ai_logger.addHandler(ai_file_handler)
        ai_logger.propagate = False
    except Exception as e:
        root_logger.warning(f"Failed to setup AI call logging: {e}")

    # ── 第三方库降噪 ──────────────────────────────────────────────────
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    # yfinance 的 ERROR 级别已经够多了，只保留 WARNING 及以上
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    # 调度器心跳日志只写文件，不打终端
    logging.getLogger("app.services.scheduler_jobs").setLevel(logging.INFO)
    logging.getLogger("app.services.market_data_fetcher").setLevel(logging.INFO)

    return logging.getLogger("api_logger")


class LogContext:
    """日志上下文管理器，用于添加额外字段"""

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
