from datetime import datetime, timezone

from core.models.market import Candle, Tick
from signals.level_detector import FBBLevelDetector
from utils.observability import (
    SECTIONS,
    event_block,
    fbb_block,
    level_map_block,
    market_block,
    nearest_level,
)

class Cfg:
    length = 200
    source = 'hlc3'
    multiplier = 3.0
    std_ddof = 0
    levels = [0.236, 0.618, 1.0]

def test_sectioned_observability_blocks_include_price_location_and_fbb_values():
    latest = {
        'basis': 100.0,
        'std': 2.0,
        'deviation': 6.0,
        'upper_0.236': 101.416,
        'upper_0.618': 103.708,
        'upper_1.000': 106.0,
        'lower_0.236': 98.584,
        'lower_0.618': 96.292,
        'lower_1.000': 94.0,
    }
    bands = {key: value for key, value in latest.items() if key.startswith(('upper_', 'lower_'))}
    bands['atr_tolerance'] = 0.5

    fbb = fbb_block('GOLD', 'M5', Cfg, latest)
    location = level_map_block('GOLD', 'M5', 98.7, bands, Cfg.levels, latest['basis'])

    assert SECTIONS['FBB'] in fbb
    assert 'VWMA=100.00000' in fbb
    assert 'U0.618=103.70800' in fbb
    assert SECTIONS['LOCATION'] in location
    assert 'Nearest FBB level = LOWER 0.236' in location
    assert nearest_level(98.7, bands, Cfg.levels).status == 'NEAR_LEVEL'

def test_market_and_fbb_event_blocks_are_sectioned_and_deterministic():
    now = datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc)
    tick = Tick('XAUUSD!', bid=100.0, ask=100.2, timestamp=now)
    candle = Candle(now, 99.0, 101.0, 98.0, 100.0, 123, closed=False)
    market = market_block('GOLD', 'XAUUSD!', 'M5', tick, [], candle, True)
    assert SECTIONS['MARKET'] in market
    assert 'Bid=100.0' in market
    assert 'HasFormingCandle=True' in market

    detector = FBBLevelDetector('GOLD', 'M5', [0.618])
    event = detector.detect(103.8, {'upper_0.618': 103.7, 'lower_0.618': 96.3}, now)[0]
    rendered = event_block(event)
    assert SECTIONS['EVENTS'] in rendered
    assert 'Event=ENTERED' in rendered
    assert 'DirectionConsidered=SELL' in rendered
