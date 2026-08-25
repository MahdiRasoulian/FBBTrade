from datetime import datetime, timezone
from core.models.market import Candle, SymbolSpec, Tick

class MT5Provider:
    def __init__(self):
        self.mt5 = None
    def connect(self):
        try: import MetaTrader5 as mt5
        except ImportError as exc: raise RuntimeError('MetaTrader5 package is required for live MT5 data') from exc
        if not mt5.initialize(): raise RuntimeError(f'MT5 initialize failed: {mt5.last_error()}')
        self.mt5 = mt5
    def is_connected(self)->bool:
        return self.mt5 is not None
    def _api(self):
        if self.mt5 is None: self.connect()
        return self.mt5
    def symbol_spec(self, symbol:str)->SymbolSpec:
        mt5=self._api(); info=mt5.symbol_info(symbol)
        if info is None: raise RuntimeError(f'Invalid MT5 symbol: {symbol}')
        if not info.visible: mt5.symbol_select(symbol, True)
        return SymbolSpec(symbol, info.point, info.digits, info.trade_contract_size, info.volume_min, info.volume_max, info.volume_step, info.trade_tick_value, info.trade_tick_size)
    def latest_tick(self, symbol:str)->Tick:
        mt5=self._api(); tick=mt5.symbol_info_tick(symbol)
        if tick is None: raise RuntimeError(f'No MT5 tick available for {symbol}')
        ts=datetime.fromtimestamp(getattr(tick, 'time', 0), tz=timezone.utc)
        return Tick(symbol=symbol, bid=float(tick.bid), ask=float(tick.ask), last=float(tick.last) if getattr(tick, 'last', 0) else None, timestamp=ts)
    def candles(self, symbol:str, timeframe:str, count:int):
        mt5=self._api(); tf=self._timeframe(timeframe)
        rates=mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None or len(rates)==0: raise RuntimeError(f'No MT5 candles available for {symbol} {timeframe}')
        candles=[]
        for i, r in enumerate(rates):
            candles.append(Candle(timestamp=datetime.fromtimestamp(int(r['time']), tz=timezone.utc), open=float(r['open']), high=float(r['high']), low=float(r['low']), close=float(r['close']), volume=float(r['tick_volume']), closed=i < len(rates)-1))
        return candles
    def _timeframe(self, timeframe:str):
        mt5=self._api(); name='TIMEFRAME_'+timeframe.upper()
        if not hasattr(mt5, name): raise ValueError(f'Unsupported MT5 timeframe: {timeframe}')
        return getattr(mt5, name)
