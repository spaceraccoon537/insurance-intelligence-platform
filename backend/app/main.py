from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, HTTPException as FastAPIHTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.api.router import api_router
from app.core.config import get_settings
from app.schemas import ErrorDetail, ErrorResponse


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Local-first insurance document intelligence API.",
    )

    @application.middleware("http")
    async def add_request_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = uuid4()
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = str(request_id)
        return response

    @application.exception_handler(FastAPIHTTPException)
    async def handle_http_exception(
        request: Request,
        exception: FastAPIHTTPException,
    ) -> JSONResponse:
        code = {
            404: "not_found",
            413: "upload_too_large",
            415: "unsupported_media_type",
            422: "invalid_document",
        }.get(exception.status_code, "http_error")
        error = ErrorResponse(
            error=ErrorDetail(
                code=code,
                message=str(exception.detail),
                request_id=request.state.request_id,
            )
        )
        return JSONResponse(
            status_code=exception.status_code,
            content=error.model_dump(mode="json"),
            headers=exception.headers,
        )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )
    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
