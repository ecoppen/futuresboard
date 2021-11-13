# futuresboard
A python based scraper and dashboard to monitor the performance of your Binance Futures account. A local sqlite3 database `config/futures.db` will be created and automatically updated by the scraper every 5 minutes.

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
- Navigate to the IP address shown e.g. `http://127.0.0.1:5000/`

Currently only Binance and Futures are supported.

## API weight usage

- Reminder: Binance API allows you to consume up to `1200 weight / minute / IP`.
- Account: Fetching account information costs `5` weight per run
- Income: Fetching income information costs `30` weight per 1000 (initial run will build database, afterwards only new income will be fetched)
- Orders: Fetching open order information costs `40` weight per run
- The scraper will sleep for a minute when the rate exceeds `800 within a minute`

## Screenshots
<img width="1346" alt="dashboard1" src="https://user-images.githubusercontent.com/51025241/141650366-a7f667c3-5699-4445-9e7f-b4fabf24278f.png">
<img width="1346" alt="dashboard2" src="https://user-images.githubusercontent.com/51025241/141650367-930947f8-8449-4ced-a46f-8abc6e93f79f.png">

## Alternative dashboards

- https://github.com/hoeckxer/exchanges_dashboard
- https://github.com/SH-Stark/trading-dashboard
