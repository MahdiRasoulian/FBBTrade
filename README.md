# FBBTrade — Fibonacci Bollinger Bands Interactive Trading System

FBBTrade is a modular Python foundation for a semi-automated Fibonacci Bollinger Bands trading workflow with Telegram human approval and MT5 integration boundaries. It is not a profitability claim and it does not assume every outer-band touch is a reversal.

## Senior trader reasoning

FBB can be useful on liquid M5 markets such as XAUUSD because VWMA anchors price to volume-weighted participation while standard-deviation bands describe current volatility expansion. Outer 0.618, 0.764, and 1.000 bands often mark stretched location, but a strong trend or news impulse can keep price pinned near an outer band. A touch is therefore only a market-location event. Reversal logic requires reaction evidence such as return inside the band or closed-candle rejection. The VWMA basis can act as a mean-reversion target when volatility normalizes, but trend context, session liquidity, spread, slippage, and gold news spikes can invalidate that assumption. This project preserves uncertain trading ideas as configuration rather than hard-coded claims.

## Architecture

`config -> market_data -> indicators/fbb -> signals -> entry -> risk -> chart -> telegram -> execution -> storage`.

Each symbol is loaded from `config/symbols/*.yaml` and owns independent detector/state-machine instances. MT5 calls are isolated in `market_data/mt5_provider.py`; Telegram formatting and buttons live in `telegram/`; FBB math is independent and deterministic in `indicators/fbb/calculator.py`.

## FBB mathematics and TradingView parity

Source is HLC3: `(high + low + close) / 3`. Basis is VWMA: `sum(HLC3 * volume, length) / sum(volume, length)`. Standard deviation defaults to population `ddof=0`, matching TradingView-style `stdev` behavior for the reference formula. Warm-up emits missing values until a complete rolling window is available. Diagnostic CSV export is available through `indicators.fbb.validator.export_diagnostic_csv`.

## Configuration

Global settings live in `config/global.yaml`; symbol settings live in `config/symbols/XAUUSD.yaml` etc. Defaults use `PAPER` mode and `require_human_approval: true`. Never put real secrets in YAML; use `.env` variables shown in `.env.example`.

## MT5 setup

Install MetaTrader 5 and the `MetaTrader5` Python package on Windows. Configure `MT5_LOGIN`, `MT5_PASSWORD`, and `MT5_SERVER` in a private `.env`. Strategy modules should consume `SymbolSpec`, `Tick`, and candle models rather than direct MT5 objects.

## Telegram setup

Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`, then enable Telegram in configuration. Proposal messages include direction-specific approval buttons, for example `APPROVE SELL` plus `REJECT`.

## Paper and live mode

`PAPER` simulates execution and never sends a real order. `LIVE` is intentionally not the default; the scaffold refuses to fake a live adapter and requires broker-specific order filling validation before real trading.

## State machine and signal lifecycle

A level detector emits `ENTERED`/`EXITED` events with duplicate prevention. The entry machine creates a setup on configured FBB levels, tracks reaction, waits for candle close back inside when enabled, then emits an `EntrySignal`. Risk creates an immutable `TradeProposal`; execution validates expiry, spread, price deviation, and volume before simulated or live execution.

## Risk calculation

The initial implementation supports fixed-point stops and risk/reward take profit. Position size uses MT5-style `tick_value`, `tick_size`, and broker min/max/step lot constraints. This keeps XAUUSD, BTCUSD, FX, and metals symbol-aware.

## Chart generation

`chart/chart_service.py` creates mobile-readable proposal charts with close price, VWMA basis, FBB bands, entry, SL, and TP.

## Backtest architecture and no look-ahead bias

Backtesting should reuse the same FBB calculator, detector, entry machine, and risk manager. `CandleManager` documents separation of live ticks, forming candles, and closed candles; historical signals must only use information available at that timestamp.

## Running

```bash
python main.py
```

## Testing

```bash
pytest
```

## Troubleshooting

- Invalid config fails at startup through typed configuration validation.
- Missing MT5 package only affects live MT5 provider usage, not unit tests.
- Wide spread, stale proposal, invalid volume, or excessive price deviation rejects execution.

## Known limitations

This is a production-quality foundation, not an empirically optimized strategy. The live MT5 order submission method is intentionally guarded and must be completed with broker-specific filling modes before `LIVE` use. No RSI/MACD/ML/extra filters are included by default.
