# futuresboard
A python (3.7+) based scraper and dashboard to monitor the performance of your Binance Futures account.<br>
<sub>Note: A local sqlite3 database `config/futures.db` will be created and automatically updated by the scraper every 5 minutes.</sub>

[Change log](https://github.com/ecoppen/futuresboard/blob/main/CHANGELOG.md)

## Getting started

- Create a fresh new API on Binance, with only read rights.
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

Currently only Binance and Futures are supported.

## API weight usage

- Reminder: Binance API allows you to consume up to `1200 weight / minute / IP`.
- Account: Fetching account information costs `5` weight per run
- Income: Fetching income information costs `30` weight per 1000 (initial run will build database, afterwards only new income will be fetched)
- Orders: Fetching open order information costs `40` weight per run
- The scraper will sleep for a minute when the rate exceeds `800 within a minute`

## Customising the dashboard
The `/config/config.json` file allows you to customise the look and feel of your dashboard as follows:
- `AUTO_SCRAPE_INTERVAL` is set to 300 seconds, this value can be adjusted between `60` and `3600`
- `NAVBAR_TITLE` changes the branding in the top left of the navigation (see below)
- `NAVBAR_BG` changes the colour of the navigation bar, acceptable values are: `bg-primary`, `bg-secondary`, `bg-success`, `bg-danger`, `bg-warning`, `bg-info` and the default `bg-dark`
<img width="500" src="https://user-images.githubusercontent.com/51025241/145609351-631db009-ac04-47c9-ae82-0d76af0362d2.png">
- `PROJECTIONS` changes the percentage values on the projections page. `1.003` equates to `0.3%` daily and `1.01` equates to `1%` daily.

For example, setting `"NAVBAR_TITLE": "Custom title"` and `"NAVBAR_BG": "bg-primary",` would result in:
<img width="1314" src="https://user-images.githubusercontent.com/51025241/145480528-408dff64-1742-41ea-baac-89bb5458d406.png">
## Screenshots
<img width="1330" src="https://user-images.githubusercontent.com/51025241/145480467-0c1c473a-90f8-42fd-bdb0-071dc0f096f9.png">
<img width="1330" src="https://user-images.githubusercontent.com/51025241/145480501-86deab0e-55fe-48fa-910f-7cae679664bb.png">
<img width="1330" src="https://user-images.githubusercontent.com/51025241/145480517-61d5fd40-22d4-4887-9307-7689d1303138.png">

## Alternative dashboards

- https://github.com/hoeckxer/exchanges_dashboard
- https://github.com/SH-Stark/trading-dashboard
