from datetime import datetime, timezone
from types import SimpleNamespace
from entry.entry_machine import EntryMachine
from signals.models import FBBLevelEvent, LevelEventType, LevelSide

def event(): return FBBLevelEvent('e','XAUUSD','M5',LevelSide.UPPER,0.764,LevelEventType.ENTERED,11,10,datetime.now(timezone.utc))
def cfg(): return SimpleNamespace(trigger_levels=[0.764],max_tracking_bars=2,return_inside_required=True,setup_type='MEAN_REVERSION_REJECTION')

def test_valid_setup_signal():
    m=EntryMachine('XAUUSD','M5',cfg()); m.on_level_event(event())
    sig=m.on_candle_close(9.9,{},datetime.now(timezone.utc))
    assert sig and sig[0].direction.value=='SELL'

def test_timeout():
    m=EntryMachine('XAUUSD','M5',cfg()); m.on_level_event(event())
    assert not m.on_candle_close(10.5,{},datetime.now(timezone.utc))
    assert not m.on_candle_close(10.5,{},datetime.now(timezone.utc))
    assert not m.on_candle_close(10.5,{},datetime.now(timezone.utc))
    assert m.trackers=={}
