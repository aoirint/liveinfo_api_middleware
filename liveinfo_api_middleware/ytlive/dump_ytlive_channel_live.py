import json
from datetime import datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

import requests
from pydantic import BaseModel

JST = ZoneInfo("Asia/Tokyo")


class YtliveApiChannelItemSnippetThumbnail(BaseModel):
    url: str
    width: int
    height: int


class YtliveApiChannelItemSnippetThumbnails(BaseModel):
    default: YtliveApiChannelItemSnippetThumbnail | None = None
    medium: YtliveApiChannelItemSnippetThumbnail | None = None
    high: YtliveApiChannelItemSnippetThumbnail | None = None


class YtliveApiChannelItemSnippet(BaseModel):
    customUrl: str | None = None
    thumbnails: YtliveApiChannelItemSnippetThumbnails | None = None


class YtliveApiChannelItem(BaseModel):
    snippet: YtliveApiChannelItemSnippet | None = None


class YtliveApiChannel(BaseModel):
    items: list[YtliveApiChannelItem] | None = None


class YtliveApiSearchItemSnippet(BaseModel):
    liveBroadcastContent: str


class YtliveApiSearchItemId(BaseModel):
    videoId: str


class YtliveApiSearchItem(BaseModel):
    id: YtliveApiSearchItemId
    snippet: YtliveApiSearchItemSnippet | None = None


class YtliveApiSearch(BaseModel):
    items: list[YtliveApiSearchItem] | None = None


class YtliveApiVideoItemLiveStreamingDetails(BaseModel):
    actualStartTime: str
    actualEndTime: str


class YtliveApiVideoItemSnippetThumbnail(BaseModel):
    url: str
    width: int
    height: int


class YtliveApiVideoItemSnippetThumbnails(BaseModel):
    default: YtliveApiVideoItemSnippetThumbnail | None = None
    medium: YtliveApiVideoItemSnippetThumbnail | None = None
    high: YtliveApiVideoItemSnippetThumbnail | None = None
    standard: YtliveApiVideoItemSnippetThumbnail | None = None
    maxres: YtliveApiVideoItemSnippetThumbnail | None = None


class YtliveApiVideoItemSnippet(BaseModel):
    title: str | None = None
    description: str | None = None
    channelId: str | None = None
    channelTitle: str | None = None
    thumbnails: YtliveApiVideoItemSnippetThumbnails | None = None


class YtliveApiVideoItemStatus(BaseModel):
    privacyStatus: Literal["public", "private", "unlisted"]


class YtliveApiVideoItem(BaseModel):
    id: str
    status: YtliveApiVideoItemStatus | None = None
    snippet: YtliveApiVideoItemSnippet | None = None
    liveStreamingDetails: YtliveApiVideoItemLiveStreamingDetails | None = None


class YtliveApiVideo(BaseModel):
    items: list[YtliveApiVideoItem] | None = None


class YtliveChannelLiveProgram(BaseModel):
    id: str | None
    title: str | None
    description: str | None
    url: str | None
    thumbnails: YtliveApiVideoItemSnippetThumbnails | None
    startTime: str | None
    endTime: str | None
    isOnair: bool | None


class YtliveChannelLiveChannel(BaseModel):
    id: str | None
    name: str | None
    url: str | None
    thumbnails: YtliveApiChannelItemSnippetThumbnails | None


class YtliveChannelLive(BaseModel):
    program: YtliveChannelLiveProgram
    channel: YtliveChannelLiveChannel


