"""NEXORA ERP — Standardized Domain & Security Exceptions."""
from __future__ import annotations

from typing import Any


class NexoraError(Exception):
    """Base application error with HTTP status code and machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class UnauthorizedError(NexoraError):
    def __init__(self, message: str = "Authentication required", code: str = "UNAUTHORIZED") -> None:
        super().__init__(code=code, message=message, status_code=401)


class ForbiddenError(NexoraError):
    def __init__(self, message: str = "Insufficient permissions", code: str = "FORBIDDEN") -> None:
        super().__init__(code=code, message=message, status_code=403)


class NotFoundError(NexoraError):
    def __init__(self, message: str = "Requested resource not found", code: str = "NOT_FOUND") -> None:
        super().__init__(code=code, message=message, status_code=404)


class ConflictError(NexoraError):
    def __init__(self, message: str = "Resource conflict", code: str = "CONFLICT") -> None:
        super().__init__(code=code, message=message, status_code=409)


class BusinessRuleError(NexoraError):
    def __init__(self, message: str, code: str = "BUSINESS_RULE_VIOLATION", details: Any = None) -> None:
        super().__init__(code=code, message=message, status_code=422, details=details)
