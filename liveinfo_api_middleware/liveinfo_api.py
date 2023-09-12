import json
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

JST = ZoneInfo("Asia/Tokyo")


def dump_nicolive_community_live(
    nicolive_community_id: str,
    useragent: str,
    dump_path: Path,
):
    onair_response = requests.get(
        f"https://com.nicovideo.jp/api/v1/communities/{nicolive_community_id}/lives/onair.json",
        headers={
            "User-Agent": useragent,
        },
    )
    # onair_response.raise_for_status()
    is_onair = False
    if onair_response.status_code == 200:
        onair_data = json.loads(onair_response.text)
        onair_live = onair_data.get("data", {}).get("live", {})

        is_onair = onair_live.get("status") == "ON_AIR"

    ogp_useragent = f"facebookexternalhit/1.1;Googlebot/2.1;{useragent}"

    watch_response = requests.get(
        f"https://live.nicovideo.jp/watch/co{nicolive_community_id}",
        headers={
            "User-Agent": ogp_useragent,
        },
    )
    watch_response.raise_for_status()

    bs = BeautifulSoup(watch_response.text, "html5lib")
    json_ld_tag = bs.find("script", attrs={"type": "application/ld+json"})
    json_ld_string = json_ld_tag.string

    json_ld_data = json.loads(json_ld_string)
    publication = json_ld_data.get("publication", {})
    author = json_ld_data.get("author", {})

    user_icon_tag = bs.select_one(
        "#watchPage > div.___program-information-area___2mmJb > div.___program-information-header-area___3F--P > div > div.___user-summary___1PSFe.___user-summary___1gieM.user-summary > div.___thumbnail-area___1z7XZ.thumbnail-area > a > img"
    )
    user_icon_url = user_icon_tag.get("src") if user_icon_tag is not None else None

    community_name_tag = bs.select_one(
        "#watchPage > div.___program-information-area___2mmJb > div.___program-information-body-area___1D8P9 > div.___program-information-side-area___1XQ24 > div > div > div > div > a"
    )
    community_name = community_name_tag.text if community_name_tag is not None else None
    community_url = (
        community_name_tag.get("href") if community_name_tag is not None else None
    )

    community_icon_tag = bs.select_one(
        "#watchPage > div.___program-information-area___2mmJb > div.___program-information-body-area___1D8P9 > div.___program-information-side-area___1XQ24 > div > div > div > a > img"
    )
    community_icon_url = (
        community_icon_tag.get("src") if community_icon_tag is not None else None
    )

    start_time_string = publication.get("startDate")
    end_time_string = publication.get("endDate")

    og_url_tag = bs.find("meta", attrs={"property": "og:url"})
    program_url = og_url_tag.get("content") if og_url_tag is not None else None

    dump_path.parent.mkdir(parents=True, exist_ok=True)
    dump_path.write_text(
        json.dumps(
            {
                "program": {
                    "title": json_ld_data.get("name"),
                    "description": json_ld_data.get("description"),
                    "url": program_url,
                    "thumbnails": json_ld_data.get("thumbnailUrl"),
                    "startTime": start_time_string,
                    "endTime": end_time_string,
                    "isOnair": is_onair,
                },
                "community": {
                    "name": community_name,
                    "url": community_url,
                    "iconUrl": community_icon_url,
                },
                "user": {
                    "name": author.get("name"),
                    "url": author.get("url"),
                    "iconUrl": user_icon_url,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def dump_ytlive_channel_live(
    ytlive_channel_id: str,
    ytlive_api_key: str,
    useragent: str,
    dump_path: Path,
):
    # チャンネル情報を取得（アイコン）
    channels_response = requests.get(
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
    channels_data = channels_response.json()
    channel_list_items = channels_data["items"]
    channel = channel_list_items[0]

    channel_snippet_obj = channel.get("snippet")
    channel_custom_url = channel_snippet_obj.get("customUrl")
    channel_thumbnails = channel_snippet_obj.get("thumbnails")

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
    search_data = search_response.json()
    search_list_items = search_data["items"]

    # 各動画の詳細を取得
    videos_response = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={
            "key": ytlive_api_key,
            "part": "snippet,status,liveStreamingDetails",
            "id": ",".join(
                list(map(lambda item: item["id"]["videoId"], search_list_items))
            ),
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

        search_item = next(
            filter(
                lambda search_item: search_item["id"]["videoId"] == video_id,
                search_list_items,
            )
        )

        live_broadcast_content = search_item["snippet"].get("liveBroadcastContent")
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
    active_search_item = next(
        filter(
            lambda search_item: search_item["id"]["videoId"] == active_video_id,
            search_list_items,
        ),
        {},
    )

    snippet_obj = active_video_item.get("snippet")
    live_streming_details_obj = active_video_item.get("liveStreamingDetails", {})
    live_broadcast_content = active_search_item.get("snippet", {}).get(
        "liveBroadcastContent"
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
                    "isOnair": live_broadcast_content == "live",
                },
                "channel": {
                    "id": channel_id,
                    "name": channel_name,
                    "url": channel_url,
                    "thumbnails": channel_thumbnails,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
