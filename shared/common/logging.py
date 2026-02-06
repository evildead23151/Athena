"""
ATHENA Structured Logging
JSON-formatted immutable audit logging
"""
import os
import json
import logging
import sys
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": getattr(record, "service", "unknown"),
            "message": record.getMessage(),
            "logger": record.name
        }
        
        # Add extra fields
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "action"):
            log_entry["action"] = record.action
        if hasattr(record, "before_state"):
            log_entry["before_state"] = record.before_state
        if hasattr(record, "after_state"):
            log_entry["after_state"] = record.after_state
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


class AthenaLogger:
    """Structured logger for ATHENA services"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(getattr(logging, LOG_LEVEL))
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # Add JSON handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with extra fields"""
        extra = {"service": self.service_name}
        extra.update(kwargs)
        self.logger.log(level, message, extra=extra)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log(logging.ERROR, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def audit(
        self,
        action: str,
        user_id: Optional[str] = None,
        before_state: Any = None,
        after_state: Any = None,
        resource_type: str = None,
        resource_id: str = None,
        **kwargs
    ):
        """Log audit event for state changes"""
        self._log(
            logging.INFO,
            f"AUDIT: {action}",
            action=action,
            user_id=user_id,
            before_state=before_state,
            after_state=after_state,
            resource_type=resource_type,
            resource_id=resource_id,
            correlation_id=str(uuid4()),
            extra_data=kwargs
        )


# Logger registry
_loggers: dict = {}


def get_logger(service_name: str) -> AthenaLogger:
    """Get or create logger for service"""
    if service_name not in _loggers:
        _loggers[service_name] = AthenaLogger(service_name)
    return _loggers[service_name]
