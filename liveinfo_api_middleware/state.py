from datetime import datetime
from functools import lru_cache

from pydantic import BaseModel


class State(BaseModel):
    nicolive_last_fetched: datetime | None = None
    ytlive_last_fetched: datetime | None = None


@lru_cache
def get_state() -> State:
    return State()
