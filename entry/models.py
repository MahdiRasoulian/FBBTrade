from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from signals.models import FBBLevelEvent
class EntryState(str, Enum): IDLE='IDLE'; FBB_LEVEL_DETECTED='FBB_LEVEL_DETECTED'; TRACKING='TRACKING'; REACTION_DETECTED='REACTION_DETECTED'; ENTRY_CONFIRMED='ENTRY_CONFIRMED'; INVALIDATED='INVALIDATED'; TIMEOUT='TIMEOUT'; WAITING_APPROVAL='WAITING_APPROVAL'; REJECTED='REJECTED'
@dataclass
class SetupTracker:
    event:FBBLevelEvent; state:EntryState; created_at:datetime; bars_seen:int=0; max_excursion:float=0.0
