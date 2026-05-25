from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.stdlib.get_logger()


class AppError(Exception):
    """Base application error with structured error response."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
    )


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    logger.warning("app_error", code=exc.code, message=exc.message)
    return _error_response(exc.status_code, exc.code, exc.message, exc.details)


async def http_error_handler(
    _request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return _error_response(exc.status_code, "HTTP_ERROR", str(exc.detail))


async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    return _error_response(
        422,
        "VALIDATION_ERROR",
        "Request validation failed",
        {"errors": errors},
    )


async def unhandled_error_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    logger.exception("unhandled_error", error=str(exc))
    return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")


def register_error_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app."""
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)
