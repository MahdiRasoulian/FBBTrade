from datetime import timedelta
from core.models.market import SymbolSpec
from core.models.trading import EntrySignal, TradeProposal
from utils.time import utc_now
from .position_sizer import lot_size_for_risk
from .sl_engine import fixed_stop
from .tp_engine import rr_take_profit
class RiskManager:
    def __init__(self, account_equity:float, proposal_expiry_seconds:int=300): self.account_equity=account_equity; self.expiry=proposal_expiry_seconds
    def create_proposal(self, signal:EntrySignal, spec:SymbolSpec, risk_config)->TradeProposal:
        risk_amount=self.account_equity*risk_config.risk_per_trade_percent/100
        sl=fixed_stop(signal.entry_price, signal.direction, risk_config.stop_loss.get('points',300), spec.point)
        rr=float(risk_config.take_profit.get('rr',2.0)); tp=rr_take_profit(signal.entry_price, sl, signal.direction, rr)
        lot=lot_size_for_risk(risk_amount, signal.entry_price, sl, spec)
        now=utc_now()
        return TradeProposal('TP-'+signal.signal_id, signal, round(sl,spec.digits), round(tp,spec.digits), lot, risk_config.risk_per_trade_percent, risk_amount, rr, now, now+timedelta(seconds=self.expiry))
