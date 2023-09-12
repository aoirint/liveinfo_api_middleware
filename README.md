# liveinfo_api_middleware

```shell
mkdir -p data
sudo chown -R 2000:2000 data

sudo docker buildx build -t aoirint/liveinfo_api_middleware .
sudo docker run --rm --init --env-file "$PWD/.env" -v "$PWD/data:/data" -p "127.0.0.1:8000:8000" aoirint/liveinfo_api_middleware
```

## Dependency management

```shell
poetry export --without-hashes -o requirements.txt
poetry export --without-hashes --with dev -o requirements-dev.txt
```
