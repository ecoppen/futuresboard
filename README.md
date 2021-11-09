# futuresboard
A python based scraper and dashboard to monitor the performance of your Binance Futures account.

## Getting started

- Create a fresh new API on Binance, with only read rights.
- Install the flask library: `pip install flask`
- Clone this repository: `git clone https://github.com/ecoppen/futuresboard.git`
- Navigate to the futuresboard directory: `cd futuresboard`
- Edit the config.json file, adding in your new api key and secret: `nano config.json`
- Run the scraper if you want to monitor the weight usage (see below): `python scraper.py`
- Setup the scraper on a crontab or alternative to keep the database up-to-date: `crontab -e` then `*/5 * * * * /usr/bin/python ~/futuresboard/scraper.py` (example is every 5 minutes, change to your needs)
- Start a screen or alternative if you want the webserver to persist: `screen -S futuresboard`
- Start flask: `flask run`
- Navigate to the IP address shown e.g. `http://127.0.0.1:5000/`

Currently only Binance and Futures are supported.

## API weight usage

- Reminder: Binance API allows you to consume up to `1200 weight / minute / IP`.
- Account: Fetching account information costs `5` weight per run
- Income: Fetching income information costs `30` weight per 1000 (initial run will build database, afterwards only new income will be fetched)
- Orders: Fetching open order information costs `40` weight per run
- The scraper will sleep for a minute when the rate exceeds `800 within a minute`

## Screenshots
<img width="1346" alt="futuresboard1" src="https://user-images.githubusercontent.com/51025241/140821486-ead40b35-d4c2-4282-986d-76fe62f295a7.png">
<img width="1346" alt="futuresboard2" src="https://user-images.githubusercontent.com/51025241/140821400-4fb0efdd-fdba-4c0b-bc49-6a997775bbab.png">

## Alternative dashboards

- https://github.com/hoeckxer/exchanges_dashboard
- https://github.com/SH-Stark/trading-dashboard
