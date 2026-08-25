from pathlib import Path
import csv
from .models import FBBResult

def export_diagnostic_csv(result: FBBResult, path: str | Path) -> None:
    path=Path(path)
    cols=[]
    for r in result.rows:
        for c in r:
            if c in {'timestamp','close','hlc3','basis','std','deviation'} or c.startswith(('upper_','lower_')):
                if c not in cols: cols.append(c)
    with path.open('w', newline='') as f:
        w=csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows({k:r.get(k) for k in cols} for r in result.rows)
