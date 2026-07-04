"""RFC 7807 problem+json error handling (Implementation Note 7).

All error responses use ``application/problem+json`` with a ``detail`` field the
frontend can surface directly.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_CONTENT_TYPE = "application/problem+json"


class ProblemException(Exception):
    """Raise anywhere to emit an RFC 7807 response."""

    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        type_: str = "about:blank",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type_ = type_
        self.headers = headers or {}
        super().__init__(detail)


def _problem_response(
    status_code: int,
    title: str,
    detail: str,
    type_: str = "about:blank",
    instance: str | None = None,
    extra: dict | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict = {"type": type_, "title": title, "status": status_code, "detail": detail}
    if instance:
        body["instance"] = instance
    if extra:
        body.update(extra)
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type=PROBLEM_CONTENT_TYPE,
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemException)
    async def _handle_problem(request: Request, exc: ProblemException) -> JSONResponse:
        return _problem_response(
            exc.status_code, exc.title, exc.detail, exc.type_,
            instance=str(request.url.path), headers=exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        title = {
            400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
            404: "Not Found", 405: "Method Not Allowed", 409: "Conflict",
            429: "Too Many Requests",
        }.get(exc.status_code, "Error")
        detail = exc.detail if isinstance(exc.detail, str) else title
        return _problem_response(
            exc.status_code, title, detail,
            instance=str(request.url.path),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": list(e.get("loc", [])), "msg": e.get("msg", ""), "type": e.get("type", "")}
            for e in exc.errors()
        ]
        return _problem_response(
            422, "Unprocessable Entity",
            "One or more fields failed validation.",
            type_="about:validation-error",
            instance=str(request.url.path),
            extra={"errors": errors},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        return _problem_response(
            500, "Internal Server Error",
            "An unexpected error occurred.",
            instance=str(request.url.path),
        )
