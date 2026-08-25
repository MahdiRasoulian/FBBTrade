from pathlib import Path
import matplotlib.pyplot as plt
from core.models.trading import TradeProposal
class ChartService:
    def __init__(self, output_dir:str='charts'): self.output_dir=Path(output_dir); self.output_dir.mkdir(exist_ok=True)
    def create_chart(self, candles, fbb_frame, proposal:TradeProposal)->Path:
        path=self.output_dir/f'{proposal.proposal_id}.png'
        plt.figure(figsize=(9,5)); x=range(len(candles)); plt.plot(x,candles['close'],label='Close',color='black')
        for col in [c for c in fbb_frame.columns if c.startswith(('upper_','lower_'))][-6:]: plt.plot(x,fbb_frame[col],alpha=.35,linewidth=.8)
        plt.plot(x,fbb_frame['basis'],label='VWMA basis',color='magenta')
        for y,label,color in [(proposal.signal.entry_price,'Entry','blue'),(proposal.stop_loss,'SL','red'),(proposal.take_profit,'TP','green')]: plt.axhline(y,label=label,color=color,linestyle='--')
        plt.title(f'FBB Proposal {proposal.signal.symbol} {proposal.signal.timeframe} {proposal.signal.direction.value}'); plt.legend(fontsize=8); plt.tight_layout(); plt.savefig(path,dpi=140); plt.close(); return path
