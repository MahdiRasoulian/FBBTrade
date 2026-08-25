from core.models.market import SymbolSpec
class MT5Provider:
    def connect(self):
        try: import MetaTrader5 as mt5
        except ImportError as exc: raise RuntimeError('MetaTrader5 package is required for live MT5 data') from exc
        if not mt5.initialize(): raise RuntimeError(f'MT5 initialize failed: {mt5.last_error()}')
    def symbol_spec(self, symbol:str)->SymbolSpec:
        import MetaTrader5 as mt5
        info=mt5.symbol_info(symbol)
        if info is None: raise RuntimeError(f'Invalid MT5 symbol: {symbol}')
        return SymbolSpec(symbol, info.point, info.digits, info.trade_contract_size, info.volume_min, info.volume_max, info.volume_step, info.trade_tick_value, info.trade_tick_size)
