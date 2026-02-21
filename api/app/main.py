# Copyright (C) 2021-2025, Mindee.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://opensource.org/licenses/Apache-2.0> for full license details.

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi

from app import config as cfg
from app.routes import detection, kie, ocr, recognition
from app.schemas import OCRIn
from app.vision import init_predictor


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Preload default OCR model at startup so first /ocr/text request stays under Render timeout."""
    default_req = OCRIn()
    app.state.default_ocr_request = default_req
    app.state.default_ocr_predictor = init_predictor(default_req)
    yield
    # no explicit teardown needed


app = FastAPI(
    title=cfg.PROJECT_NAME,
    description=cfg.PROJECT_DESCRIPTION,
    debug=cfg.DEBUG,
    version=cfg.VERSION,
    lifespan=lifespan,
)


# Routing
app.include_router(recognition.router, prefix="/recognition", tags=["recognition"])
app.include_router(detection.router, prefix="/detection", tags=["detection"])
app.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
app.include_router(kie.router, prefix="/kie", tags=["kie"])


@app.get("/health", summary="Health check")
def health():
    """Lightweight health check for Render/proxies. Does not load OCR models."""
    return {"status": "ok"}


# Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Docs
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=cfg.PROJECT_NAME,
        version=cfg.VERSION,
        description=cfg.PROJECT_DESCRIPTION,
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
