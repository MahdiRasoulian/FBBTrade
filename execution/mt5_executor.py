from dataclasses import dataclass
from core.models.trading import TradeProposal
@dataclass(frozen=True)
class ExecutionResult: success:bool; ticket:int|None; message:str
class MT5Executor:
    def __init__(self, mode:str='PAPER'): self.mode=mode.upper(); self._ticket=100000
    def execute(self, proposal:TradeProposal)->ExecutionResult:
        if self.mode!='LIVE':
            self._ticket+=1; return ExecutionResult(True,self._ticket,'PAPER execution simulated; no real MT5 order sent')
        try:
            import MetaTrader5 as mt5
        except ImportError:
            return ExecutionResult(False,None,'MetaTrader5 package unavailable')
        return ExecutionResult(False,None,'LIVE order adapter scaffolded; configure broker-specific filling/deviation before enabling')
