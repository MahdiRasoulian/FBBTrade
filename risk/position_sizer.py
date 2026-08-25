import math
from core.models.market import SymbolSpec

def normalize_volume(volume:float, spec:SymbolSpec)->float:
    if volume < spec.min_lot:
        raise ValueError(f'calculated volume {volume} is below broker minimum lot {spec.min_lot}')
    if volume > spec.max_lot:
        raise ValueError(f'calculated volume {volume} is above broker maximum lot {spec.max_lot}')
    steps=math.floor((volume-spec.min_lot)/spec.lot_step)
    normalized=spec.min_lot+steps*spec.lot_step
    return round(normalized, 8)

def fixed_lot_size(volume:float, spec:SymbolSpec)->float:
    return normalize_volume(volume, spec)

def lot_size_for_risk(risk_amount:float, entry:float, stop:float, spec:SymbolSpec)->float:
    distance=abs(entry-stop)
    if distance<=0: raise ValueError('entry and stop cannot be equal')
    value_per_lot=(distance/spec.tick_size)*spec.tick_value
    if value_per_lot<=0: raise ValueError('invalid symbol tick specification')
    return normalize_volume(risk_amount/value_per_lot, spec)
