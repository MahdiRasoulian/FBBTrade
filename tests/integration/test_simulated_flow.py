from datetime import datetime, timezone
from types import SimpleNamespace
from core.models.market import SymbolSpec, Tick
from indicators.fbb.calculator import FBBCalculator
from signals.level_detector import FBBLevelDetector
from entry.entry_machine import EntryMachine
from risk.risk_manager import RiskManager
from execution.execution_validator import ExecutionValidator
from execution.mt5_executor import MT5Executor

def test_complete_simulated_flow():
    df=[{'high':10,'low':8,'close':9,'volume':1},{'high':11,'low':9,'close':10,'volume':1},{'high':12,'low':10,'close':11,'volume':1}]
    fbb=FBBCalculator(length=2,levels=[1.0]).calculate(df).frame
    bands={'upper_1.000':10,'lower_1.000':8}
    now=datetime.now(timezone.utc)
    events=FBBLevelDetector('XAUUSD','M5',[1.0]).detect(10.5,bands,now)
    cfg=SimpleNamespace(trigger_levels=[1.0],max_tracking_bars=3,return_inside_required=True,setup_type='MEAN_REVERSION_REJECTION')
    m=EntryMachine('XAUUSD','M5',cfg); [m.on_level_event(e) for e in events]
    sig=m.on_candle_close(9.9,bands,now)[0]
    spec=SymbolSpec('XAUUSD',.01,2,100,.01,100,.01,1,.01)
    rcfg=SimpleNamespace(risk_per_trade_percent=1,stop_loss={'points':100},take_profit={'rr':2})
    proposal=RiskManager(10000).create_proposal(sig,spec,rcfg)
    assert ExecutionValidator(100,50).validate(proposal,Tick('XAUUSD',9.85,9.95,now),spec).ok
    assert MT5Executor('PAPER').execute(proposal).success
