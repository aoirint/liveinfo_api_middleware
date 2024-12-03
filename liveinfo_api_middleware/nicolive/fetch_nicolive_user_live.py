from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel

JST = ZoneInfo("Asia/Tokyo")


class NicoliveApiUserBroadcastHistoryProgramId(BaseModel):
    value: str | None = None
    """Live ID: lvXXXXXXXX"""


class NicoliveApiUserBroadcastHistoryProgramScheduleTime(BaseModel):
    seconds: int | None = None


class NicoliveApiUserBroadcastHistoryProgramSchedule(BaseModel):
    status: Literal["ENDED", "ON_AIR"] | str | None = None
    beginTime: NicoliveApiUserBroadcastHistoryProgramScheduleTime | None = None
    endTime: NicoliveApiUserBroadcastHistoryProgramScheduleTime | None = None


class NicoliveApiUserBroadcastHistoryProgramProgram(BaseModel):
    title: str | None = None
    """
    放送のタイトル
    """

    description: str | None = None
    """
    放送の説明文
    """

    schedule: NicoliveApiUserBroadcastHistoryProgramSchedule | None = None
    """
    放送のスケジュール（実際の放送時間や予約状態）
    """


class NicoliveApiUserBroadcastHistoryProgramProviderId(BaseModel):
    value: str | None = None
    """ユーザーID"""


class NicoliveApiUserBroadcastHistoryProgramProviderIcons(BaseModel):
    uri150x150: str | None = None
    """
    ユーザーのアイコンURL（150px x 150px）
    """


class NicoliveApiUserBroadcastHistoryProgramProvider(BaseModel):
    programProviderId: NicoliveApiUserBroadcastHistoryProgramProviderId | None = None
    """
    ユーザーのID
    """
    name: str
    """
    ユーザーの名前
    """
    icons: NicoliveApiUserBroadcastHistoryProgramProviderIcons | None = None
    """
    ユーザーのアイコン
    """


class NicoliveApiUserBroadcastHistoryThumbnailListingItem(BaseModel):
    value: str | None = None
    """
    サムネイルのURL
    """


class NicoliveApiUserBroadcastHistoryThumbnailListing(BaseModel):
    xlarge: NicoliveApiUserBroadcastHistoryThumbnailListingItem | None = None
    """
    サムネイル（1280px x 720px）

    ユーザーがサムネイルを設定している場合、設定されたサムネイル。
    設定していない場合、自動的に生成されたサムネイル。
    """


class NicoliveApiUserBroadcastHistoryThumbnail(BaseModel):
    listing: NicoliveApiUserBroadcastHistoryThumbnailListing | None = None


class NicoliveApiUserBroadcastHistoryProgram(BaseModel):
    id: NicoliveApiUserBroadcastHistoryProgramId | None = None
    program: NicoliveApiUserBroadcastHistoryProgramProgram | None = None
    """
    放送情報
    """
    programProvider: NicoliveApiUserBroadcastHistoryProgramProvider | None = None
    """
    放送者の情報
    """
    thumbnail: NicoliveApiUserBroadcastHistoryThumbnail | None = None
    """
    サムネイル
    """


class NicoliveApiUserBroadcastHistoryData(BaseModel):
    programsList: list[NicoliveApiUserBroadcastHistoryProgram] | None = None


class NicoliveApiUserBroadcastHistory(BaseModel):
    data: NicoliveApiUserBroadcastHistoryData | None = None


class NicoliveUserLiveProgram(BaseModel):
    title: str | None
    description: str | None
    url: str | None
    thumbnails: list[str] | None
    startTime: str | None
    endTime: str | None
    isOnair: bool | None


class NicoliveUserLiveUser(BaseModel):
    name: str | None
    url: str | None
    iconUrl: str | None


class NicoliveUserLive(BaseModel):
    program: NicoliveUserLiveProgram
    user: NicoliveUserLiveUser


