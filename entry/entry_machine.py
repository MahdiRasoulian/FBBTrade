import logging
from datetime import datetime
from core.models.trading import Direction, EntrySignal
from signals.models import FBBLevelEvent, LevelEventType, LevelSide
from .models import EntryState, SetupTracker
logger = logging.getLogger(__name__)

class EntryMachine:
    def __init__(self, symbol:str, timeframe:str, config):
        self.symbol=symbol; self.timeframe=timeframe; self.config=config; self.trackers:dict[str,SetupTracker]={}; self.seq=0
    def on_level_event(self,event:FBBLevelEvent):
        if event.event_type is LevelEventType.ENTERED and event.level in self.config.trigger_levels:
            self.trackers[event.level_name]=SetupTracker(event, EntryState.TRACKING, event.timestamp)
            logger.info('Entry setup created', extra={'event': 'ENTRY_STATE_TRANSITIONS', 'symbol': self.symbol, 'level': event.level_name, 'state': EntryState.TRACKING.value})
        elif event.event_type is LevelEventType.EXITED and event.level_name in self.trackers:
            self.trackers[event.level_name].state=EntryState.REACTION_DETECTED
            logger.info('Entry reaction detected', extra={'event': 'ENTRY_STATE_TRANSITIONS', 'symbol': self.symbol, 'level': event.level_name, 'state': EntryState.REACTION_DETECTED.value})
    def on_candle_close(self, close_price:float, bands:dict[str,float], timestamp:datetime)->list[EntrySignal]:
        out=[]
        for name,t in list(self.trackers.items()):
            t.bars_seen+=1
            if t.bars_seen>self.config.max_tracking_bars:
                t.state=EntryState.TIMEOUT
                logger.info('Entry setup timed out', extra={'event': 'SIGNAL_REJECTIONS', 'symbol': self.symbol, 'level': name, 'state': EntryState.TIMEOUT.value})
                del self.trackers[name]; continue
            band_key=f'{t.event.side.value.lower()}_{t.event.level:.3f}'
            current_level_price=bands.get(band_key, t.event.level_price)
            tolerance=float(bands.get('atr_tolerance', 0.0))
            inside = close_price <= current_level_price+tolerance if t.event.side is LevelSide.UPPER else close_price >= current_level_price-tolerance
            if (not self.config.return_inside_required) or inside:
                self.seq+=1; direction=Direction.SELL if t.event.side is LevelSide.UPPER else Direction.BUY
                sid=f'FBB-{timestamp:%Y%m%d}-{self.symbol}-{self.seq:06d}'
                out.append(EntrySignal(sid,self.symbol,self.timeframe,direction,t.event.level_name,t.event.price,close_price,timestamp,self.config.setup_type,'FBB level entered then closed back inside; configurable mean-reversion rejection'))
                t.state=EntryState.ENTRY_CONFIRMED
                logger.info('Entry confirmed', extra={'event': 'ENTRY_STATE_TRANSITIONS', 'symbol': self.symbol, 'level': name, 'state': EntryState.ENTRY_CONFIRMED.value, 'signal_id': sid})
                del self.trackers[name]
        return out
