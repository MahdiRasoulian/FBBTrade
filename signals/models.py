from dataclasses import dataclass
from datetime import datetime
from enum import Enum
class LevelSide(str, Enum): UPPER='UPPER'; LOWER='LOWER'
class LevelEventType(str, Enum): ENTERED='ENTERED'; EXITED='EXITED'; REJECTED='REJECTED'; RETESTED='RETESTED'; REACHED='REACHED'
@dataclass(frozen=True)
class FBBLevelEvent:
    event_id:str; symbol:str; timeframe:str; side:LevelSide; level:float; event_type:LevelEventType; price:float; level_price:float; timestamp:datetime
    @property
    def level_name(self)->str: return f'{self.side.value}_{self.level:.3f}'
