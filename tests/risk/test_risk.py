from datetime import datetime, timezone
from types import SimpleNamespace
from core.models.market import SymbolSpec
from core.models.trading import EntrySignal, Direction
from risk.risk_manager import RiskManager

def test_risk_proposal_lot_sl_tp_rr():
    spec=SymbolSpec('XAUUSD',0.01,2,100,0.01,100,0.01,1,0.01)
    sig=EntrySignal('s','XAUUSD','M5',Direction.BUY,'LOWER_1.000',1900,1900,datetime.now(timezone.utc),'x','r')
    cfg=SimpleNamespace(risk_per_trade_percent=1.0,stop_loss={'points':100},take_profit={'rr':2.0})
    p=RiskManager(10000).create_proposal(sig,spec,cfg)
    assert p.stop_loss==1899.0 and p.take_profit==1902.0 and p.rr_ratio==2.0 and p.lot_size>0

def test_invalid_equal_stop():
    import pytest
    from risk.position_sizer import lot_size_for_risk
    spec=SymbolSpec('X',0.01,2,1,.01,1,.01,1,.01)
    with pytest.raises(ValueError): lot_size_for_risk(100,1,1,spec)

def test_risk_size_below_minimum_is_not_clamped_up():
    import pytest
    from risk.position_sizer import lot_size_for_risk
    spec=SymbolSpec('X',0.01,2,1,0.1,1,0.01,1,0.01)
    with pytest.raises(ValueError): lot_size_for_risk(0.01,100,99,spec)

def test_fixed_lot_from_config():
    spec=SymbolSpec('XAUUSD',0.01,2,100,0.01,100,0.01,1,0.01)
    sig=EntrySignal('s','XAUUSD','M5',Direction.SELL,'UPPER_1.000',1900,1900,datetime.now(timezone.utc),'x','r')
    cfg=SimpleNamespace(risk_per_trade_percent=1.0,fixed_lot=0.01,stop_loss={'points':100},take_profit={'rr':2.0})
    assert RiskManager(10000).create_proposal(sig,spec,cfg).lot_size == 0.01
