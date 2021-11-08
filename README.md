# futuresboard
A python based scraper and dashboard to monitor the performance of your Binance Futures account

## Getting started

- Create a fresh new API on Binance, with only read rights.
- Install the flask library: `pip install flask`
- Clone this repository: `git clone https://github.com/ecoppen/futuresboard.git`
- Navigate to the futuresboard directory: `cd futuresboard`
- Edit the config.json file, adding in your new api key and secret: `nano config.json`
- Setup the scraper on a crontab or alternative: `crontab -e` then `*/5 * * * * /usr/bin/python ~/futuresboard/scraper.py` (every 5 minutes)
- Start flask `flask run`
- Navigate to the IP address shown e.g. `http://127.0.0.1:5000/`

Currently only Binance and Futures are supported.

## API weight usage

- Reminder: Binance API allows you to consume up to `1200 weight / minute / IP`.
- Account: Fetching account information costs `5` weight per run
- Income: Fetching income information costs `30` weight per 1000
- Orders: Fetching open order information costs `40` weight per run
- The scraper will sleep for a minute when the rate exceeds `800 within a minute`

## Alternative dashboards (my inspiration)

- https://github.com/hoeckxer/exchanges_dashboard
- https://github.com/SH-Stark/trading-dashboard
