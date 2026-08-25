from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from core.models.market import Candle, Tick
from signals.models import FBBLevelEvent, LevelSide

SEPARATOR = '=' * 80

SECTIONS = {
    'MARKET': '1. RUNTIME & MARKET DATA',
    'FBB': '2. FBB CALCULATION',
    'LOCATION': '3. FBB LEVEL MAP / PRICE LOCATION',
    'EVENTS': '4. FBB LEVEL EVENTS',
    'ENTRY': '5. ENTRY STATE MACHINE',
    'SIGNAL': '6. ENTRY SIGNAL',
    'RISK': '7. RISK & TRADE PROPOSAL',
    'CHART_TELEGRAM': '8. CHART & TELEGRAM',
    'APPROVAL_EXECUTION': '9. EXECUTION / HUMAN APPROVAL',
    'STATUS': '10. RUNTIME STATUS / HEARTBEAT',
}

@dataclass(frozen=True)
class PriceLocation:
    side: str
    level: float
    price: float
    distance: float
    status: str

    @property
    def label(self) -> str:
        return f'{self.side} {self.level:.3f}'

def section(title: str, body: str) -> str:
    return f'\n{SEPARATOR}\n[{title}]\n{SEPARATOR}\n{body}'

def fmt_value(value: Any, digits: int | None = None) -> str:
    if value is None:
        return 'N/A'
    if isinstance(value, float):
        return f'{value:.{digits}f}' if digits is not None else f'{value:.5f}'
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)

def age_seconds(timestamp: datetime | None, now: datetime | None = None) -> float | None:
    if timestamp is None:
        return None
    current = now or datetime.now(timezone.utc)
    return max(0.0, (current - timestamp).total_seconds())

def nearest_level(price: float, bands: dict[str, float], levels: list[float], basis: float | None = None) -> PriceLocation | None:
    candidates: list[PriceLocation] = []
    if basis is not None:
        candidates.append(PriceLocation('MIDDLE', 0.0, basis, price - basis, ''))
    for level in levels:
        for side in ('UPPER', 'LOWER'):
            key = f'{side.lower()}_{level:.3f}'
            level_price = bands.get(key)
            if level_price is None:
                continue
            candidates.append(PriceLocation(side, level, level_price, price - level_price, ''))
    if not candidates:
        return None
    closest = min(candidates, key=lambda item: abs(item.distance))
    status = 'NEAR_LEVEL' if abs(closest.distance) <= float(bands.get('atr_tolerance', 0.0)) else 'BETWEEN_LEVELS'
    return PriceLocation(closest.side, closest.level, closest.price, closest.distance, status)

def market_block(symbol: str, mt5_symbol: str, timeframe: str, tick: Tick, closed: list[Candle], forming: Candle | None, mt5_connected: bool) -> str:
    candle = forming or (closed[-1] if closed else None)
    freshness = age_seconds(tick.timestamp)
    candle_line = 'Candle=N/A'
    if candle is not None:
        candle_line = (
            f'CandleTimestamp={fmt_value(candle.timestamp)} | Forming={not candle.closed} | '
            f'O={candle.open} H={candle.high} L={candle.low} C={candle.close} Volume={candle.volume}'
        )
    body = '\n'.join([
        f'[Runtime] Symbol={symbol} | MT5Symbol={mt5_symbol} | Timeframe={timeframe} | MT5Connected={mt5_connected}',
        f'[Tick] Timestamp={fmt_value(tick.timestamp)} | Bid={tick.bid} | Ask={tick.ask} | Mid={tick.mid} | Spread={tick.spread} | FreshnessSeconds={fmt_value(freshness, 1)}',
        f'[MARKET] ClosedCandles={len(closed)} | HasFormingCandle={forming is not None}',
        candle_line,
    ])
    return section(SECTIONS['MARKET'], body)

def fbb_block(symbol: str, timeframe: str, cfg: Any, latest: dict[str, Any]) -> str:
    levels = getattr(cfg, 'levels', [])
    upper = [f'U{level:.3f}={fmt_value(latest.get(f"upper_{level:.3f}"))}' for level in levels]
    lower = [f'L{level:.3f}={fmt_value(latest.get(f"lower_{level:.3f}"))}' for level in levels]
    body = '\n'.join([
        f'[FBB] Symbol={symbol} | Timeframe={timeframe}',
        f'Length={cfg.length} | Source={str(cfg.source).upper()} | Multiplier={cfg.multiplier} | StdDDOF={cfg.std_ddof}',
        f'VWMA={fmt_value(latest.get("basis"))} | StdDev={fmt_value(latest.get("std"))} | Deviation={fmt_value(latest.get("deviation"))}',
        'ConfiguredLevels=' + ', '.join(f'{level:.3f}' for level in levels),
        'UpperBands: ' + ' | '.join(upper),
        'LowerBands: ' + ' | '.join(lower),
    ])
    return section(SECTIONS['FBB'], body)

