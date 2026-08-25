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
        if fbb_rows:
            upper=[r.get('upper_1.000') for r in fbb_rows]
            basis=[r.get('basis') for r in fbb_rows]
            lower=[r.get('lower_1.000') for r in fbb_rows]
            if any(v is not None for v in upper): plt.plot(x, upper, label='Upper FBB 1.000', color='red', linewidth=1.1)
            if any(v is not None for v in basis): plt.plot(x, basis, label='VWMA basis', color='magenta', linewidth=1.1)
            if any(v is not None for v in lower): plt.plot(x, lower, label='Lower FBB 1.000', color='green', linewidth=1.1)
        for y,label,color in [(proposal.signal.entry_price,'Entry','blue'),(proposal.stop_loss,'SL','red'),(proposal.take_profit,'TP','green')]: plt.axhline(y,label=label,color=color,linestyle='--')
        plt.title(f'FBB Proposal {proposal.signal.symbol} {proposal.signal.timeframe} {proposal.signal.direction.value}'); plt.legend(fontsize=8); plt.tight_layout(); plt.savefig(path,dpi=140); plt.close(); logger.info(section(SECTIONS['CHART_TELEGRAM'], f'[CHART]\nGenerated successfully\nPath={path}\nSymbol={proposal.signal.symbol}\nLevels={proposal.signal.trigger_level}\nPlottedFBB=Upper 1.000, VWMA basis, Lower 1.000\nEntry={proposal.signal.entry_price}\nSL={proposal.stop_loss}\nTP={proposal.take_profit}'), extra={'event':'CHART_GENERATION','symbol':proposal.signal.symbol,'proposal_id':proposal.proposal_id}); return path
