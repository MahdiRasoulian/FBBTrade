from datetime import datetime, timezone
from signals.level_detector import FBBLevelDetector

def test_enter_exit_duplicate_prevention():
    d=FBBLevelDetector('XAUUSD','M5',[0.764]); bands={'upper_0.764':10,'lower_0.764':5}; t=datetime.now(timezone.utc)
    assert len(d.detect(11,bands,t))==1
    assert d.detect(12,bands,t)==[]
    ev=d.detect(9,bands,t)
    assert len(ev)==1 and ev[0].event_type.value=='EXITED'

def test_multi_level():
    d=FBBLevelDetector('XAUUSD','M5',[0.618,0.764]); bands={'upper_0.618':9,'lower_0.618':6,'upper_0.764':10,'lower_0.764':5}
    assert len(d.detect(11,bands,datetime.now(timezone.utc)))==2
