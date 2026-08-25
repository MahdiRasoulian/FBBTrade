class CandleManager:
    """Separates live ticks, forming candles, and closed candles to avoid look-ahead bias."""
    def __init__(self, provider, symbol:str, timeframe:str, warmup:int):
        self.provider=provider; self.symbol=symbol; self.timeframe=timeframe; self.warmup=warmup
        self._last_closed_timestamp=None
    def snapshot(self):
        candles=self.provider.candles(self.symbol, self.timeframe, self.warmup)
        closed=[c for c in candles if c.closed]
        forming=next((c for c in reversed(candles) if not c.closed), None)
        return closed, forming
    def has_new_closed_candle(self, closed)->bool:
        if not closed: return False
        ts=closed[-1].timestamp
        if ts != self._last_closed_timestamp:
            self._last_closed_timestamp=ts; return True
        return False
    @staticmethod
    def to_records(candles):
        return [{'timestamp':c.timestamp,'open':c.open,'high':c.high,'low':c.low,'close':c.close,'volume':c.volume} for c in candles]
