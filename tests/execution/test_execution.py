from datetime import timedelta
from core.models.market import Tick, SymbolSpec
from core.models.trading import EntrySignal, TradeProposal, Direction
from execution.execution_validator import ExecutionValidator
from utils.time import utc_now

def proposal(exp=300):
    sig=EntrySignal('s','XAUUSD','M5',Direction.SELL,'UPPER_0.764',2000,2000,utc_now(),'x','r')
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
