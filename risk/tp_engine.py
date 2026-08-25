from core.models.trading import Direction
def rr_take_profit(entry:float, stop:float, direction:Direction, rr:float)->float:
    risk=abs(entry-stop)
    return entry + risk*rr if direction is Direction.BUY else entry - risk*rr
