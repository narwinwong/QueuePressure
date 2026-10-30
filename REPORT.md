# A fixed queue-pressure rule failed its development screen

## Economic question

Displayed queue imbalance may predict the next price change. An aggressive trader must buy at an ask and sell at a bid, with delay and costs. The question is whether the prediction survives those charges. [Gould and Bonart](https://arxiv.org/abs/1512.03492) study next-midprice prediction; [Cont, Kukanov and Stoikov](https://arxiv.org/abs/1011.6402) study order-flow impact. Their results do not establish profitability for this rule. A search excerpt exposed a third-party repository using this public sample; it was not opened or copied. There is no novelty claim.

## Fixed reference

Source clocks before 13:30 supplied 68,087 paired rows and 61,994 completed timestamp groups. Decisions ran every ten seconds from 09:35 through 13:29:40. The last completed group strictly before each decision had to be no more than one second old. Entry required bid quantity at least four times ask quantity.

The entry reference used the first completed timestamp group at or after the order arrival. If that group was ineligible or more than 500 ms late, entry was canceled without searching forward. Otherwise the reference bought one share at its ask. The exit request followed one second after entry and incurred another order delay before selling at the first eligible bid. Invalid exit states delayed the exit instead of deleting the trade. Tied timestamps used the final state and conservative whole-group eligibility.

Primary delay was 250 ms per order, with $0.003 fees and $0.01 adverse charge per side. Those are assumptions, not verified 2012 execution costs. Spread crossing is already included in the bid/ask legs.

## Observed conditional margins

| Scenario | Round trips | Sum, USD | Mean per round trip, USD | Exits over two seconds |
| --- | ---: | ---: | ---: | ---: |
| No additional charges | 117 | -20.610 | -0.17615 | 40 |
| Primary | 117 | -23.652 | -0.20215 | 40 |
| Double fees | 117 | -24.354 | -0.20815 | 40 |
| Double adverse charge | 117 | -25.992 | -0.22215 | 40 |
| One-second order delay | 126 | -25.276 | -0.20060 | 126 |

Primary block margins were -$7.702, -$4.698, -$7.184 and -$4.068, on 32, 23, 39 and 23 round trips. Total and per-block support requirements passed. Absolute margin, positive block and exit-timing requirements failed. The fixed result is FIXED_REFERENCE_SCREEN_FAIL.

Of 1,409 primary decisions, 477 had stale or unusable signal states, 683 missed the pressure threshold, 132 were canceled before entry and 117 became completed trades. None overlapped a position.

The unfiltered primary control completed 494 round trips at -$99.514. Scaling it by the pressure policy's realized entry-price-times-holding exposure gives +$1.228692 of relative excess for the pressure rule. That favorable comparison does not overcome its negative margin against cash. Ex-post exposure scaling is not an executable fractional-share policy or exact risk match. The delay-stress relative comparison is negative.

## Interpretation and scope

These are conditional one-share quote margins, not funded PnL. Displayed depth does not guarantee a fill. Receiver timing, consolidated prices, historical fees, financing, settlement, tax and broker minimums remain unqualified. All five fixed scenarios are retained; none replaces the primary after results.

The events and trades from this single day are dependent. No bootstrap, Monte Carlo confidence claim or p-value is reported. The later session from source time 48,600 seconds remains economically sealed; earlier full-day technical QC exposure is disclosed. No threshold/horizon/sign reversal, regime rescue or out-of-sample analysis followed the failure. There is no verified market or prop-firm edge.
