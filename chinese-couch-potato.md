# Chinese Couch Potato Investing

In Canada, the [Canadian Couch Potato website](https://canadiancouchpotato.com/) offers great guidance for low-cost, passive, index investing. This note introduces example "couch potato" portfolios for Chinese investors.

PLEASE NOTE: THIS DOCUMENT IS NOT FINANCIAL ADVICE. INDIVIDUAL SITUATIONS VARY. USE AT YOUR OWN RISK.

**For the average person, a low-cost, indexed, strictly passive, well-diversified investment portfolio consisting of bonds and stocks is the best place to invest money.**

Here are a few important points:

- Periodic contributions and buy-and-hold strategies help overcome behavioural biases that often lead to suboptimal outcomes.

- Prevailing evidence shows that actively managed funds typically _underperform_ the market after adjusting for fees.

- Factor returns, discovered through backtesting, have historically existed. However, emerging evidence indicates that these excess returns tend to _diminish_ following the discovery's publication; It wouldn't be meaningful for the average person to take a bet on their persistence at a price of deviating from the cap-weighted version and higher fees.

- Market timing, a common investment pitfall, is one of the worst habits investors tend to fall into.

- Day trading and cryptocurrency, while frequently promoted on social media, are more akin to gambling in casinos than legitimate investment strategies - they're not good investments.

- Unfortunately, if not "day trading," many investors invest in individual stocks or sector funds, driven by market sentiment. This approach often leads to below-market returns.

## Available Asset Classes

The meaningful and accessible asset classes for investors in mainland China, available as mutual funds (公募基金) or ETFs[^1], are as follows:

- Domestic Bonds
  - Various segments available, including government, investment grade, high-yield and convertible.
- A Shares (Shanghai & Shenzhen Stock Exchanges)
  - CSI 300 index (沪深 300 指数), a large-cap index capturing 70% of capitalization.
  - CSI 800 index (中证 800 指数), large and mid caps accounting for 95% capitalization.
- Hong Kong-listed Stocks
  - Hang Seng Index (恒生指数), a large-cap index for stocks listed in the Hong Kong Stock Exchange representing 60% capitalization.
  - Hang Seng China Enterprises Index (恒生中国企业指数), comprises companies with close business ties to mainland China.
- U.S. Large Stocks
  - Nasdaq 100 and S&P 500 are available as QDII funds.

## Capital Market Assumptions

### Return and Volatility Assumptions

| Asset class       | Expected return (author) | Annualized Volatility (10-y historical) | Expected return (JPM) | Annualized Volatility (JPM) |
| ----------------- | -----------------------: | --------------------------------------: | --------------------: | --------------------------: |
| China Bond Market |                       3% |                                   1.79% |                  2.7% |                       2.75% |
| A Shares          |                       8% |                                  21.76% |                  5.5% |                      27.27% |
| HK-listed Stocks  |                       8% |                                  19.30% |                  5.7% |                      22.93% |
| U.S. Large Stocks |                       8% |                                  14.46% |                  4.5% |                      15.97% |

Note:

1. The returns are compound, nominal, before taxes and fees. Subtract 1% for fees and taxes to get an estimate of net returns.
2. JPM data are from [2026 Long-Term Capital Market Assumptions](https://am.jpmorgan.com/ca/en/asset-management/adv/insights/portfolio-insights/ltcma/).
3. 10-y historical volatilities are from:
   - China Bond Market: Factsheet for S&P China Bond Index
   - China A Shares: Factsheet for MSCI China A Onshore Index
   - HK-listed Stocks: Factsheet for MSCI Hong Kong-listed Southbound Index
   - U.S. Large Stocks: Factsheet for S&P 500 (in CNY)

### Correlations

| Asset Class       | A Shares | HK-listed Stocks | U.S. Large Stocks |
| ----------------- | -------: | ---------------: | ----------------: |
| A Shares          |        1 |             0.68 |              0.27 |
| HK-listed Stocks  |     0.68 |                1 |              0.41 |
| U.S. Large Stocks |     0.27 |             0.41 |                 1 |

Note:

1. Correlations are from [2026 Long-Term Capital Market Assumptions](https://am.jpmorgan.com/ca/en/asset-management/adv/insights/portfolio-insights/ltcma/).
2. Bonds are excluded, assuming 0 correlation with stocks.

## Representative Funds

The following low-cost index funds that are available for investors in mainland China are selected to represent these four asset classes.

| Asset Class             | Fund Name          | Ticker |
| ----------------------- | ------------------ | ------ |
| China Bond Market       | 易方达中债新综指 A | 161119 |
| A Shares                | 易方达中证 800ETF  | 515810 |
| Hong Kong-listed Stocks | 华夏沪港通恒生 ETF | 513660 |
| U.S. Large Stocks       | 摩根标普 500 指数  | 017641 |

Note:

1. These are examples; many alternatives exist.

## Model Portfolios

The model portfolios are derived from running portfolio optimization (maximum Sharpe, minimum variance), with some subjective adjustments.

Allocating a portion to international stocks, especially U.S. equities, is crucial for diversification and volatility reduction.

Those who invest solely in A Shares (or A+H Shares) tend to experience poorer risk-adjusted returns — A standard deviation of 20% is very high for most people. A portfolio consisting just a few A-Share stocks typically has volatility a lot more than 20%, with the expected return being the same.

Like investors in other markets, Chinese investors should consider an optimal home bias. Allocating between 50-90% of the equity portion to international stocks (U.S. equities) is desirable. The model portfolios suggest a 15/15/70 split for Shanghai & Shenzhen/HK/US, which serves as a good starting point.

### 20% Stocks/80% Bonds "Income"

```mermaid
pie
"China Bond Market" : 80
"CSI 800": 3
"Hang Seng Index" : 3
"S&P 500" : 14
```

### 40% Stocks/60% Bonds "Conservative"

```mermaid
pie
"China Bond Market" : 60
"CSI 800" : 6
"Hang Seng Index" : 6
"S&P 500" : 28
```

### 60% Stocks/40% Bonds "Balanced"

```mermaid
pie
"China Bond Market" : 40
"CSI 800" : 9
"Hang Seng Index" : 9
"S&P 500" : 42
```

### 80% Stocks/20% Bonds "Growth"

```mermaid
pie
"China Bond Market" : 20
"CSI 800" : 12
"Hang Seng Index" : 12
"S&P 500" : 56
```

### 100% Stocks "Aggressive"

```mermaid
pie
"CSI 800" : 15
"Hang Seng Index" : 15
"S&P 500" : 70
```

[^1]: Bank term deposits (定期存款) and direct real estate investing (投资房) are "meaningful" options but they are not available as mutual funds or ETFs. Another option is banks' wealth management products (理财产品); they're not as transparent as mutual funds (公募基金) mentioned in the note. I wouldn't recommend any of these: privately offered funds (私募基金), segregated funds (储蓄型 / 投资型保险), nor private equities (私募股权 / 信托).
