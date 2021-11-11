# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [Unreleased]
- Create a route for unrealized PnL that shows all positions in one place. Add hyperlinks from sidebar, dashboard and coin pages
- Change position/orders on coin page to use datatables
- Create a route for all incomes. Add datatables to page for filtering, sorting and exporting
- Merge the scraper into the app through the asyncio library [@s0undt3ch](https://github.com/s0undt3ch)
- Match all of the details from [passivbot](https://github.com/enarjord/passivbot)s telegram commands `/position` and `/open_orders` commands
- Add DCA tracker / warnings when running out of buys
- Store total BNB value from wallet and notify if it falls below a threshold
- Show current coin price on coin page
- Store and display historical unrealized PnL

## 2021-11-10
### Added
- Added `favicon.ico` and referenced in base template
- Add last update time to `dashboard` and `coin` pages (pulls the last order creation time)

### Changed
- Renamed variable `result` to `all_fees` in `app.py`

## 2021-11-10
### Added
- Added this `CHANGELOG.md` 

## 2021-11-09
### Added
- Added recommended command for docker in `README.md` [@MiKE0#7135]
- Added hyperlinks to the bar charts to redirect to the page for that specific coin
- Added numeric values on top of the line and within bar charts

### Changed
- Changed the required libraries to include `requests` in `README.md` [@MiKE0#7135]

## 2021-11-08
### Added
- `README.md` and `LICENSE.md` created
- `app.py` and `scraper.py` python files uploaded
- `config.json` json file uploaded
- `static/styles/dashboard.css`and `static/styles/sidebars.css` CSS files uploaded
- `templates/base.html`, `templates/coin.html`, `templates/date.html`, `templates/error.html`, `templates/home.html` and `templates/showall.html` HTML files uploaded

### Changed
- README.md updated with suggested running instructions
