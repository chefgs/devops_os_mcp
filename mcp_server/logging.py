"""Structured logging with credential redaction for MCP server."""
import asyncio
import contextvars
import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Sensitive patterns to redact from logs
REDACT_PATTERNS = {
    'token', 'authorization', 'auth_secret', 'api_key', 'apikey', 
    'secret', 'password', 'passwd', 'private_key', 'credential',
    'jwt_secret', 'bearer', 'access_token', 'refresh_token',
    'x-api-key', 'x-token', 'x-auth', 'signing_key'
}

# Correlation ID context variable
_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    'correlation_id', default='unknown'
)


class CorrelationContext:
    """Thread-safe and async-safe correlation ID tracking."""

    @staticmethod
    def set(correlation_id: str) -> None:
        """Set the correlation ID for this context."""
        _correlation_id.set(correlation_id)

    @staticmethod
    def get() -> str:
        """Get the current correlation ID."""
        return _correlation_id.get()

    @staticmethod
    def new() -> str:
        """Generate and set a new correlation ID."""
        import uuid
        cid = f"req-{uuid.uuid4().hex[:12]}"
        CorrelationContext.set(cid)
        return cid


class RedactedDict(dict):
    """Dictionary that redacts sensitive values when converted to string."""

    def redact(self, obj: Any, depth: int = 5) -> Any:
        """Recursively redact sensitive values from an object."""
        if depth <= 0:
            return "<depth_limit>"

        if isinstance(obj, dict):
            return {
                k: self._redact_value(k, v, depth)
                for k, v in obj.items()
            }
        elif isinstance(obj, (list, tuple)):
            return type(obj)(
                self._redact_value(None, item, depth)
                for item in obj
            )
        return obj

    def _redact_value(self, key: Optional[str], value: Any, depth: int) -> Any:
        """Redact a single value if key matches sensitive patterns."""
        if key and isinstance(key, str):
            key_lower = key.lower()
            if any(pattern in key_lower for pattern in REDACT_PATTERNS):
                if isinstance(value, str):
                    return f"<{len(value)}-char-secret>"
                return "<redacted>"

        if isinstance(value, dict):
            return {
                k: self._redact_value(k, v, depth - 1)
                for k, v in value.items()
            }
        elif isinstance(value, (list, tuple)):
            return type(value)(
                self._redact_value(None, item, depth - 1)
                for item in value
            )
        return value


class JsonFormatter(logging.Formatter):
    """JSON log formatter with structured fields."""

    def __init__(self):
        super().__init__()
        self.redactor = RedactedDict()

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "correlation_id": CorrelationContext.get(),
            "event": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, 'tool_name'):
            log_entry['tool_name'] = record.tool_name
        if hasattr(record, 'transport'):
            log_entry['transport'] = record.transport
        if hasattr(record, 'duration_ms'):
            log_entry['duration_ms'] = record.duration_ms
        if hasattr(record, 'status'):
            log_entry['status'] = record.status
        if hasattr(record, 'output_size_bytes'):
            log_entry['output_size_bytes'] = record.output_size_bytes
        if hasattr(record, 'error_category'):
            log_entry['error_category'] = record.error_category
        if hasattr(record, 'extra_data'):
            extra = record.extra_data
            if isinstance(extra, dict):
                extra = self.redactor.redact(extra)
            log_entry['extra'] = extra

        # Include exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
            }

        return json.dumps(log_entry)


class StructuredLogger:
    """Structured logger with automatic redaction and correlation tracking."""

    def __init__(self, name: str, level: str = "INFO"):
        """Initialize structured logger.
        
        Args:
            name: Logger name (usually __name__)
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level))
        
        # Remove any existing handlers
        self.logger.handlers.clear()
        self.logger.propagate = False

        # Add stderr handler with JSON formatter
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JsonFormatter())
        self.logger.addHandler(handler)

        self.redactor = RedactedDict()

    def _log_with_extras(
        self,
        level: str,
        message: str,
        **extras: Any
    ) -> None:
        """Log with extra fields."""
        record = self.logger.makeRecord(
            self.logger.name,
            getattr(logging, level),
            "", 0, message, (), None,
        )
        for key, value in extras.items():
            setattr(record, key, value)
        self.logger.handle(record)

    def debug(self, message: str, **extras: Any) -> None:
        """Log debug message."""
        self._log_with_extras("DEBUG", message, **extras)

    def info(self, message: str, **extras: Any) -> None:
        """Log info message."""
        self._log_with_extras("INFO", message, **extras)

    def warning(self, message: str, **extras: Any) -> None:
        """Log warning message."""
        self._log_with_extras("WARNING", message, **extras)

    def error(self, message: str, **extras: Any) -> None:
        """Log error message."""
        self._log_with_extras("ERROR", message, **extras)

    def critical(self, message: str, **extras: Any) -> None:
        """Log critical message."""
        self._log_with_extras("CRITICAL", message, **extras)

    def log_tool_invocation(
        self,
        tool_name: str,
        transport: str = "stdio",
        status: str = "started",
        duration_ms: Optional[int] = None,
        output_size_bytes: Optional[int] = None,
        error_category: Optional[str] = None,
    ) -> None:
        """Log a tool invocation event."""
        message = f"Tool invocation: {tool_name}"
        extras = {
            'tool_name': tool_name,
            'transport': transport,
            'status': status,
        }
        if duration_ms is not None:
            extras['duration_ms'] = duration_ms
        if output_size_bytes is not None:
            extras['output_size_bytes'] = output_size_bytes
        if error_category is not None:
            extras['error_category'] = error_category
        
        level = "WARNING" if error_category else "INFO"
        self._log_with_extras(level, message, **extras)

    def log_auth_failure(
        self,
        reason: str,
        transport: str = "http",
    ) -> None:
        """Log an authentication failure (without exposing token)."""
        message = f"Authentication failed: {reason}"
        self._log_with_extras(
            "WARNING",
            message,
            transport=transport,
            error_category="auth_failure",
        )

    def log_validation_error(
        self,
        tool_name: str,
        field: str,
        reason: str,
    ) -> None:
        """Log input validation failure."""
        message = f"Validation error in {tool_name}.{field}: {reason}"
        self._log_with_extras(
            "WARNING",
            message,
            tool_name=tool_name,
            error_category="validation_error",
        )

    def log_startup(self, **config: Any) -> None:
        """Log server startup with redacted config."""
        redacted_config = self.redactor.redact(config)
        message = f"Server starting with configuration"
        self._log_with_extras("INFO", message, extra_data=redacted_config)

    def log_shutdown(self, reason: str = "normal") -> None:
        """Log server shutdown."""
        self._log_with_extras(
            "INFO",
            f"Server shutting down: {reason}",
        )


def get_logger(name: str, level: str = "INFO") -> StructuredLogger:
    """Get or create a structured logger."""
    return StructuredLogger(name, level)