def level_map_block(symbol: str, timeframe: str, price: float, bands: dict[str, float], levels: list[float], basis: float | None) -> str:
    trading_levels = [level for level in levels if round(level, 3) == 1.0]
    lines = [f'CurrentPrice={fmt_value(price)} | VWMA Basis={fmt_value(basis)} | Symbol={symbol} | Timeframe={timeframe}', '', 'UPPER FBB 1.000:']
    for level in trading_levels:
        value = bands.get(f'upper_{level:.3f}')
        lines.append(f'{level:.3f} = {fmt_value(value)} | distance = {fmt_value(None if value is None else price - value)}')
    lines.extend(['', 'MIDDLE VWMA BASIS:', f'basis = {fmt_value(basis)} | distance = {fmt_value(None if basis is None else price - basis)}'])
    lines.extend(['', 'LOWER FBB 1.000:'])
    for level in trading_levels:
        value = bands.get(f'lower_{level:.3f}')
        lines.append(f'{level:.3f} = {fmt_value(value)} | distance = {fmt_value(None if value is None else price - value)}')
    closest = nearest_level(price, bands, trading_levels, basis)
    lines.extend(['', 'PRICE LOCATION:'])
    if closest is None:
        lines.append('Nearest FBB level = N/A | Distance=N/A | Status=NO_BANDS')
    else:
        label = 'VWMA BASIS' if closest.side == 'MIDDLE' else closest.label
        lines.append(f'Nearest FBB level = {label} | LevelPrice={fmt_value(closest.price)} | Distance={fmt_value(closest.distance)} | Status={closest.status}')
    return section(SECTIONS['LOCATION'], '\n'.join(lines))

def event_block(event: FBBLevelEvent) -> str:
    direction = 'SELL' if event.side is LevelSide.UPPER else 'BUY'
    body = '\n'.join([
        '[FBB EVENT]',
        f'Symbol={event.symbol} | Timeframe={event.timeframe} | DirectionConsidered={direction}',
        f'Band={event.side.value} | Level={event.level:.3f} | LevelPrice={fmt_value(event.level_price)}',
        f'CurrentPrice={fmt_value(event.price)} | Event={event.event_type.value} | EventId={event.event_id}',
    ])
    return section(SECTIONS['EVENTS'], body)

def no_event_block(symbol: str, price: float, closest: PriceLocation | None) -> str:
    location = 'N/A' if closest is None else f'{closest.label} distance={fmt_value(closest.distance)} status={closest.status}'
    body = f'[FBB EVENT STATUS]\nSymbol={symbol} | CurrentPrice={fmt_value(price)} | No new ENTERED/EXITED event | Existing inside-state prevents duplicate events | Nearest={location}'
    return section(SECTIONS['EVENTS'], body)

def runtime_status_block(state: dict[str, Any]) -> str:
    lines = [
        f'Symbol={state.get("symbol")} | Runtime=RUNNING | MT5={state.get("mt5_state", "UNKNOWN")} | Mode={state.get("mode")}',
        f'Price={fmt_value(state.get("price"))} | Spread={fmt_value(state.get("spread"))}',
        f'FBB: Basis={fmt_value(state.get("basis"))} | NearestLevel={state.get("nearest_level", "N/A")} | Distance={fmt_value(state.get("nearest_distance"))} | LocationStatus={state.get("location_status", "N/A")}',
        f'EntryMachine: State={state.get("entry_state", "UNKNOWN")} | ActiveSetups={state.get("active_setups", 0)} | Detail={state.get("entry_detail", "")}',
        f'PendingProposals={state.get("pending_proposals", 0)} | ActivePositions=0 | LastClosedCandle={fmt_value(state.get("last_closed_candle"))} | LastSuccessfulCycle={fmt_value(state.get("last_successful_cycle"))}',
    ]
    return section(SECTIONS['STATUS'], '\n'.join(lines))