def fetch_nicolive_user_live(
    nicolive_user_id: str,
    useragent: str,
) -> NicoliveUserLive:
    history_response = requests.get(
        "https://live.nicovideo.jp/front/api/v2/user-broadcast-history",
        headers={
            "User-Agent": useragent,
        },
        params={
            "providerId": nicolive_user_id,
            "providerType": "user",
            "isIncludeNonPublic": "false",
            "offset": "0",
            "limit": "1",
            "withTotalCount": "true",
        },
    )

    broadcast_history: NicoliveApiUserBroadcastHistory | None = None
    if history_response.status_code == 200:
        broadcast_history = NicoliveApiUserBroadcastHistory.model_validate_json(
            history_response.text
        )
    else:
        print(f"ERRORED: {history_response.text}")

    program: NicoliveApiUserBroadcastHistoryProgram | None = None
    if broadcast_history is not None:
        if broadcast_history.data is not None:
            if broadcast_history.data.programsList is not None:
                if len(broadcast_history.data.programsList) > 0:
                    program = broadcast_history.data.programsList[0]

    is_onair = False
    if program is not None:
        if program.program is not None:
            if program.program.schedule is not None:
                is_onair = program.program.schedule.status == "ON_AIR"

    title: str | None = None
    if program is not None:
        if program.program is not None:
            title = program.program.title

    description: str | None = None
    if program is not None:
        if program.program is not None:
            if program.program.description is not None:
                description_html = program.program.description

                description_bs = BeautifulSoup(description_html, "html5lib")

                # keep line breaks
                for br_tag in description_bs.select("br"):
                    br_tag.replace_with("\n")

                description = description_bs.text

    thumbnails: list[str] | None = None
    if program is not None:
        if program.thumbnail is not None:
            if program.thumbnail.listing is not None:
                if program.thumbnail.listing.xlarge is not None:
                    if program.thumbnail.listing.xlarge.value is not None:
                        thumbnails = [program.thumbnail.listing.xlarge.value]

    user_name: str | None = None
    if program is not None:
        if program.programProvider is not None:
            user_name = program.programProvider.name

    user_url: str | None = None
    if program is not None:
        if program.programProvider is not None:
            if program.programProvider.programProviderId is not None:
                if program.programProvider.programProviderId.value is not None:
                    user_url = f"https://www.nicovideo.jp/user/{program.programProvider.programProviderId.value}"  # noqa: B950

    user_icon_url: str | None = None
    if program is not None:
        if program.programProvider is not None:
            if program.programProvider.icons is not None:
                user_icon_url = program.programProvider.icons.uri150x150

    start_time_string: str | None = None
    end_time_string: str | None = None
    if program is not None:
        if program.program is not None:
            if program.program.schedule is not None:
                if program.program.schedule.beginTime is not None:
                    if program.program.schedule.beginTime.seconds is not None:
                        start_time_seconds = program.program.schedule.beginTime.seconds
                        start_time_string = datetime.fromtimestamp(
                            start_time_seconds, tz=JST
                        ).isoformat()

                if program.program.schedule.endTime is not None:
                    if program.program.schedule.endTime.seconds is not None:
                        end_time_seconds = program.program.schedule.endTime.seconds
                        end_time_string = datetime.fromtimestamp(
                            end_time_seconds, tz=JST
                        ).isoformat()

    program_url: str | None = None
    if program is not None:
        if program.id is not None:
            if program.id.value is not None:
                program_url = f"https://live.nicovideo.jp/watch/{program.id.value}"

    return NicoliveUserLive(
        program=NicoliveUserLiveProgram(
            title=title,
            description=description,
            url=program_url,
            thumbnails=thumbnails,
            startTime=start_time_string,
            endTime=end_time_string,
            isOnair=is_onair,
        ),
        user=NicoliveUserLiveUser(
            name=user_name,
            url=user_url,
            iconUrl=user_icon_url,
        ),
    )
