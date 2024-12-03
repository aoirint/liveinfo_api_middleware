import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from liveinfo_api_middleware import __VERSION__ as LIVEINFO_VERSION
from liveinfo_api_middleware.nicolive import NicoliveUserLive, fetch_nicolive_user_live
from liveinfo_api_middleware.ytlive import YtliveChannelLive, fetch_ytlive_channel_live

YTLIVE_CHANNEL_ID = os.environ["YTLIVE_CHANNEL_ID"]
YTLIVE_API_KEY = os.environ["YTLIVE_API_KEY"]
YTLIVE_DUMP_PATH = Path(os.environ["YTLIVE_DUMP_PATH"])

NICOLIVE_USER_ID = os.environ["NICOLIVE_USER_ID"]
NICOLIVE_DUMP_PATH = Path(os.environ["NICOLIVE_DUMP_PATH"])

CORS_ALLOW_ORIGINS = os.environ["CORS_ALLOW_ORIGINS"].split(",")

USERAGENT = f"aoirint_liveinfo_api_middleware/{LIVEINFO_VERSION}"

app = FastAPI(
    title="Live Info API Middleware",
    version=LIVEINFO_VERSION,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nicolive_last_fetched: Optional[datetime] = None
nicolive_interval = timedelta(seconds=60)

ytlive_last_fetched: Optional[datetime] = None
ytlive_interval = timedelta(seconds=60)


@app.get(
    "/v1/nicolive",
    response_model=NicoliveUserLive,
)
def v1_nicolive() -> NicoliveUserLive:
    global nicolive_last_fetched

    nicolive_user_live: NicoliveUserLive | None = None

    now = datetime.now(tz=timezone.utc)
    if (
        nicolive_last_fetched is None
        or nicolive_interval <= now - nicolive_last_fetched
    ):
        # cache expired
        nicolive_last_fetched_string = (
            nicolive_last_fetched.isoformat()
            if nicolive_last_fetched is not None
            else "None"
        )
        print(
            f"[{now.isoformat()}] Fetch nicolive "
            f"(last_fetched_at: {nicolive_last_fetched_string})"
        )

        try:
            nicolive_user_live = fetch_nicolive_user_live(
                nicolive_user_id=NICOLIVE_USER_ID,
                useragent=USERAGENT,
            )

            NICOLIVE_DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)
            NICOLIVE_DUMP_PATH.write_text(
                nicolive_user_live.model_dump_json(),
                encoding="utf-8",
            )
        finally:
            nicolive_last_fetched = now

    if nicolive_user_live is None:
        # cache not expired or error fallback
        if NICOLIVE_DUMP_PATH.exists():
            nicolive_user_live = NicoliveUserLive.model_validate_json(
                NICOLIVE_DUMP_PATH.read_text(encoding="utf-8")
            )

    if nicolive_user_live is None:
        # return 404 if not found
        raise HTTPException(
            status_code=404,
            detail="Nicolive User Live not found",
        )

    return nicolive_user_live


@app.get(
    "/v1/ytlive",
    response_model=YtliveChannelLive,
)
def v1_ytlive() -> YtliveChannelLive:
    global ytlive_last_fetched

    ytlive_channel_live: YtliveChannelLive | None = None

    now = datetime.now(tz=timezone.utc)
    if ytlive_last_fetched is None or ytlive_interval <= now - ytlive_last_fetched:
        ytlive_last_fetched_string = (
            ytlive_last_fetched.isoformat()
            if ytlive_last_fetched is not None
            else "None"
        )
        print(
            f"[{now.isoformat()}] Fetch ytlive (last_fetched_at: {ytlive_last_fetched_string})"
        )

        try:
            ytlive_channel_live = fetch_ytlive_channel_live(
                ytlive_channel_id=YTLIVE_CHANNEL_ID,
                ytlive_api_key=YTLIVE_API_KEY,
                useragent=USERAGENT,
            )

            YTLIVE_DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)
            YTLIVE_DUMP_PATH.write_text(
                ytlive_channel_live.model_dump_json(),
                encoding="utf-8",
            )
        finally:
            ytlive_last_fetched = now

    if ytlive_channel_live is None:
        # cache not expired or error fallback
        if YTLIVE_DUMP_PATH.exists():
            ytlive_channel_live = YtliveChannelLive.model_validate_json(
                YTLIVE_DUMP_PATH.read_text(encoding="utf-8")
            )

    if ytlive_channel_live is None:
        # return 404 if not found
        raise HTTPException(
            status_code=404,
            detail="Ytlive Channel Live not found",
        )

    return ytlive_channel_live
