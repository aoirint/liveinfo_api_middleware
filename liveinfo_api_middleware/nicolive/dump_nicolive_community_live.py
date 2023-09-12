import json
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel

JST = ZoneInfo("Asia/Tokyo")


class NicoliveCommunityLiveOnairLive(BaseModel):
    status: str


class NicoliveCommunityLiveOnairData(BaseModel):
    live: NicoliveCommunityLiveOnairLive | None = None


class NicoliveCommunityLiveOnair(BaseModel):
    data: NicoliveCommunityLiveOnairData | None = None


class NicoliveWatchJsonLdPublication(BaseModel):
    startDate: str | None = None
    endDate: str | None = None


class NicoliveWatchJsonLdAuthor(BaseModel):
    name: str | None = None
    url: str | None = None


class NicoliveWatchJsonLd(BaseModel):
    name: str | None = None
    thumbnailUrl: list[str] | None = None
    publication: NicoliveWatchJsonLdPublication | None = None
    author: NicoliveWatchJsonLdAuthor | None = None


class NicoliveWatchEmbeddedDataSupplierIcons(BaseModel):
    uri150x150: str | None = None


class NicoliveWatchEmbeddedDataSupplier(BaseModel):
    icons: NicoliveWatchEmbeddedDataSupplierIcons | None = None


class NicoliveWatchEmbeddedDataProgram(BaseModel):
    description: str | None = None
    supplier: NicoliveWatchEmbeddedDataSupplier | None = None


class NicoliveWatchEmbeddedDataSocialGroup(BaseModel):
    id: str | None = None
    name: str | None = None
    thumbnailImageUrl: str | None = None
    socialGroupPageUrl: str | None = None


class NicoliveWatchEmbeddedData(BaseModel):
    program: NicoliveWatchEmbeddedDataProgram | None = None
    socialGroup: NicoliveWatchEmbeddedDataSocialGroup | None = None


def dump_nicolive_community_live(
    nicolive_community_id: str,
    useragent: str,
    dump_path: Path,
) -> None:
    onair_response = requests.get(
        f"https://com.nicovideo.jp/api/v1/communities/{nicolive_community_id}/lives/onair.json",
        headers={
            "User-Agent": useragent,
        },
    )
    # onair_response.raise_for_status()
    is_onair = False
    if onair_response.status_code == 200:
        onair_live = NicoliveCommunityLiveOnair.model_validate(onair_response.json())
        if onair_live.data is not None:
            if onair_live.data.live is not None:
                is_onair = onair_live.data.live.status == "ON_AIR"
    else:
        # {'meta': {'status': 403, 'error-code': 'PERMISSION_DENIED', 'error-message': '非公開コミュニティの生放送情報はフォロワー以外取得できません。'}}  # noqa: B950
        print(f"ERRORED: {onair_response.text}")

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

    json_ld_dict = json.loads(json_ld_string)
    json_ld = NicoliveWatchJsonLd.model_validate(json_ld_dict)

    embedded_data_tag = bs.find(id="embedded-data")
    embedded_data_string = embedded_data_tag.attrs.get("data-props")
    embedded_data_dict = json.loads(embedded_data_string)
    embedded_data = NicoliveWatchEmbeddedData.model_validate(embedded_data_dict)

    user_icon_url: str | None = None
    description: str | None = None
    if embedded_data.program is not None:
        if embedded_data.program.supplier is not None:
            if embedded_data.program.supplier.icons is not None:
                user_icon_url = embedded_data.program.supplier.icons.uri150x150

        description_html = embedded_data.program.description

        bs = BeautifulSoup(description_html, "html5lib")

        # keep line breaks
        for br_tag in bs.select("br"):
            br_tag.replace_with("\n")

        description = bs.text

    community_name: str | None = None
    community_url: str | None = None
    community_icon_url: str | None = None
    if embedded_data.socialGroup is not None:
        community_name = embedded_data.socialGroup.name
        community_url = embedded_data.socialGroup.socialGroupPageUrl
        community_icon_url = embedded_data.socialGroup.thumbnailImageUrl

    start_time_string: str | None = None
    end_time_string: str | None = None
    if json_ld.publication is not None:
        start_time_string = json_ld.publication.startDate
        end_time_string = json_ld.publication.endDate

    author_name: str | None = None
    author_url: str | None = None
    if json_ld.author is not None:
        author_name = json_ld.author.name
        author_url = json_ld.author.url

    og_url_tag = bs.find("meta", attrs={"property": "og:url"})
    program_url = og_url_tag.get("content") if og_url_tag is not None else None

    dump_path.parent.mkdir(parents=True, exist_ok=True)
    dump_path.write_text(
        json.dumps(
            {
                "program": {
                    "title": json_ld.name,
                    "description": description,
                    "url": program_url,
                    "thumbnails": json_ld.thumbnailUrl,
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
                    "name": author_name,
                    "url": author_url,
                    "iconUrl": user_icon_url,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
