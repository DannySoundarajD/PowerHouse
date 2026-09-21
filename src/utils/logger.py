"""
Logging configuration for Sentinel AI Workbench.
Supports both JSON-Lines and text formats for audit-friendly logging.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .constants import LOGS_DIR, LOG_LEVEL, LOG_FORMAT


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName",
                "relativeCreated", "thread", "threadName", "exc_info",
                "exc_text", "stack_info"
            ]:
                log_data[key] = value
        
        return json.dumps(log_data)


def setup_logger(
    name: str = "sentinel",
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
    format_type: Optional[str] = None,
) -> logging.Logger:
    """
    Setup logger with console and file handlers.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (auto-generated if None)
        format_type: "json" or "text"
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Set level
    log_level = getattr(logging, (level or LOG_LEVEL).upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Determine format
    use_json = (format_type or LOG_FORMAT).lower() == "json"
    
    # Console handler (always text for readability)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = LOGS_DIR / f"sentinel-{timestamp}.log"
    
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    
    if use_json:
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str = "sentinel") -> logging.Logger:
    """
    Get existing logger or create new one.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        setup_logger(name)
    
    return logger


# Create default logger on module import
_default_logger = setup_logger()
