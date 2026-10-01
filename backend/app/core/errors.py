"""Domain errors with stable machine-readable codes.

The API always responds with ``{"error": {"code", "message", "details"}}`` so
both React and Flutter clients can translate errors by code.
"""

from typing import Any


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, *, code: str | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class AuthenticationError(AppError):
    status_code = 401
    code = "AUTHENTICATION_FAILED"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "PERMISSION_DENIED"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class ValidationFailedError(AppError):
    status_code = 422
    code = "VALIDATION_FAILED"


class InvalidTransitionError(ConflictError):
    code = "INVALID_STATUS_TRANSITION"


class PaymentStateError(ConflictError):
    code = "PAYMENT_STATE_ERROR"


class ProviderUnavailableError(ConflictError):
    code = "PROVIDER_UNAVAILABLE"


class RateLimitedError(AppError):
    status_code = 429
    code = "RATE_LIMITED"
