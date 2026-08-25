import pandas as pd
class CSVDataProvider:
    def __init__(self,path): self.path=path
    def candles(self): return pd.read_csv(self.path, parse_dates=['timestamp'])
