from dataclasses import dataclass
from importlib import import_module, util
from core.models.trading import Direction, TradeProposal

@dataclass(frozen=True)
class ExecutionResult:
    success: bool
    ticket: int | None
    message: str

class MT5Executor:
    def __init__(self, mode:str='PAPER', mt5_symbol_by_symbol:dict[str,str]|None=None):
        self.mode=mode.upper(); self._ticket=100000; self.mt5_symbol_by_symbol=mt5_symbol_by_symbol or {}
    def execute(self, proposal:TradeProposal)->ExecutionResult:
        if self.mode!='LIVE':
            self._ticket+=1; return ExecutionResult(True,self._ticket,'PAPER execution simulated; no real MT5 order sent')
        if util.find_spec('MetaTrader5') is None:
            return ExecutionResult(False,None,'MetaTrader5 package unavailable')
        mt5 = import_module('MetaTrader5')
        if not mt5.initialize():
            return ExecutionResult(False,None,f'MT5 initialize failed: {mt5.last_error()}')
        symbol=self.mt5_symbol_by_symbol.get(proposal.signal.symbol, proposal.signal.symbol)
        info=mt5.symbol_info(symbol)
        if info is None:
            return ExecutionResult(False,None,f'Invalid MT5 symbol: {symbol}')
        if not info.visible and not mt5.symbol_select(symbol, True):
            return ExecutionResult(False,None,f'MT5 symbol_select failed for {symbol}: {mt5.last_error()}')
        tick=mt5.symbol_info_tick(symbol)
        if tick is None:
            return ExecutionResult(False,None,f'No MT5 tick available for {symbol}')
        order_type=mt5.ORDER_TYPE_BUY if proposal.signal.direction is Direction.BUY else mt5.ORDER_TYPE_SELL
        price=float(tick.ask) if proposal.signal.direction is Direction.BUY else float(tick.bid)
        filling=getattr(info, 'filling_mode', mt5.ORDER_FILLING_RETURN)
        request={
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': symbol,
            'volume': float(proposal.lot_size),
            'type': order_type,
            'price': price,
            'sl': float(proposal.stop_loss),
            'tp': float(proposal.take_profit),
            'deviation': 20,
            'magic': 20260825,
            'comment': proposal.proposal_id[:31],
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': filling,
        }
        result=mt5.order_send(request)
        if result is None:
            return ExecutionResult(False,None,f'MT5 order_send returned None: {mt5.last_error()}')
        retcode=getattr(result, 'retcode', None)
        if retcode != mt5.TRADE_RETCODE_DONE:
            return ExecutionResult(False,getattr(result, 'order', None),f'MT5 order rejected retcode={retcode} comment={getattr(result, "comment", "")}')
        ticket=getattr(result, 'order', None) or getattr(result, 'deal', None)
        return ExecutionResult(True,ticket,f'LIVE MT5 order executed retcode={retcode} price={price} volume={proposal.lot_size}')
