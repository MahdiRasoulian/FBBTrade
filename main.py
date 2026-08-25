import asyncio
import logging
import os
import signal
from dataclasses import dataclass
from typing import Any

from chart.chart_service import ChartService
from config_loader.settings import SymbolConfig, load_configs
from entry.entry_machine import EntryMachine
from execution.execution_validator import ExecutionValidator
from indicators.fbb.calculator import FBBCalculator
from market_data.candle_manager import CandleManager
from market_data.mt5_provider import MT5Provider
from risk.risk_manager import RiskManager
from signals.level_detector import FBBLevelDetector
from storage.database import Database
from telegram.bot import TelegramBot
from utils.logging import configure_logging

logger=logging.getLogger(__name__)

@dataclass
class SymbolRuntime:
    config: SymbolConfig
    spec: Any
    candles: CandleManager
    fbb: FBBCalculator
    detector: FBBLevelDetector
    entry: EntryMachine

class TradingRuntime:
    def __init__(self, global_cfg, symbol_cfgs):
        self.global_cfg=global_cfg; self.symbol_cfgs=symbol_cfgs; self.running=True
        self.provider=MT5Provider(); self.db=Database(global_cfg.app.get('database_path','data/fbbtrade.db'))
        self.chart=ChartService(global_cfg.app.get('charts_dir','charts'))
        self.telegram=TelegramBot(os.getenv('TELEGRAM_BOT_TOKEN'), os.getenv('TELEGRAM_CHAT_ID'), bool(global_cfg.telegram.get('enabled', False)))
        self.risk=RiskManager(float(global_cfg.risk.get('account_equity',10000)), int(global_cfg.execution.get('proposal_expiry_seconds',300)))
        self.validator=ExecutionValidator(float(global_cfg.execution.get('max_price_deviation_points',100)), float(global_cfg.execution.get('max_spread_points',80)))
        self.symbols:list[SymbolRuntime]=[]
    def setup(self):
        self.provider.connect()
        for cfg in self.symbol_cfgs:
            spec=self.provider.symbol_spec(cfg.symbol.mt5_symbol)
            warmup=cfg.fbb.length+5
            self.symbols.append(SymbolRuntime(cfg, spec, CandleManager(self.provider,cfg.symbol.mt5_symbol,cfg.market.timeframe,warmup), FBBCalculator(cfg.fbb.length,cfg.fbb.multiplier,cfg.fbb.levels,cfg.fbb.std_ddof), FBBLevelDetector(cfg.symbol.name,cfg.market.timeframe,cfg.fbb.levels), EntryMachine(cfg.symbol.name,cfg.market.timeframe,cfg.entry)))
    async def run(self):
        self.setup()
        poll=float(os.getenv('FBB_POLL_SECONDS','1.0'))
        while self.running:
            await asyncio.gather(*(self.process_symbol_safely(s) for s in self.symbols))
            await asyncio.sleep(poll)
    async def process_symbol_safely(self, rt:SymbolRuntime):
        try:
            await self.process_symbol(rt)
        except Exception:
            logger.exception('Symbol processing failed for %s', rt.config.symbol.name)
    async def process_symbol(self, rt:SymbolRuntime):
        tick=self.provider.latest_tick(rt.config.symbol.mt5_symbol)
        closed, forming=rt.candles.snapshot()
        if len(closed) < rt.config.fbb.length: return
        records=rt.candles.to_records(closed)
        fbb_result=rt.fbb.calculate(records)
        latest=fbb_result.frame[-1]
        bands={k:v for k,v in latest.items() if k.startswith(('upper_','lower_')) and v is not None}
        tolerance=rt.candles.atr(closed)*float(getattr(rt.config.entry, 'atr_tolerance_multiplier', 0.0))
        bands['atr_tolerance']=tolerance
        for event in rt.detector.detect(tick.mid, bands, tick.timestamp, tolerance=tolerance):
            self.db.store('level_event', event.event_id, event.__dict__)
            rt.entry.on_level_event(event)
        if rt.candles.has_new_closed_candle(closed):
            signals=rt.entry.on_candle_close(closed[-1].close, bands, closed[-1].timestamp)
            for sig in signals:
                proposal=self.risk.create_proposal(sig, rt.spec, rt.config.risk)
                validation=self.validator.validate(proposal, tick, rt.spec)
                self.db.store('entry_signal', sig.signal_id, sig.__dict__)
                if not validation.ok:
                    self.db.store('proposal_rejected_pre_telegram', proposal.proposal_id, {'reason':validation.reason})
                    continue
                chart_path=self.chart.create_chart(records, fbb_result.frame, proposal)
                self.db.store('trade_proposal', proposal.proposal_id, proposal.__dict__)
                await self.telegram.send_proposal(proposal, chart_path)

def _load_dotenv():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

def main():
    _load_dotenv()
    global_cfg, symbols = load_configs(os.getenv('FBB_CONFIG_DIR','config'))
    configure_logging(global_cfg.app.get('log_level','INFO'))
    mode=global_cfg.execution.get('mode','PAPER')
    print(f'EXECUTION MODE: {mode}')
    print(f'Enabled symbols: {", ".join(s.symbol.name for s in symbols)}')
    runtime=TradingRuntime(global_cfg, symbols)
    loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    def stop_runtime(*_):
        runtime.running=False
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_runtime)
        except (NotImplementedError, RuntimeError):
            signal.signal(sig, stop_runtime)
    try:
        loop.run_until_complete(runtime.run())
    except KeyboardInterrupt:
        runtime.running=False
        loop.run_until_complete(asyncio.sleep(0))
    finally:
        loop.close()

if __name__=='__main__': main()
