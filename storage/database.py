import sqlite3, json
from pathlib import Path
class Database:
    def __init__(self,path='data/fbbtrade.db'):
        self.path=Path(path); self.path.parent.mkdir(exist_ok=True); self.conn=sqlite3.connect(self.path); self.init()
    def init(self):
        self.conn.execute('create table if not exists events(id integer primary key, kind text, correlation_id text, payload text, created_at text default current_timestamp)'); self.conn.commit()
    def store(self, kind:str, correlation_id:str, payload:dict):
        self.conn.execute('insert into events(kind,correlation_id,payload) values(?,?,?)',(kind,correlation_id,json.dumps(payload,default=str))); self.conn.commit()
