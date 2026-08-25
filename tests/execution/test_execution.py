from datetime import timedelta
from core.models.market import Tick, SymbolSpec
from core.models.trading import EntrySignal, TradeProposal, Direction
from execution.execution_validator import ExecutionValidator
from utils.time import utc_now

def proposal(exp=300):
    sig=EntrySignal('s','XAUUSD','M5',Direction.SELL,'UPPER_1.000',2000,2000,utc_now(),'x','r')
    return TradeProposal('p',sig,2003,1994,.1,1,100,2,utc_now(),utc_now()+timedelta(seconds=exp))
def spec(): return SymbolSpec('XAUUSD',.01,2,100,.01,10,.01,1,.01)

def test_price_deviation_reject():
    r=ExecutionValidator(10,100).validate(proposal(),Tick('XAUUSD',2001,2001.1,utc_now()),spec())
    assert not r.ok and 'PRICE' in r.reason

def test_stale_proposal_reject():
    r=ExecutionValidator(10,100).validate(proposal(-1),Tick('XAUUSD',2000,2000.1,utc_now()),spec())
    assert not r.ok and 'EXPIRED' in r.reason

def test_valid_execution_validation():
    assert ExecutionValidator(20,20).validate(proposal(),Tick('XAUUSD',1999.95,2000.05,utc_now()),spec()).ok


def test_live_mt5_executor_sends_demo_order(monkeypatch):
    from types import SimpleNamespace
    from execution import mt5_executor
    from execution.mt5_executor import MT5Executor

    sent = {}
    fake_mt5 = SimpleNamespace(
        ORDER_TYPE_BUY=0,
        ORDER_TYPE_SELL=1,
        ORDER_FILLING_RETURN=2,
        TRADE_ACTION_DEAL=3,
        ORDER_TIME_GTC=4,
        TRADE_RETCODE_DONE=10009,
        initialize=lambda: True,
        last_error=lambda: ('ok', 0),
        symbol_info=lambda symbol: SimpleNamespace(visible=True, filling_mode=2),
        symbol_select=lambda symbol, visible: True,
        symbol_info_tick=lambda symbol: SimpleNamespace(bid=1999.9, ask=2000.1),
    )
    def order_send(request):
        sent.update(request)
        return SimpleNamespace(retcode=fake_mt5.TRADE_RETCODE_DONE, order=123456, deal=0, comment='done')
    fake_mt5.order_send = order_send

    monkeypatch.setattr(mt5_executor.util, 'find_spec', lambda name: object())
    monkeypatch.setattr(mt5_executor, 'import_module', lambda name: fake_mt5)

    result = MT5Executor('LIVE', {'XAUUSD': 'XAUUSD!'}).execute(proposal())

    assert result.success
    assert result.ticket == 123456
    assert sent['symbol'] == 'XAUUSD!'
    assert sent['type'] == fake_mt5.ORDER_TYPE_SELL
    assert sent['volume'] == proposal().lot_size
