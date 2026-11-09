"""Application error types and the standard error envelope.

Every error returned to the frontend uses this shape:

    {"error": {"code", "message", "details", "request_id"}}

Internal exception details stay in server logs.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for expected, user-displayable application errors."""

    status_code = 500
    code = "internal_error"
    message = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Any | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details
        super().__init__(self.message)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def error_payload(
    request: Request,
    *,
    code: str,
    message: str,
    details: Any | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": _request_id(request),
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "Application error code=%s status=%s request_id=%s",
            exc.code,
            exc.status_code,
            _request_id(request),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(
                request, code=exc.code, message=exc.message, details=exc.details
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg", "Invalid value"),
                "type": error.get("type", "value_error"),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_payload(
                request,
                code="validation_error",
                message="The request contains invalid or missing fields.",
                details=details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_error(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code_by_status = {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
            409: "conflict",
            413: "payload_too_large",
            415: "unsupported_media_type",
            429: "rate_limited",
            502: "upstream_error",
            503: "service_unavailable",
            504: "upstream_timeout",
        }
        message = (
            exc.detail
            if isinstance(exc.detail, str) and exc.detail
            else "The request could not be completed."
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(
                request,
                code=code_by_status.get(exc.status_code, "http_error"),
                message=message,
            ),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "Unhandled error request_id=%s path=%s",
            _request_id(request),
            request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content=error_payload(
                request,
                code="internal_error",
                message="An unexpected error occurred. Please try again.",
            ),
        )
