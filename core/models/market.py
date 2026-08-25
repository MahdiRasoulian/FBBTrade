from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    closed: bool = True

@dataclass(frozen=True)
class Tick:
    symbol: str
    bid: float
    ask: float
    timestamp: datetime
    last: float | None = None
    @property
    def mid(self) -> float: return self.last if self.last is not None else (self.bid + self.ask) / 2
    @property
    def spread(self) -> float: return self.ask - self.bid

@dataclass(frozen=True)
class SymbolSpec:
    symbol: str; point: float; digits: int; contract_size: float
    min_lot: float; max_lot: float; lot_step: float; tick_value: float; tick_size: float
