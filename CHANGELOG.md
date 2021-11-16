# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [Unreleased]
- Create a route for unrealized PnL that shows all positions in one place. Add hyperlinks from sidebar, dashboard and coin pages
- Match all of the details from [passivbot](https://github.com/enarjord/passivbot)s telegram commands `/position` and `/open_orders` commands
- Add DCA tracker / warnings when running out of buys
- Store total BNB value from wallet and notify if it falls below a threshold
- Store and display historical unrealized PnL
- Tidy up repeated code into functions

## 2021-11-16
### Changed
- Fixed issue highlighted by [@ltorres6](https://github.com/ltorres6) where coins wouldn't show as active unless there was an open buy/sell order and realised PNL

## 2021-11-14
### Added
- Income history page added, allows you to pull CSVs out of the income database table depending on the common timeframes used (today, week...)
- Totals and PBR added to the sidebar for active coins

## 2021-11-13
### Added
- Buy and sell position indicators for each active coin in the menu
- Mark price now displays on the active coin pages

### Changed
- SQL for latest order switched from `ORDER BY / LIMIT` to `MAX()`
- Repeated code removed for lastupdate and put into `get_lastupdate()`
- All of the headline values for profit will display with 2dp i.e. `4.00` instead of `4.0`
- Rounded the position price on coins page to 5dp maximum
- Split the coin menu into `active` and `inactive`

## 2021-11-12
### Changed
- Auto refresh after 60 seconds now on a page by page basis rather than whole site
- Line charts now have padding at the top for when you hit ATH profits and can't see the numbers because the chart cuts off
- Positions/orders now uses datatables instead of a list within a card meaning it is now sortable and each value is individually identifiable (was previously volume@price)

## 2021-11-11
### Added
- Added `favicon.ico` and referenced in base template
- Add last update time to `dashboard` and `coin` pages (pulls the last order creation time)
- Added automatic page refresh every 60 seconds (to show the latest information from data pull)

### Changed
- Renamed variable `result` to `all_fees` in `app.py`
- Merge the scraper into the app through the asyncio library - completed in PR by [@s0undt3ch](https://github.com/s0undt3ch)

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
