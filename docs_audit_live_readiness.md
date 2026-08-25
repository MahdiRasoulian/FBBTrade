# FBBTrade Runtime Audit and Live-Readiness Notes

## Audit summary

The runtime now starts a continuous multi-symbol processing loop from `python main.py` instead of acting as a one-shot status command. MT5 access remains isolated in `market_data.mt5_provider.MT5Provider`; strategy modules consume normalized `Tick`, `Candle`, and `SymbolSpec` models.

Key findings from the code audit:

- FBB math uses HLC3, VWMA basis, population standard deviation by default, multiplier 3.0, and Fibonacci levels configured per symbol.
- Level detection and entry confirmation are distinct: `FBBLevelDetector` emits market-location events, while `EntryMachine` confirms signals on candle close using current band values.
- Symbol runtimes are independent objects, with separate candle managers, detectors, calculators, and entry machines.
- Risk currently supports fixed lots through symbol configuration, which is appropriate for the requested current risk phase.
- Persistence is event-table based in SQLite. It stores level events, entry signals, rejected proposals, and trade proposals as JSON payloads, but does not yet model approvals, executions, position lifecycle, reconciliation, or restart recovery as first-class relational records.
- Live execution remains intentionally scaffolded; the `MT5Executor` refuses live broker orders until broker-specific filling/deviation/order semantics are implemented and tested.

## Implemented remediation

- Added professional console and rotating file logging with structured context fields.
- Added runtime event logs for startup, configuration, MT5 connection, symbol validation, market data snapshots, candle updates, FBB calculations, FBB level events, entry signals, signal rejections, risk calculation, proposal rejections, chart generation, Telegram notification, errors, shutdown, and heartbeat.
- Reworked shutdown registration to use portable `signal.signal`, avoiding Unix-only asyncio signal handling.
- Ensured per-symbol exceptions are logged without stopping other enabled symbols.

## Live-readiness decision

FBBTrade is safer and more observable after this pass, but it is **not technically ready for controlled LIVE trading** yet. The system should remain in PAPER mode until at least the following are complete:

1. Telegram callback handling persists approval and rejection decisions.
2. Execution records, broker tickets, order results, fills, and position lifecycle are persisted and reconciled on restart.
3. The live MT5 order adapter is implemented with symbol-specific filling modes, deviation, SL/TP normalization, volume validation, and broker error handling.
4. Restart recovery reloads open proposals, pending approvals, active setups, and open positions.
5. End-to-end paper and MT5 demo tests prove duplicate-order prevention and recovery behavior.

## ZIP deliverable

The repository can be packaged with:

```bash
python -m zipfile -c FBBTrade_live_readiness.zip .
```
