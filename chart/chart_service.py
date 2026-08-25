import logging
from pathlib import Path
import matplotlib.pyplot as plt
from core.models.trading import TradeProposal
from utils.observability import SECTIONS, section
logger = logging.getLogger(__name__)

class ChartService:
    def __init__(self, output_dir:str='charts'):
        self.output_dir=Path(output_dir); self.output_dir.mkdir(exist_ok=True)
    def _col(self, rows, name):
        if hasattr(rows, '__getitem__') and not isinstance(rows, list):
            return rows[name]
        return [r.get(name) for r in rows]
    def create_chart(self, candles, fbb_frame, proposal:TradeProposal)->Path:
        path=self.output_dir/f'{proposal.proposal_id}.png'
        candle_rows = candles.to_dict('records') if hasattr(candles, 'to_dict') else list(candles)
        fbb_rows = fbb_frame.to_dict('records') if hasattr(fbb_frame, 'to_dict') else list(fbb_frame)
        closes=[r['close'] if isinstance(r, dict) else r.close for r in candle_rows]
        x=range(len(closes))
        plt.figure(figsize=(9,5)); plt.plot(x, closes, label='Close', color='black')
        band_cols=[c for c in (fbb_rows[-1].keys() if fbb_rows else []) if c.startswith(('upper_','lower_'))]
        for col in band_cols:
            vals=[r.get(col) for r in fbb_rows]
            if any(v is not None for v in vals): plt.plot(x, vals, alpha=.25, linewidth=.7)
        basis=[r.get('basis') for r in fbb_rows]
        if any(v is not None for v in basis): plt.plot(x, basis, label='VWMA basis', color='magenta')
        for y,label,color in [(proposal.signal.entry_price,'Entry','blue'),(proposal.stop_loss,'SL','red'),(proposal.take_profit,'TP','green')]: plt.axhline(y,label=label,color=color,linestyle='--')
        plt.title(f'FBB Proposal {proposal.signal.symbol} {proposal.signal.timeframe} {proposal.signal.direction.value}'); plt.legend(fontsize=8); plt.tight_layout(); plt.savefig(path,dpi=140); plt.close(); logger.info(section(SECTIONS['CHART_TELEGRAM'], f'[CHART]\nGenerated successfully\nPath={path}\nSymbol={proposal.signal.symbol}\nLevels={proposal.signal.trigger_level}\nEntry={proposal.signal.entry_price}\nSL={proposal.stop_loss}\nTP={proposal.take_profit}'), extra={'event':'CHART_GENERATION','symbol':proposal.signal.symbol,'proposal_id':proposal.proposal_id}); return path
