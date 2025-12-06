from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..settings import Settings, get_settings
from ..site.ytlive import (
    YtliveChannelLive,
    fetch_ytlive_channel_live,
)
from ..state import State, get_state
from ..utility.useragent import get_useragent

router = APIRouter()


@router.get(
    "/v1/ytlive",
    response_model=YtliveChannelLive,
)
def v1_ytlive(
    settings: Annotated[Settings, Depends(get_settings)],
    state: Annotated[State, Depends(get_state)],
) -> YtliveChannelLive:
    ytlive_channel_live: YtliveChannelLive | None = None

    ytlive_channel_id = settings.ytlive_channel_id
    ytlive_api_key = settings.ytlive_api_key
    ytlive_interval = timedelta(seconds=settings.ytlive_interval)

    ytlive_dump_path_string = settings.ytlive_dump_path
    if not ytlive_dump_path_string:
        raise ValueError("YTLIVE_DUMP_PATH is not set")
    ytlive_dump_path = Path(ytlive_dump_path_string)

    ytlive_last_fetched = state.ytlive_last_fetched

    useragent = get_useragent(settings=settings)

    now = datetime.now(tz=UTC)
    if ytlive_last_fetched is None or ytlive_interval <= now - ytlive_last_fetched:
        ytlive_last_fetched_string = (
            ytlive_last_fetched.isoformat()
            if ytlive_last_fetched is not None
            else "None"
        )
        print(
            f"[{now.isoformat()}] Fetch ytlive "
            f"(last_fetched_at: {ytlive_last_fetched_string})"
        )

        try:
            ytlive_channel_live = fetch_ytlive_channel_live(
                ytlive_channel_id=ytlive_channel_id,
                ytlive_api_key=ytlive_api_key,
                useragent=useragent,
            )

            ytlive_dump_path.parent.mkdir(parents=True, exist_ok=True)
            ytlive_dump_path.write_text(
                ytlive_channel_live.model_dump_json(),
                encoding="utf-8",
            )
        finally:
            ytlive_last_fetched = now

    if ytlive_channel_live is None:
        # cache not expired or error fallback
        if ytlive_dump_path.exists():
            ytlive_channel_live = YtliveChannelLive.model_validate_json(
                ytlive_dump_path.read_text(encoding="utf-8")
            )

    if ytlive_channel_live is None:
        # return 404 if not found
        raise HTTPException(
            status_code=404,
            detail="Ytlive Channel Live not found",
        )

    return ytlive_channel_live
