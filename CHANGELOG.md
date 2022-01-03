# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [Unreleased]
- Match all of the details from [passivbot](https://github.com/enarjord/passivbot)s telegram commands `/position` and `/open_orders` commands
- Store and display historical unrealized PnL
- Tidy up repeated code into functions

## 2022-01-03
### Changed
- Added a composite key to the income table in the database to stop duplicates from being entered. This change will only be active on fresh databases/built from scratch. 
- Added the transactionId from Bybit to the list for future processing - this is a string whereas Binance uses integers. This needs to be managed to avoid more database deletions.

## 2021-12-27
### Changed
- Fixed an issue on history page where dowload buttons would cause 500 error when pressed
- Fixed an issue with bybit scraping to get latest trades. Still more to do here with regard to old trades looking back.

## 2021-12-25
### Changed
- Commas removed from `config.json.example` as the extra commas caused errors [@jontstaz](https://github.com/jontstaz)
- Inverse the colours for current buy/sells on the 15m, 1h, 4h and 1d charts to match green for buy and red for sell

## 2021-12-24
### Added
- Bybit now supported as an exchange, data will be scraped as best as possible however whole historical data doesn't seem possible currently.
- Candle chart with buy/sell lines now available on coin pages for 15m, 1h, 4h and 1d

### Changed
- Coin pages now have Average Down Calculator showing all the time, with specific distances away from position already calculated
- Income history page buttons fixed
- Positions page now has a table showing distance from next buys and all previous information

## 2021-12-10
### Changed
- Minor fixes and README updates regarding the latest changes made yesterday

## 2021-12-09
### Added
- The config file now has the ability to change the look and feel of the dashboard. The title can be changed using `NAVBAR_TITLE`, the background colour of the navigation bar can now be changed to a set of colours using `NAVBAR_BG` and the projection percentages can be changed to show more or less values as specified by the user with `PROJECTIONS`
- The config file can also be used to set the value of the `AUTO_SCRAPE_INTERVAL` between `60` and `3600` for more or less frequent updates depending on their needs
- Under the charts on the dashboard and coin pages there is now a summary showing either the `total profit` for that period or `number of coins active`
- Positions page now shows unrealised Profit and Loss for each coin

### Changed
- Tooltips were lost somewhere along the line for the values in the sidebar, these are reintroduced 
- Link to the repo in the footer was lost also, reintroduced

## 2021-12-07
### Changed
- Codebase overhauled by [@s0undt3ch](https://github.com/s0undt3ch) to use a blueprint which allows the multiple dashboards to be served 
- Hard coded URLs swapped to use `url_for` by  [@s0undt3ch](https://github.com/s0undt3ch)

## 2021-12-02
### Changed
- Timeframes no longer exist, instead there are start dates and end dates with a daterangepicker on all appropriate pages

## 2021-11-29
### Changed
- Added a fix for the graph on the dashboard that would only calculate the total - profit over a week and not the other tiemframes

## 2021-11-28
### Added
- Route added for balance projection over 365 days at fixed and average %, this can be accessed from the main dashboard page above the line chart
- Average down calculator now available on coin page (only shows when a coin has no more buy positions)

### Changed
- Changed 'Week' to be previous 7 days rather than 8

## 2021-11-21
### Changed
- Fixed issue that was reintroduced (new positions wouldn't show unless a buy/sell was present)
- Fixed issue where `positions` were not returned by API causing error which is now handled more gracefully
- Fixed issue where some coins were automatically hidden on the graph when too many were present - now resizes to fit

## 2021-11-20
### Added
- Table on history page to show all of the previously saved CSV files
- favicon2 (warning emoji) will replace favicon (rocket emoji) when no buys are left on an active coin
- New route added for `All positions` that shows every coin in one place. Accordian can be opened to see the orders relating to each position.

### Changed
- Active coins now have a red background if there are no buys left on an active coin
- Cards on the front page (profit for today, week, month and PnL) are now hyperlinked to their respective pages

## 2021-11-19
### Added
- Balance now displays on profit chart as requested by [@s0undt3ch](https://github.com/s0undt3ch)

## 2021-11-18
### Added
- Tooltips added on left menu for PBR, BUY, SELL by [@s0undt3ch](https://github.com/s0undt3ch)

### Changed
- Fixed issue highlighted by [@hungud](https://github.com/hungud) with no longer used route for `/coins/`
- Fixed issue with calculation for profit not including `FUNDING_FEES` so now if a coin is stuck and funding fees, it will show negative impact
- Changed the tooltips to use the bootstrap theme

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
