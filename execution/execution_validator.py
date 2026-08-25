from dataclasses import dataclass
from utils.time import utc_now
from core.models.trading import TradeProposal
from core.models.market import Tick, SymbolSpec
@dataclass(frozen=True)
class ValidationResult: ok:bool; reason:str='OK'
class ExecutionValidator:
    def __init__(self, max_deviation_points:float, max_spread_points:float): self.max_dev=max_deviation_points; self.max_spread=max_spread_points
    def validate(self, proposal:TradeProposal, tick:Tick, spec:SymbolSpec)->ValidationResult:
        if utc_now()>proposal.expires_at: return ValidationResult(False,'TRADE EXPIRED')
        if tick.spread/spec.point>self.max_spread: return ValidationResult(False,'SPREAD TOO WIDE')
        if abs(tick.mid-proposal.signal.entry_price)/spec.point>self.max_dev: return ValidationResult(False,'PRICE DEVIATION TOO LARGE')
        if not(spec.min_lot<=proposal.lot_size<=spec.max_lot): return ValidationResult(False,'INVALID VOLUME')
        return ValidationResult(True)
