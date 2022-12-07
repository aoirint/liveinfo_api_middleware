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
  ogp_useragent = f'facebookexternalhit/1.1;Googlebot/2.1;{useragent}'

  watch_response = requests.get(
    f'https://live.nicovideo.jp/watch/{nicolive_community_id}',
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
  start_time = datetime.fromisoformat(start_time_string) if start_time_string is not None else None
  end_time_string = publication.get('endDate')
  end_time = datetime.fromisoformat(end_time_string) if end_time_string is not None else None

  now = datetime.now(tz=JST)

  og_url_tag = bs.find('meta', attrs={'property': 'og:url'})
  program_url = og_url_tag.get('content') if og_url_tag is not None else None

  embedded_data_tag = bs.select_one('#embedded-data')
  embedded_data_props = embedded_data_tag.get('props', {}) if embedded_data_tag is not None else {}
  print(embedded_data_props) # FIXME: == {}, for bot HTTP request

  # タイムシフトの状態を確認する
  # programTimeshift.publiction.status = Before, Open, End, {None}
  # if timeshift is unpublished, noTimeshiftProgram is in userProgramWatch.rejectedReasons
  program_timeshift_status = embedded_data_props.get('programTimeshift', {}).get('publication', {}).get('status')

  user_program_watch_rejected_reasons = embedded_data_props.get('userProgramWatch', {}).get('rejectedReasons', [])

  # status = scheduled, live, timeshiftAvailable, timeshiftExpired, timeshiftUnpublished
  status: Literal['scheduled', 'live', 'timeshiftAvailable', 'timeshiftExpired', 'timeshiftUnpublished']
  if 'noTimeshiftProgram' in user_program_watch_rejected_reasons:
    # タイムシフト非公開番組
    status = 'timeshiftUnpublished'

  elif 'programNotBegun' in user_program_watch_rejected_reasons:
    # 予約番組
    status = 'scheduled'
  
  elif program_timeshift_status == 'Open':
    # タイムシフト公開中の番組
    status = 'timeshiftAvailable'

  elif program_timeshift_status == 'End':
    # タイムシフト公開が終了した番組
    status = 'timeshiftExpired'

  else:
    # 放送中の番組
    status = 'live'

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
          'status': status,
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
