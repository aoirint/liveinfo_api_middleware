from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..settings import Settings, get_settings
from ..site.nicolive import NicoliveUserLive, fetch_nicolive_user_live
from ..state import State, get_state
from ..utility.useragent import get_useragent

router = APIRouter()


@router.get(
    "/v1/nicolive",
    response_model=NicoliveUserLive,
)
def v1_nicolive(
    settings: Annotated[Settings, Depends(get_settings)],
    state: Annotated[State, Depends(get_state)],
) -> NicoliveUserLive:
    nicolive_user_live: NicoliveUserLive | None = None

    nicolive_user_id = settings.nicolive_user_id
    nicolive_interval = timedelta(seconds=settings.nicolive_interval)

    nicolive_dump_path_string = settings.nicolive_dump_path
    if not nicolive_dump_path_string:
        raise ValueError("NICOLIVE_DUMP_PATH is not set")
    nicolive_dump_path = Path(nicolive_dump_path_string)

    nicolive_last_fetched = state.nicolive_last_fetched

    useragent = get_useragent(settings=settings)

    now = datetime.now(tz=UTC)
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
                nicolive_user_id=nicolive_user_id,
                useragent=useragent,
            )

            nicolive_dump_path.parent.mkdir(parents=True, exist_ok=True)
            nicolive_dump_path.write_text(
                nicolive_user_live.model_dump_json(),
                encoding="utf-8",
            )
        finally:
            nicolive_last_fetched = now

    if nicolive_user_live is None:
        # cache not expired or error fallback
        if nicolive_dump_path.exists():
            nicolive_user_live = NicoliveUserLive.model_validate_json(
                nicolive_dump_path.read_text(encoding="utf-8")
            )

    if nicolive_user_live is None:
        # return 404 if not found
        raise HTTPException(
            status_code=404,
            detail="Nicolive User Live not found",
        )

    return nicolive_user_live
