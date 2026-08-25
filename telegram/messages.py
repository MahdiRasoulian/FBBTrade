from core.models.trading import TradeProposal
def format_proposal(p:TradeProposal)->str:
    return f"""FBB TRADE PROPOSAL

{p.signal.symbol} | {p.signal.timeframe}

{p.signal.direction.value}

FBB Level: {p.signal.trigger_level}
Trigger: {p.signal.trigger_price:.5f}
Entry: {p.signal.entry_price:.5f}
SL: {p.stop_loss}
TP: {p.take_profit}
Lot: {p.lot_size}
Risk: {p.risk_percent:.2f}% (${p.risk_amount:.2f})
RR: {p.rr_ratio:.2f}
Expires: {p.expires_at.isoformat()}"""
