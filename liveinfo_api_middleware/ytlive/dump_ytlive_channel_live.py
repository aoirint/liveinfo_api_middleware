import json
from datetime import datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

import requests
from pydantic import BaseModel

JST = ZoneInfo("Asia/Tokyo")


class YtliveDataChannelItemSnippetThumbnail(BaseModel):
    url: str
    width: int
    height: int


class YtliveDataChannelItemSnippetThumbnails(BaseModel):
    default: YtliveDataChannelItemSnippetThumbnail | None = None
    medium: YtliveDataChannelItemSnippetThumbnail | None = None
    high: YtliveDataChannelItemSnippetThumbnail | None = None


class YtliveDataChannelItemSnippet(BaseModel):
    customUrl: str | None = None
    thumbnails: YtliveDataChannelItemSnippetThumbnails | None = None


class YtliveDataChannelItem(BaseModel):
    snippet: YtliveDataChannelItemSnippet | None = None


class YtliveDataChannel(BaseModel):
    items: list[YtliveDataChannelItem] | None = None


class YtliveDataSearchItemSnippet(BaseModel):
    liveBroadcastContent: str


class YtliveDataSearchItemId(BaseModel):
    videoId: str


class YtliveDataSearchItem(BaseModel):
    id: YtliveDataSearchItemId
    snippet: YtliveDataSearchItemSnippet | None = None


class YtliveDataSearch(BaseModel):
    items: list[YtliveDataSearchItem] | None = None


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
    channel_api_data = YtliveDataChannel.model_validate(channel_api_dict)

    channel_list_items = channel_api_data.items
    channel = channel_list_items[0] if channel_list_items is not None else None

    channel_custom_url: str | None = None
    channel_thumbnails: YtliveDataChannelItemSnippetThumbnails | None = None
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
    search_api_data = YtliveDataSearch.model_validate(search_api_dict)

    search_list_items = (
        search_api_data.items if search_api_data.items is not None else []
    )

    # 各動画の詳細を取得
    videos_response = requests.get(
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
    videos_data = videos_response.json()

    live_items = []
    for video_item in videos_data["items"]:
        video_id = video_item["id"]

        status_obj = video_item["status"]

        privacy_status: Literal["public", "private", "unlisted"] = status_obj.get(
            "privacyStatus"
        )
        if privacy_status != "public":
            # 非公開・限定公開のライブ配信・動画は対象にしない
            continue

        search_item: YtliveDataSearchItem = next(
            filter(
                lambda search_item: search_item.id.videoId == video_id,
                search_list_items,
            )
        )

        live_broadcast_content: str | None = None
        if search_item.snippet is not None:
            live_broadcast_content = search_item.snippet.liveBroadcastContent

        live_streming_details_obj = video_item.get("liveStreamingDetails")

        if live_broadcast_content == "live":
            # ライブ配信中の番組がある場合、選択する
            live_items.append(video_item)

        if live_broadcast_content == "none" and live_streming_details_obj is not None:
            # 終了済みのライブ番組またはプレミア公開番組がある場合、選択する
            live_items.append(video_item)

    # 最新とその1つ前のライブ番組の順番が交換されるYouTubeの謎仕様の対策（再エンコード処理のせい？）
    # 実際の放送時間に基づいてソートし直す
    active_video_item = {}
    max_start_time = None
    for video_item in live_items:
        start_time_string = video_item.get("liveStreamingDetails", {}).get(
            "actualStartTime"
        )
        start_time = (
            datetime.fromisoformat(start_time_string)
            if start_time_string is not None
            else datetime.min
        )

        if max_start_time is None or max_start_time < start_time:
            active_video_item = video_item
            max_start_time = start_time

    # Extract data from active_video_item
    active_video_id = active_video_item.get("id")
    active_search_item: YtliveDataSearchItem | None = next(
        filter(
            lambda search_item: search_item.id.videoId == active_video_id,
            search_list_items,
        ),
        None,
    )

    snippet_obj = active_video_item.get("snippet")
    live_streming_details_obj = active_video_item.get("liveStreamingDetails", {})

    active_search_item_live_broadcast_content: str | None = None
    if active_search_item is not None:
        if active_search_item.snippet is not None:
            active_search_item_live_broadcast_content = (
                active_search_item.snippet.liveBroadcastContent
            )

    title = snippet_obj.get("title")
    description = snippet_obj.get("description")

    channel_id = snippet_obj.get("channelId")
    channel_name = snippet_obj.get("channelTitle")

    thumbnails = snippet_obj.get("thumbnails", {})

    start_time_string = live_streming_details_obj.get("actualStartTime")
    end_time_string = live_streming_details_obj.get("actualEndTime")

    channel_url = (
        f"https://www.youtube.com/channel/{channel_id}"
        if channel_id is not None
        else None
    )
    if channel_custom_url is not None:
        channel_url = f"https://www.youtube.com/{channel_custom_url}"  # ハンドル名

    dump_path.parent.mkdir(parents=True, exist_ok=True)
    dump_path.write_text(
        json.dumps(
            {
                "program": {
                    "id": active_video_id,
                    "title": title,
                    "description": description,
                    "url": f"https://www.youtube.com/watch?v={active_video_id}"
                    if active_video_id is not None
                    else None,
                    "thumbnails": thumbnails,
                    "startTime": start_time_string,
                    "endTime": end_time_string,
                    "isOnair": active_search_item_live_broadcast_content == "live",
                },
                "channel": {
                    "id": channel_id,
                    "name": channel_name,
                    "url": channel_url,
                    "thumbnails": (
                        channel_thumbnails.model_dump()
                        if channel_thumbnails is not None
                        else None
                    ),
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
