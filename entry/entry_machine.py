from datetime import datetime
from core.models.trading import Direction, EntrySignal
from signals.models import FBBLevelEvent, LevelEventType, LevelSide
from .models import EntryState, SetupTracker
class EntryMachine:
    def __init__(self, symbol:str, timeframe:str, config):
        self.symbol=symbol; self.timeframe=timeframe; self.config=config; self.trackers:dict[str,SetupTracker]={}; self.seq=0
    def on_level_event(self,event:FBBLevelEvent):
        if event.event_type is LevelEventType.ENTERED and event.level in self.config.trigger_levels:
            self.trackers[event.level_name]=SetupTracker(event, EntryState.TRACKING, event.timestamp)
        elif event.event_type is LevelEventType.EXITED and event.level_name in self.trackers:
            self.trackers[event.level_name].state=EntryState.REACTION_DETECTED
    def on_candle_close(self, close_price:float, bands:dict[str,float], timestamp:datetime)->list[EntrySignal]:
        out=[]
        for name,t in list(self.trackers.items()):
            t.bars_seen+=1
            if t.bars_seen>self.config.max_tracking_bars:
                t.state=EntryState.TIMEOUT; del self.trackers[name]; continue
            inside = close_price < t.event.level_price if t.event.side is LevelSide.UPPER else close_price > t.event.level_price
            if (not self.config.return_inside_required) or inside:
                self.seq+=1; direction=Direction.SELL if t.event.side is LevelSide.UPPER else Direction.BUY
                sid=f'FBB-{timestamp:%Y%m%d}-{self.symbol}-{self.seq:06d}'
                out.append(EntrySignal(sid,self.symbol,self.timeframe,direction,t.event.level_name,t.event.price,close_price,timestamp,self.config.setup_type,'FBB level entered then closed back inside; configurable mean-reversion rejection'))
                t.state=EntryState.ENTRY_CONFIRMED; del self.trackers[name]
        return out