def dump_ytlive_channel_live(
    ytlive_channel_id: str,
    ytlive_api_key: str,
    useragent: str,
    dump_path: Path,
) -> None:
    # チャンネル情報を取得（アイコン）
    channel_api_response = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={
            "key": ytlive_api_key,
            "part": "snippet",
            "id": ytlive_channel_id,
        },
        headers={
            "User-Agent": useragent,
        },
    )
    channel_api_dict = channel_api_response.json()
    channel_api_data = YtliveApiChannel.model_validate(channel_api_dict)

    channel_list_items = channel_api_data.items
    channel = channel_list_items[0] if channel_list_items is not None else None

    channel_custom_url: str | None = None
    channel_thumbnails: YtliveApiChannelItemSnippetThumbnails | None = None
    if channel is not None:
        if channel.snippet is not None:
            channel_custom_url = channel.snippet.customUrl
            channel_thumbnails = channel.snippet.thumbnails

    # チャンネルの動画リストを取得
    search_response = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "key": ytlive_api_key,
            "part": "id,snippet",
            "channelId": ytlive_channel_id,
            "type": "video",
            "order": "date",  # createdAt desc
            "maxResults": "10",
        },
        headers={
            "User-Agent": useragent,
        },
    )
    search_api_dict = search_response.json()
    search_api_data = YtliveApiSearch.model_validate(search_api_dict)

    search_list_items = (
        search_api_data.items if search_api_data.items is not None else []
    )

    # 各動画の詳細を取得
    video_api_response = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={
            "key": ytlive_api_key,
            "part": "snippet,status,liveStreamingDetails",
            "id": ",".join(list(map(lambda item: item.id.videoId, search_list_items))),
        },
        headers={
            "User-Agent": useragent,
        },
    )
    video_api_dict = video_api_response.json()
    video_api_data = YtliveApiVideo.model_validate(video_api_dict)

    video_list_items = video_api_data.items if video_api_data.items is not None else []
    live_items: list[YtliveApiVideoItem] = []
    for video_item in video_list_items:
        video_id = video_item.id

        if video_item.status is None or video_item.status.privacyStatus != "public":
            # 非公開・限定公開のライブ配信・動画は対象にしない
            continue

        search_item: YtliveApiSearchItem = next(
            filter(
                lambda search_item: search_item.id.videoId == video_id,
                search_list_items,
            )
        )

        live_broadcast_content: str | None = None
        if search_item.snippet is not None:
            live_broadcast_content = search_item.snippet.liveBroadcastContent

        if live_broadcast_content == "live":
            # ライブ配信中の番組がある場合、選択する
            live_items.append(video_item)

        if (
            live_broadcast_content == "none"
            and video_item.liveStreamingDetails is not None
        ):
            # 終了済みのライブ番組またはプレミア公開番組がある場合、選択する
            live_items.append(video_item)

    # 最新とその1つ前のライブ番組の順番が交換されるYouTubeの謎仕様の対策（再エンコード処理のせい？）
    # 実際の放送時間に基づいてソートし直す
    active_video_item: YtliveApiVideoItem | None = None
    max_start_time: datetime | None = None
    for video_item in live_items:
        start_time_string: str | None = None
        if video_item.liveStreamingDetails is not None:
            start_time_string = video_item.liveStreamingDetails.actualStartTime

        start_time = (
            datetime.fromisoformat(start_time_string)
            if start_time_string is not None
            else datetime.min
        )

        if max_start_time is None or max_start_time < start_time:
            active_video_item = video_item
            max_start_time = start_time

    # Extract data from active_video_item
    active_video_id = active_video_item.id if active_video_item is not None else None

    active_search_item: YtliveApiSearchItem | None = next(
        filter(
            lambda search_item: (
                search_item is not None and search_item.id.videoId == active_video_id
            ),
            search_list_items,
        ),
        None,
    )

    active_search_item_live_broadcast_content: str | None = None
    if active_search_item is not None:
        if active_search_item.snippet is not None:
            active_search_item_live_broadcast_content = (
                active_search_item.snippet.liveBroadcastContent
            )

    title: str | None = None
    description: str | None = None
    channel_id: str | None = None
    channel_name: str | None = None
    thumbnails: YtliveApiVideoItemSnippetThumbnails | None = None
    if active_video_item is not None:
        if active_video_item.snippet is not None:
            title = active_video_item.snippet.title
            description = active_video_item.snippet.description
            channel_id = active_video_item.snippet.channelId
            channel_name = active_video_item.snippet.channelTitle
            thumbnails = active_video_item.snippet.thumbnails

    active_video_item_start_time_string: str | None = None
    active_video_item_end_time_string: str | None = None
    if active_video_item is not None:
        if active_video_item.liveStreamingDetails is not None:
            active_video_item_start_time_string = (
                active_video_item.liveStreamingDetails.actualStartTime
            )
            active_video_item_end_time_string = (
                active_video_item.liveStreamingDetails.actualEndTime
            )

    channel_url = (
        f"https://www.youtube.com/channel/{channel_id}"
        if channel_id is not None
        else None
    )
    if channel_custom_url is not None:
        channel_url = f"https://www.youtube.com/{channel_custom_url}"  # ハンドル名

    dump_path.parent.mkdir(parents=True, exist_ok=True)
    dump_path.write_text(
        YtliveChannelLive(
            program=YtliveChannelLiveProgram(
                id=active_video_id,
                title=title,
                description=description,
                url=f"https://www.youtube.com/watch?v={active_video_id}"
                if active_video_id is not None
                else None,
                thumbnails=thumbnails,
                startTime=active_video_item_start_time_string,
                endTime=active_video_item_end_time_string,
                isOnair=active_search_item_live_broadcast_content == "live",
            ),
            channel=YtliveChannelLiveChannel(
                id=channel_id,
                name=channel_name,
                url=channel_url,
                thumbnails=(
                    channel_thumbnails.model_dump()
                    if channel_thumbnails is not None
                    else None
                ),
            ),
        ).model_dump_json(),
        encoding="utf-8",
    )
