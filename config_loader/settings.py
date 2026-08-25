from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # lightweight fallback for bundled examples
    yaml = None

@dataclass
class FBBConfig:
    enabled: bool=True; length:int=200; source:str='hlc3'; multiplier:float=3.0; std_ddof:int=0; levels:list[float]=field(default_factory=lambda:[.236,.382,.5,.618,.764,1.0])
@dataclass
class SymbolBlock: enabled:bool=True; name:str=''; mt5_symbol:str=''
@dataclass
class MarketConfig: timeframe:str='M5'; data_source:str='MT5'
@dataclass
class EntryConfig:
    enabled:bool=True; setup_type:str='MEAN_REVERSION_REJECTION'; trigger_levels:list[float]=field(default_factory=lambda:[.618,.764,1.0]); min_penetration_points:float=0; atr_tolerance_multiplier:float=0.2; return_inside_required:bool=True; confirmation:str='CLOSED_CANDLE'; max_tracking_bars:int=3; duplicate_cooldown_seconds:int=900
@dataclass
class RiskConfig: enabled:bool=True; risk_per_trade_percent:float=1.0; fixed_lot:float|None=None; stop_loss:dict[str,Any]=field(default_factory=lambda:{'method':'FIXED_POINTS','points':300}); take_profit:dict[str,Any]=field(default_factory=lambda:{'method':'RISK_REWARD','rr':2.0})
@dataclass
class ExecutionConfig: enabled:bool=True; mode:str='PAPER'; require_human_approval:bool=True
@dataclass
class SymbolConfig: symbol:SymbolBlock; market:MarketConfig; fbb:FBBConfig; entry:EntryConfig; risk:RiskConfig; execution:ExecutionConfig
@dataclass
class GlobalConfig: app:dict[str,Any]; execution:dict[str,Any]; risk:dict[str,Any]; telegram:dict[str,Any]

def _primitive(v:str):
    v=v.strip().strip('"').strip("'")
    if v.lower() in {'true','false'}: return v.lower()=='true'
    if v.startswith('[') and v.endswith(']'): return [_primitive(x) for x in v[1:-1].split(',') if x.strip()]
    try: return int(v)
    except ValueError:
        try: return float(v)
        except ValueError: return v

def _mini_yaml(text:str)->dict[str,Any]:
    root:dict[str,Any]={}; stack=[(-1,root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.strip().startswith('#'): continue
        indent=len(raw)-len(raw.lstrip(' ')); line=raw.strip()
        while stack and indent<=stack[-1][0]: stack.pop()
        parent=stack[-1][1]
        if ':' in line:
            k,v=line.split(':',1); k=k.strip(); v=v.strip()
            if not v:
                parent[k]={}; stack.append((indent,parent[k]))
            else: parent[k]=_primitive(v)
    return root

def load_yaml(path: Path) -> dict[str,Any]:
    text=path.read_text()
    if yaml is not None: return yaml.safe_load(text) or {}
    return _mini_yaml(text)

def _make_symbol(d:dict[str,Any])->SymbolConfig:
    fbb=FBBConfig(**d.get('fbb',{}))
    if fbb.length < 1: raise ValueError('fbb.length must be >= 1')
    return SymbolConfig(SymbolBlock(**d.get('symbol',{})), MarketConfig(**d.get('market',{})), fbb, EntryConfig(**d.get('entry',{})), RiskConfig(**d.get('risk',{})), ExecutionConfig(**d.get('execution',{})))

def load_configs(config_dir: str='config') -> tuple[GlobalConfig, list[SymbolConfig]]:
    base=Path(config_dir); gd=load_yaml(base/'global.yaml')
    global_cfg=GlobalConfig(gd.get('app',{}), gd.get('execution',{}), gd.get('risk',{}), gd.get('telegram',{}))
    symbols=[_make_symbol(load_yaml(p)) for p in sorted((base/'symbols').glob('*.yaml'))]
    return global_cfg, [s for s in symbols if s.symbol.enabled]
