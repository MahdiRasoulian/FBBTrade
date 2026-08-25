from math import sqrt
from .models import FBBResult

class FBBCalculator:
    """TradingView parity: HLC3=(H+L+C)/3, VWMA=sum(src*volume)/sum(volume), stdev uses population ddof=0 by default."""
    def __init__(self, length:int=200, multiplier:float=3.0, levels:list[float]|None=None, std_ddof:int=0):
        self.length=length; self.multiplier=multiplier; self.levels=levels or [1.0]; self.std_ddof=std_ddof
    def _records(self, candles):
        if hasattr(candles, 'to_dict'):
            return candles.to_dict('records')
        return list(candles)
    def calculate(self, candles) -> FBBResult:
        rows=self._records(candles)
        required={'high','low','close','volume'}
        for r in rows:
            missing=required-set(r)
            if missing: raise ValueError(f'missing candle columns: {sorted(missing)}')
        out=[]
        hlc3=[]; vols=[]
        for r in rows:
            row=dict(r); src=(row['high']+row['low']+row['close'])/3.0
            row['hlc3']=src; hlc3.append(src); vols.append(row['volume'])
            if len(hlc3) >= self.length:
                xs=hlc3[-self.length:]; vs=vols[-self.length:]; v_sum=sum(vs)
                basis=None if v_sum==0 else sum(x*v for x,v in zip(xs,vs))/v_sum
                mean=sum(xs)/self.length
                denom=self.length-self.std_ddof
                std=sqrt(sum((x-mean)**2 for x in xs)/denom) if denom>0 else None
                dev=None if std is None else self.multiplier*std
                row['basis']=basis; row['std']=std; row['deviation']=dev
                for level in self.levels:
                    key=f'{level:.3f}'
                    row[f'upper_{key}']=None if basis is None or dev is None else basis+level*dev
                    row[f'lower_{key}']=None if basis is None or dev is None else basis-level*dev
            else:
                row['basis']=row['std']=row['deviation']=None
                for level in self.levels:
                    key=f'{level:.3f}'; row[f'upper_{key}']=row[f'lower_{key}']=None
            out.append(row)
        return FBBResult(out,self.levels)
