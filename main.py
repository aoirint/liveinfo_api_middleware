import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from liveinfo_api_middleware import liveinfo_api

YTLIVE_CHANNEL_ID = os.environ["YTLIVE_CHANNEL_ID"]
YTLIVE_API_KEY = os.environ["YTLIVE_API_KEY"]
YTLIVE_DUMP_PATH = Path(os.environ["YTLIVE_DUMP_PATH"])

NICOLIVE_COMMUNITY_ID = os.environ["NICOLIVE_COMMUNITY_ID"]
NICOLIVE_DUMP_PATH = Path(os.environ["NICOLIVE_DUMP_PATH"])

CORS_ALLOW_ORIGINS = os.environ["CORS_ALLOW_ORIGINS"].split(",")

USERAGENT = "aoirint_liveinfo_api_middleware/0.0.0"

app = FastAPI()
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


@app.get("/v1/nicolive")
def v1_nicolive():
    global nicolive_last_fetched

    now = datetime.now(tz=timezone.utc)
    if (
        nicolive_last_fetched is None
        or nicolive_interval <= now - nicolive_last_fetched
    ):
        nicolive_last_fetched_string = (
            nicolive_last_fetched.isoformat()
            if nicolive_last_fetched is not None
            else "None"
        )
        print(
            f"[{now.isoformat()}] Fetch nicolive (last_fetched_at: {nicolive_last_fetched_string})"
        )

        try:
            liveinfo_api.dump_nicolive_community_live(
                nicolive_community_id=NICOLIVE_COMMUNITY_ID,
                useragent=USERAGENT,
                dump_path=NICOLIVE_DUMP_PATH,
            )
        finally:
            nicolive_last_fetched = now

    return FileResponse(NICOLIVE_DUMP_PATH)


@app.get("/v1/ytlive")
def v1_ytlive():
    global ytlive_last_fetched

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
            liveinfo_api.dump_ytlive_channel_live(
                ytlive_channel_id=YTLIVE_CHANNEL_ID,
                ytlive_api_key=YTLIVE_API_KEY,
                useragent=USERAGENT,
                dump_path=YTLIVE_DUMP_PATH,
            )
        finally:
            ytlive_last_fetched = now

    return FileResponse(YTLIVE_DUMP_PATH)
