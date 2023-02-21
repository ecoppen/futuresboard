
<h1 align="center">Futuresboard</h1>
<p align="center">
A python (3.7+) based scraper and dashboard to monitor the performance of your Binance or Bybit Futures account.<br>
</p>
<p align="center">
<img alt="GitHub Pipenv locked Python version" src="https://img.shields.io/github/pipenv/locked/python-version/ecoppen/futuresboard"> 
<a href="https://github.com/ecoppen/futuresboard/blob/main/LICENSE"><img alt="License: GPL v3" src="https://img.shields.io/badge/License-GPLv3-blue.svg">
<a href="https://app.fossa.com/projects/git%2Bgithub.com%2Fecoppen%2Ffuturesboard?ref=badge_shield"><img alt="FOSSA Status" src="https://app.fossa.com/api/projects/git%2Bgithub.com%2Fecoppen%2Ffreqdash.svg?type=shield"></a>
<a href="https://codecov.io/gh/ecoppen/futuresboard"><img src="https://codecov.io/gh/ecoppen/futuresboard/branch/main/graph/badge.svg?token=4XCZZ6MFPH"/></a>
<a href="https://codeclimate.com/github/ecoppen/futuresboard/maintainability"><img src="https://api.codeclimate.com/v1/badges/ee2153da0bf153eb80bb/maintainability"/></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

## Getting started

- Create a fresh new API on Binance or Bybit, with only read rights.
- Clone this repository: `git clone https://github.com/ecoppen/futuresboard.git`
- Navigate to the futuresboard directory: `cd futuresboard`
- Install dependencies `python -m pip install .`. For developing, `python -m pip install -e .[dev]`
- Copy `config/config.json.example` to `config/config.json` and add your new api key and secret: `nano config.json`
- Collect your current trades by running `futuresboard --scrape-only`. If you want to monitor the weight usage (see below).
- By default, when launching the futuresboard web application, a separate thread is also started to continuously collect new trades.
  Alternatively, setup the scraper on a crontab or alternative to keep the database up-to-date: `crontab -e` then `*/5 * * * * futuresboard --scrape-only` (example is every 5 minutes, change to your needs)
  In this case, don't forget to pass `--disable-auto-scraper`.
- Start a screen or alternative if you want the webserver to persist: `screen -S futuresboard`
- Start the futuresboard web application `futuresboard`
- Navigate to the IP address shown e.g. `http://127.0.0.1:5000/`. These settings can be changed by passing `--host` and/or `--port` when running the above command

Currently only Binance and Bybit Futures are supported - as those are supported by passivbot.

## API weight usage - Binance

- Reminder: Binance API allows you to consume up to `1200 weight / minute / IP`.
- Account: Fetching account information costs `5` weight per run
- Income: Fetching income information costs `30` weight per 1000 (initial run will build database, afterwards only new income will be fetched)
- Orders: Fetching open order information costs `40` weight per run
- The scraper will sleep for a minute when the rate exceeds `800 within a minute`

## API weight usage - Bybit
- Account/Income/Positions: Fetching account information or positions costs `1` weight per run with a maximum combination allowed of `120/min`. Income can be fetched in batches of 50 (initial run will build database, afters only new income will be fetched)
- Orders: Fetching open order information costs `1` weight per symbol with a maximum allowed of `600/min`
- The scraper will sleep for a minute when the rate exceeds `100 within a minute`

## Customising the dashboard
The `/config/config.json` file allows you to customise the look and feel of your dashboard as follows:
- `AUTO_SCRAPE_INTERVAL` is set to 300 seconds, this value can be adjusted between `60` and `3600`
- `NAVBAR_TITLE` changes the branding in the top left of the navigation (see below)
- `NAVBAR_BG` changes the colour of the navigation bar, acceptable values are: `bg-primary`, `bg-secondary`, `bg-success`, `bg-danger`, `bg-warning`, `bg-info` and the default `bg-dark`
- `PROJECTIONS` changes the percentage values on the projections page. `1.003` equates to `0.3%` daily and `1.01` equates to `1%` daily.

For example, setting `"NAVBAR_TITLE": "Custom title"` and `"NAVBAR_BG": "bg-primary",` would result in:
<img width="1314" src="https://user-images.githubusercontent.com/51025241/145480528-408dff64-1742-41ea-baac-89bb5458d406.png">
<img width="500" src="https://user-images.githubusercontent.com/51025241/145609351-631db009-ac04-47c9-ae82-0d76af0362d2.png">
## Screenshots
<img width="600" alt="dashboard" src="https://user-images.githubusercontent.com/51025241/147236951-c87d1b2e-9eee-49bb-bc44-1769b9756f45.png">
<img width="600" alt="calendar" src="https://user-images.githubusercontent.com/51025241/147236947-426ee144-fe30-4041-93b0-36a3073a9233.png">
<img width="550" alt="coin" src="https://user-images.githubusercontent.com/51025241/147359139-e2ba33c9-0d10-4b09-a235-c9979658dd9b.png">
<img width="600" alt="1h chart" src="https://user-images.githubusercontent.com/51025241/147358812-b860f5db-a867-4bf4-b98e-b467bb928a25.png">
<img width="600" alt="history" src="https://user-images.githubusercontent.com/51025241/147236956-7b427c72-0a8b-443b-bd24-3eaef3246895.png">
<img width="600" alt="positions" src="https://user-images.githubusercontent.com/51025241/147236958-160a4cd8-c461-46d2-87d1-560d89207a93.png">
<img width="600" alt="projection" src="https://user-images.githubusercontent.com/51025241/147236959-7ca52391-f6bb-496e-bba2-5b914ee333c7.png">

## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fecoppen%2Ffuturesboard.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fecoppen%2Ffuturesboard?ref=badge_large)

## Alternative dashboards
- https://github.com/hoeckxer/exchanges_dashboard
- https://github.com/SH-Stark/trading-dashboard
