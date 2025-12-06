import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router.nicolive import router as nicolive_router
from .router.ytlive import router as ytlive_router
from .settings import get_settings
from .utility.version import get_version

_version = get_version()
_settings = get_settings()

_cors_allow_origins = _settings.cors_allow_origins.split(",")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title="Live Info API Middleware",
    version=_version,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nicolive_router)
app.include_router(ytlive_router)
