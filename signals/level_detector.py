from datetime import datetime
from .models import FBBLevelEvent, LevelEventType, LevelSide
class FBBLevelDetector:
    def __init__(self, symbol:str, timeframe:str, levels:list[float]):
        self.symbol=symbol; self.timeframe=timeframe; self.levels=levels; self.inside:dict[str,bool]={}
    def detect(self, price:float, bands:dict[str,float], timestamp:datetime)->list[FBBLevelEvent]:
        events=[]
        for level in self.levels:
            for side in (LevelSide.UPPER, LevelSide.LOWER):
                key=f'{side.value.lower()}_{level:.3f}'; lp=bands[key]
                active=price>=lp if side is LevelSide.UPPER else price<=lp
                prior=self.inside.get(key, False)
                if active and not prior:
                    events.append(FBBLevelEvent(f'{self.symbol}-{timestamp.timestamp()}-{key}', self.symbol,self.timeframe,side,level,LevelEventType.ENTERED,price,lp,timestamp))
                elif (not active) and prior:
                    events.append(FBBLevelEvent(f'{self.symbol}-{timestamp.timestamp()}-{key}-exit', self.symbol,self.timeframe,side,level,LevelEventType.EXITED,price,lp,timestamp))
                self.inside[key]=active
        return events
