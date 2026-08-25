from dataclasses import dataclass

@dataclass(frozen=True)
class FBBResult:
    rows: list[dict]
    levels: list[float]
    @property
    def frame(self):
        return self.rows
