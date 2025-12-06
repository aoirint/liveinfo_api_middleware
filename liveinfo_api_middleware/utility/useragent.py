from ..settings import Settings
from .version import get_version


def get_useragent(settings: Settings) -> str:
    if settings.useragent:
        return settings.useragent

    version = get_version()
    return f"aoirint_liveinfo_api_middleware/{version}"
