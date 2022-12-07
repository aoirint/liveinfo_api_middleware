from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Literal
import json
import requests
from bs4 import BeautifulSoup


JST = ZoneInfo('Asia/Tokyo')


def dump_nicolive_community_live(
  nicolive_community_id: str,
  useragent: str,
  dump_path: Path,
):
  onair_response = requests.get(
    f'https://com.nicovideo.jp/api/v1/communities/{nicolive_community_id}/lives/onair.json',
    headers={
      'User-Agent': useragent,
    },
  )
  # onair_response.raise_for_status()
  is_onair = False
  if onair_response.status_code == 200:
    onair_data = json.loads(onair_response.text)
    onair_live = onair_data.get('data', {}).get('live', {})

    is_onair = onair_live.get('status') == 'ON_AIR'


  ogp_useragent = f'facebookexternalhit/1.1;Googlebot/2.1;{useragent}'

  watch_response = requests.get(
    f'https://live.nicovideo.jp/watch/co{nicolive_community_id}',
    headers={
      'User-Agent': ogp_useragent,
    },
  )
  watch_response.raise_for_status()

  bs = BeautifulSoup(watch_response.text, 'html5lib')
  json_ld_tag = bs.find('script', attrs={'type': 'application/ld+json'})
  json_ld_string = json_ld_tag.string

  json_ld_data = json.loads(json_ld_string)
  publication = json_ld_data.get('publication', {})
  author = json_ld_data.get('author', {})

  user_icon_tag = bs.select_one('#root > div > div.___program-information-area___2mmJb > div.___program-information-header-area___3F--P > div > div.___user-summary___1PSFe.___user-summary___1gieM.user-summary > div.___thumbnail-area___1z7XZ.thumbnail-area > a > img')
  user_icon_url = user_icon_tag.get('src') if user_icon_tag is not None else None

  community_name_tag = bs.select_one('#root > div > div.___program-information-area___2mmJb > div.___program-information-body-area___1D8P9 > div.___program-information-side-area___1XQ24 > div > div > div.___description-area___2F98E > div > a')
  community_name = community_name_tag.text if community_name_tag is not None else None
  community_url = community_name_tag.get('href') if community_name_tag is not None else None

  community_icon_tag = bs.select_one('#root > div > div.___program-information-area___2mmJb > div.___program-information-body-area___1D8P9 > div.___program-information-side-area___1XQ24 > div > div > div.___description-area___2F98E > a > img')
  community_icon_url = community_icon_tag.get('src') if community_icon_tag is not None else None

  start_time_string = publication.get('startDate')
  end_time_string = publication.get('endDate')

  og_url_tag = bs.find('meta', attrs={'property': 'og:url'})
  program_url = og_url_tag.get('content') if og_url_tag is not None else None

  dump_path.parent.mkdir(parents=True, exist_ok=True)
  dump_path.write_text(
    json.dumps(
      {
        'program': {
          'title': json_ld_data.get('name'),
          'description': json_ld_data.get('description'),
          'url': program_url,
          'thumbnails': json_ld_data.get('thumbnailUrl'),
          'startTime': start_time_string,
          'endTime': end_time_string,
          'isOnair': is_onair,
        },
        'community': {
          'name': community_name,
          'url': community_url,
          'iconUrl': community_icon_url,
        },
        'user': {
          'name': author.get('name'),
          'url': author.get('url'),
          'iconUrl': user_icon_url,
        },
      },
      ensure_ascii=False,
    ),
    encoding='utf-8',
  )


def dump_ytlive_channel_live(
  ytlive_channel_id: str,
  ytlive_api_key: str,
  useragent: str,
  dump_path: Path,
):
  pass
