import logging
from datetime import datetime
from core.models.trading import Direction, EntrySignal
from signals.models import FBBLevelEvent, LevelEventType, LevelSide
from utils.observability import SECTIONS, section, fmt_value
from .models import EntryState, SetupTracker
logger = logging.getLogger(__name__)

class EntryMachine:
    def __init__(self, symbol:str, timeframe:str, config):
        self.symbol=symbol; self.timeframe=timeframe; self.config=config; self.trackers:dict[str,SetupTracker]={}; self.seq=0
    def on_level_event(self,event:FBBLevelEvent):
        if event.event_type is LevelEventType.ENTERED and event.level in self.config.trigger_levels:
            self.trackers[event.level_name]=SetupTracker(event, EntryState.TRACKING, event.timestamp)
            direction='SELL' if event.side is LevelSide.UPPER else 'BUY'
            logger.info(section(SECTIONS['ENTRY'], '\n'.join([
                '[ENTRY SETUP CREATED]',
                f'Symbol={self.symbol} | Timeframe={self.timeframe} | Side={direction}',
                f'Band={event.side.value} | Level={event.level:.3f} | LevelPrice={fmt_value(event.level_price)} | TriggerPrice={fmt_value(event.price)}',
                'State=WAITING_REACTION',
                'Reason=Configured FBB trigger level entered; waiting for reaction/exit and closed-candle confirmation',
            ])), extra={'event': 'ENTRY_STATE_TRANSITIONS', 'symbol': self.symbol, 'level': event.level_name, 'state': EntryState.TRACKING.value})
        elif event.event_type is LevelEventType.EXITED and event.level_name in self.trackers:
            self.trackers[event.level_name].state=EntryState.REACTION_DETECTED
            logger.info(section(SECTIONS['ENTRY'], '\n'.join([
                '[ENTRY STATE TRANSITION]',
                f'Symbol={self.symbol} | Level={event.level_name}',
                'WAITING_REACTION -> REACTION_DETECTED -> WAITING_CANDLE_CLOSE',
                f'CurrentPrice={fmt_value(event.price)} | LevelPrice={fmt_value(event.level_price)}',
                'Reason=Price exited the touched FBB level; waiting for closed candle confirmation using current bands',
            ])), extra={'event': 'ENTRY_STATE_TRANSITIONS', 'symbol': self.symbol, 'level': event.level_name, 'state': EntryState.REACTION_DETECTED.value})
    def on_candle_close(self, close_price:float, bands:dict[str,float], timestamp:datetime)->list[EntrySignal]:
        out=[]
        for name,t in list(self.trackers.items()):
            t.bars_seen+=1
            if t.bars_seen>self.config.max_tracking_bars:
                t.state=EntryState.TIMEOUT
                logger.warning(section(SECTIONS['SIGNAL'], '\n'.join([
                    'ENTRY SIGNAL REJECTED',
                    f'Symbol={self.symbol} | Level={name} | BarsSeen={t.bars_seen} | MaxTrackingBars={self.config.max_tracking_bars}',
                    'Reason=Setup expired before confirmation candle closed back inside the current FBB band',
                    'Decision=NO_ENTRY_SIGNAL',
                ])), extra={'event': 'SIGNAL_REJECTIONS', 'symbol': self.symbol, 'level': name, 'state': EntryState.TIMEOUT.value})
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
                logger.info(section(SECTIONS['SIGNAL'], '\n'.join([
                    'ENTRY SIGNAL GENERATED',
                    f'Symbol={self.symbol} | Side={direction.value} | Timeframe={self.timeframe}',
                    f'FBB Band={t.event.side.value} | FBB Level={t.event.level:.3f} | CurrentBandPrice={fmt_value(current_level_price)}',
                    f'TriggerPrice={fmt_value(t.event.price)} | ConfirmationClose={fmt_value(close_price)} | ConfirmationCandle={fmt_value(timestamp)}',
                    f'ReactionDetected={"YES" if t.state is EntryState.REACTION_DETECTED else "NO"} | ClosedBackInsideBand=YES | Tolerance={fmt_value(tolerance)}',
                    f'Decision=ENTRY_SIGNAL | SignalId={sid}',
                ])), extra={'event': 'ENTRY_SIGNALS', 'symbol': self.symbol, 'level': name, 'state': EntryState.ENTRY_CONFIRMED.value, 'signal_id': sid})
                del self.trackers[name]
        return out
    def state_snapshot(self, current_price:float|None=None, bands:dict[str,float]|None=None, now:datetime|None=None)->dict:
        if not self.trackers:
            return {'state':'IDLE','active_setups':0,'detail':'No active FBB setup; waiting for configured level entry'}
        name,t=next(iter(self.trackers.items()))
        direction='SELL' if t.event.side is LevelSide.UPPER else 'BUY'
        band_key=f'{t.event.side.value.lower()}_{t.event.level:.3f}'
        current_level_price=(bands or {}).get(band_key, t.event.level_price)
        state='WAITING_CANDLE_CLOSE' if t.state is EntryState.REACTION_DETECTED else 'WAITING_REACTION'
        age=None if now is None else max(0.0,(now-t.created_at).total_seconds())
        return {'state':state,'active_setups':len(self.trackers),'detail':f'Side={direction} Level={name} LevelPrice={fmt_value(current_level_price)} SetupAgeSeconds={fmt_value(age,1)} CurrentPrice={fmt_value(current_price)} Reason=Waiting for closed candle to return inside current band'}
