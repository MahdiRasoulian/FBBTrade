from core.models.trading import Direction
def fixed_stop(entry:float, direction:Direction, points:float, point:float)->float:
    return entry - points*point if direction is Direction.BUY else entry + points*point
