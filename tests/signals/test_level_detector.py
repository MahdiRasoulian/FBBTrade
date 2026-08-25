from datetime import datetime, timezone
from signals.level_detector import FBBLevelDetector


def test_enter_exit_duplicate_prevention_for_outer_fbb_only():
    d=FBBLevelDetector('XAUUSD','M5',[1.0]); bands={'upper_1.000':10,'lower_1.000':5}; t=datetime.now(timezone.utc)
    assert len(d.detect(11,bands,t))==1
    assert d.detect(12,bands,t)==[]
    ev=d.detect(9,bands,t)
    assert len(ev)==1 and ev[0].event_type.value=='EXITED'


def test_only_configured_outer_level_is_detected():
    d=FBBLevelDetector('XAUUSD','M5',[1.0]); bands={'upper_1.000':10,'lower_1.000':5}
    events=d.detect(11,bands,datetime.now(timezone.utc))
    assert len(events)==1
    assert events[0].level == 1.0
