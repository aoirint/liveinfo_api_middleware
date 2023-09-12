# liveinfo_api_middleware

各配信サイトから最新の配信情報（生放送情報）を取得して結果を返すAPIサーバ。
個人サイトなどに自分の配信情報を表示するために使うことを想定しています。

## 機能

### 対応サービス

- YouTube Live（YouTube Data API）
- ニコニコ生放送（非公式API）
  - 非公開コミュニティには対応していません

各サービスごとに1つのチャンネル（コミュニティ）のみ、データ取得できます。
同一のサービスで複数のチャンネル（コミュニティ）からデータを取得したい場合、必要な数のAPIサーバを起動してください（各サービスに過剰なアクセスが発生しないように注意してください）。

### キャッシュ

APIサーバから各サービスに過剰なアクセスが発生しないように、取得結果を1分間キャッシュします。キャッシュ間隔の間に再度APIサーバへのリクエストがあった場合、キャッシュした内容を返します。

## リリース

ソースコードおよびDockerイメージを配布しています。

- [GitHub](https://github.com/aoirint/liveinfo_api_middleware)
- [Docker Hub](https://hub.docker.com/r/aoirint/liveinfo_api_middleware)

## デプロイ手順

Docker Composeおよびリバースプロキシを使ったデプロイを想定しています。

### 1. 永続化ディレクトリを作成

永続化のため、`UID=2000`、`GID=2000`のデータディレクトリを作成します（Docker Volumeで代用可）。

```shell
mkdir -p data
sudo chown -R 2000:2000 data
```

### 2. .envファイルを作成

`template.env`を`.env`としてコピーして、設定します。設定項目については、[設定](#設定)の項目を参照してください。

### 3. Docker Composeサービスを起動

`docker-compose.yml`をコピーして、以下のコマンドを実行します。

```shell
sudo docker compose up -d
```

### 4. リバースプロキシを設定

必要に応じて、nginxやcloudflaredを設定してください。

## （開発者向け）実行手順

### 1. 永続化ディレクトリを作成

永続化のため、`UID=2000`、`GID=2000`のデータディレクトリを作成します（Docker Volumeで代用可）。

```shell
mkdir -p data
sudo chown -R 2000:2000 data
```

### 2. .envファイルを作成

`template.env`を`.env`としてコピーして、設定します。設定項目については、[設定](#設定)の項目を参照してください。

### 3. Dockerイメージをビルド

```shell
sudo docker build -t aoirint/liveinfo_api_middleware .
```

### 4. Dockerイメージを実行

```shell
sudo docker run --rm --init --env-file "$PWD/.env" -v "$PWD/data:/data" -p "127.0.0.1:8000:8000" aoirint/liveinfo_api_middleware
```

## 設定

環境変数または`.env`ファイルで設定します。

|項目|詳細|
|:--|:--|
|YTLIVE_CHANNEL_ID|取得するYouTubeチャンネルID（ハンドル名とは異なります）|
|YTLIVE_API_KEY|YouTube Data APIのAPIキー|
|YTLIVE_DUMP_PATH|YouTube配信のキャッシュの保存先（JSONファイルのパス）|
|NICOLIVE_COMMUNITY_ID|取得するニコニコ生放送のコミュニティID（`co`から始まるコミュニティIDのうち、数値の部分のみ）|
|NICOLIVE_DUMP_PATH|ニコニコ生放送のキャッシュの保存先（JSONファイルのパス）|
|CORS_ALLOW_ORIGINS|CORS設定（カンマ区切り）|
|HOST_DATA_DIR|（Docker Composeの場合のみ）ホスト側からコンテナにマウントするデータディレクトリのパス|
|HOST_PORT|（Docker Composeの場合のみ）ホスト側にバインドするAPIサーバのTCPポート番号|

## （開発者向け） ライブラリ管理

ライブラリ管理にはPoetryを使っています。

ライブラリに変更があった場合、以下のコマンドで`requirements.txt`を更新します（DockerイメージやCIで使われます）。

```shell
poetry export --without-hashes -o requirements.txt
poetry export --without-hashes --with dev -o requirements-dev.txt
```
