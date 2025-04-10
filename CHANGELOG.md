# Changelog

## [2.1.0] - 2025-04-10
- Add iFVG (Inverse Fair Value Gap) strategy for EURUSD and GBPUSD
- Walk-forward validation: 15/16 OOS windows profitable for AMD
- Add FX cost model (commission + slippage) for IC Markets raw spreads

## [2.0.0] - 2025-01-15
- Port AMD strategy to EURUSD 1H (London-NY overlap, 12-16 UTC)
- Add EURUSD London ORB (07-08 UTC opening range)
- Optimal 7-strategy portfolio: Sharpe 2.49, MaxDD -2.63%

## [1.1.0] - 2024-09-30
- Add regime filter (optional, default off — marginal benefit on tested instruments)
- Fix stale sweep flags in AMD strategy causing spurious re-entries
- Add breakeven stop tests (tested and removed — degraded performance on all strategies)

## [1.0.0] - 2024-05-01
- Initial release: FVG, ORB, AMD strategies on QQQ 15M
- Walk-forward validation framework
- Optimal 3-strategy portfolio: Sharpe 1.86, MaxDD -7.39%
