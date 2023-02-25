# Setup

## Cloning and installing
If the git framework is not installed already for downloading from GitHub, install with `apt-get install git` or through a package on [gitscm](https://git-scm.com/downloads)

Clone this repository: `git clone https://github.com/ecoppen/futuresboard.git`

Navigate to the futuresboard directory in a terminal/cmd: `cd futuresboard`

Install dependencies: `python -m pip install .` making sure to include the dot

Copy `config/config.json.example` to `config/config.json` and add your new api key and secret: `cp config/config.json.example config/config.json` and then `nano config.json`

## API Setup
It is highly recommended to setup an independent API key solely for the purpose of reading data and nothing extra. 

Limiting the IP address to your VPS/PC is highly recommended for added security.

Be sure to make a note of your `API Key` and `API Secret` for use in your server setup.

## Configuration
The `/config/config.json` file allows you to customise the look and feel of your dashboard as follows:

- `AUTO_SCRAPE_INTERVAL` is set to 300 seconds, this value can be adjusted between 60 and 3600
- `NAVBAR_TITLE` changes the branding in the top left of the navigation (see below)
- `NAVBAR_BG` changes the colour of the navigation bar, acceptable values are: bg-primary, bg-secondary, bg-success, bg-danger, bg-warning, bg-info and the default bg-dark
- `PROJECTIONS` changes the percentage values on the projections page. 1.003 equates to 0.3% daily and 1.01 equates to 1% daily.

## Scraping
Collect your current trades by running `futuresboard --scrape-only`.

Reminder: Binance API allows you to consume up to 1200 weight / minute / IP.

- Account: Fetching account information costs 5 weight per run
- Income: Fetching income information costs 30 weight per 1000 (initial run will build database, afterwards only new income will be fetched)
- Orders: Fetching open order information costs 40 weight per run
- The scraper will sleep for a minute when the rate exceeds 800 within a minute

## Running
Start the futuresboard web application `futuresboard`

Navigate to the IP address shown e.g. `http://127.0.0.1:5000/`. These settings can be changed by passing `--host` and/or `--port` when running the above command
