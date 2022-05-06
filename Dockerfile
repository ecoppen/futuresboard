FROM python:3.8-buster

LABEL maintainer="ecoppen" \
	org.opencontainers.image.url="https://github.com/ecoppen/futuresboard" \
	org.opencontainers.image.source="https://github.com/ecoppen/futuresboard" \
	org.opencontainers.image.vendor="ecoppen" \
	org.opencontainers.image.title="futuresboard" \
	org.opencontainers.image.description="Dashboard to monitor the performance of your Binance or Bybit Futures account" \
	org.opencontainers.image.licenses="GPL-3.0"

WORKDIR /usr/src/futuresboard
COPY . .
RUN python -m pip install .

CMD futuresboard