from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class Direction(str, Enum): BUY='BUY'; SELL='SELL'
class ProposalStatus(str, Enum): WAITING_APPROVAL='WAITING_APPROVAL'; APPROVED='APPROVED'; REJECTED='REJECTED'; EXPIRED='EXPIRED'; EXECUTED='EXECUTED'

@dataclass(frozen=True)
class EntrySignal:
    signal_id: str; symbol: str; timeframe: str; direction: Direction; trigger_level: str
    trigger_price: float; entry_price: float; timestamp: datetime; setup_type: str; reason: str; score: float=1.0

@dataclass(frozen=True)
class TradeProposal:
    proposal_id: str; signal: EntrySignal; stop_loss: float; take_profit: float; lot_size: float
    risk_percent: float; risk_amount: float; rr_ratio: float; created_at: datetime; expires_at: datetime
    status: ProposalStatus = ProposalStatus.WAITING_APPROVAL
