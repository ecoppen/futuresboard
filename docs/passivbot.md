# passivbot

[Passivbot](https://www.passivbot.com/en/latest/) is a fully automated trading bot built in Python (3.8 for most things, 3.8+ for live) by [@enarjord](https://github.com/enarjord/).

It was designed to provide a stable and low-risk profit avenue without manual actions, however it can also be used in a high-risk way if you aren't careful (or if you want to do so).

Passivbot trades in futures (7x) or spot markets on either Binance or Bybit, using grid trading.

This guide will focus on some of the common issues people run into when jumping into a trading bot, visit the official website for instructions on getting setup.

## Risks

!!! danger
    You should never trade with money you cannot afford (or are afraid) to lose. As with every bot, you are responsible for how it is configured and therefore how it performs, win or lose.

On futures markets with leverage, passivbot may expose more than 100% of the wallet's funds. To measure a position's risk, passivbot finds the ratio of position size to total unleveraged balance.

The formula for Position cost to Balance Ratio (PBR) is:
`pbr = (position_size * position_price) / unleveraged_wallet_balance`

!!! info
    PBR is no longer referred to within the docs or community, instead Wallet Exposure (WE) is used instead. The concept is similar and therefore these calculations are still pertinent.

`pbr==0.0` means no position
`pbr==1.0` means 100% of unleveraged wallet balance is in position.
`pbr==4.0` means 400% of unleveraged wallet balance is in position.
Each bot is configured with a parameter pbr_limit, greater than which the bot will not allow a position's pbr to grow. Having multiple bots active at the same time will mean a larger exposure, so beware as having `3 bots at 1.0 each == 10 bots at 0.3 each`

Bankruptcy is defined as when equity `(balance + unrealized_pnl) == 0.0`, that is, when total debt is equal to total assets.

Liquidation happens when the exchange force closes a position to avoid it going into negative equity. This usually happens before actual bankruptcy is reached, in order for exchange to cover slippage costs.

Bankruptcy price may be calculated from position and balance.

`pbr==1.0`, bankruptcy price is zero.
`pbr==2.0`, bankruptcy price is 50% lower than position price.
`pbr==3.0`, bankruptcy price is 33.33% lower than position price.
`pbr==10.0`, bankruptcy price is 10% lower than position price.

## Profit expectations

Passivbot can be run in a high risk, high reward mode by running a high leverage and high PBR. Similarly it can be run in a low risk, low reward mode by not altering the leverage (default is 7x) and lowering the PBR.

!!! warning
    Try to avoid the lure of high ADG by using high leverage, high PBR or a high risk configuration as they are more prone to liquidation in times where the market is crashing downwards.

Generally you should pay attention to the percentage of profits your bot(s) make rather than absolute figures. This allows you to understand the effect of changing your wallet size, make predictions for future profits if consistently maintained and compare performance against others running similar coins.

When first starting out you need to think realistically about your profit expectations and adjust them over time as you understand the process the bot goes through and you hit your targets. Below are some targets for you to begin with and after ticking off each one, move onto the next.
1 month target - $5/$6/$8 - Cover the cost of running the bot
1 month target - 2% - Beat your banks yearly interest rate in a month
1 month target - 8% - Beat your banks yearly interest rate 4x over in a month
If you've managed to do all of these then the next goal is to maintain it before thinking about new targets but honestly, is 4x your banks yearly interest rate in one month not enough?! Remember that profits are compounding. Below are some examples using these figures on different wallets
$1000 at 2% per year results in $1020.20 after one year. At 2% monthly results in $1271.15 and at 8% $2,608.41.
$5000 at 2% per year results in $5101 after one year. At 2% monthly results in $6,355.74 and at 8% $13,042.04.
$10000 at 2% per year results in $10,202.01 after one year. At 2% monthly results in $12,711.49 and at 8% $26,084.07.
The important part is not get 20% in your first month then be liquidated (-100%) in the next because you went for higher risk and reward.

## Coin selection
You can select any coin pairings that are listed on your exchange however there are certain factors that make coins more profitable and/or suitable for your particular setup.

The first consideration you need to have is the price of the coin. Passivbot will create a grid of orders that increase with each entry, for example the first might be 1 unit, the second might be 2, the third is 4 and the last is 8. If this is the case, once all of the units have been bought you would have 15 units. If you were running BTC at a rate of $45000 your wallet would need to be able to deal with at least $675000 ($45000 * 15) which even at 7x leverage is a lot. Similarly if you went for AVAX at $100 per unit you would need to be able to cover $1500. Taking this into consideration alongside a wallet of $1000 and a PBR setting of 0.2 ($200 available of the $1000) you can see why considering the price is important. It is important to note that these examples are assuming that you can only buy 1 unit each time which is true of coins like AVAX and SOL however BTC allows you to buy small amounts e.g. 0.0001 so therefore can be still be used on smaller wallets.

!!! info
    Coins like ADA ($0.36), HOT ($0.002), VET ($0.03) and XLM ($0.08) are good starting points for optimising and backtesting with smaller (<= $1000) wallets because of their relatively accessible price however you still need to check them!

The next consideration you should think about is the volume of the coin compared to the market cap and the volatility of the coin itself. ADA was listed above as a good starting point however if it is acting like a stablecoin (small volatility on a daily/weekly/monthly basis) then it won't be suitable. If the volume of a coin over 24 hours was 815989512 and the market cap was 1145588013 then the volatility would be 0.71 which shows quite a high level of volatility and might be suitable. This information and more can be viewed at websites like coinmarketcap.com

!!! warning
    Whichever coin you select and for whatever reason, you should optimise and backtest thoroughly before going live.
