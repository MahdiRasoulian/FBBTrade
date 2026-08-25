import math
from core.models.market import SymbolSpec

def normalize_volume(volume:float, spec:SymbolSpec)->float:
    steps=math.floor((volume-spec.min_lot)/spec.lot_step)
    normalized=spec.min_lot+max(0,steps)*spec.lot_step
    return round(min(max(normalized, spec.min_lot), spec.max_lot), 8)
def lot_size_for_risk(risk_amount:float, entry:float, stop:float, spec:SymbolSpec)->float:
    distance=abs(entry-stop)
    if distance<=0: raise ValueError('entry and stop cannot be equal')
    value_per_lot=(distance/spec.tick_size)*spec.tick_value
    if value_per_lot<=0: raise ValueError('invalid symbol tick specification')
    return normalize_volume(risk_amount/value_per_lot, spec)
