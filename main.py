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
from utils.logging import configure_logging, log_event

logger = logging.getLogger(__name__)

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
        self.global_cfg = global_cfg
        self.symbol_cfgs = symbol_cfgs
        self.running = True
        self.provider = MT5Provider()
        self.db = Database(global_cfg.app.get('database_path', 'data/fbbtrade.db'))
        self.chart = ChartService(global_cfg.app.get('charts_dir', 'charts'))
        self.telegram = TelegramBot(os.getenv('TELEGRAM_BOT_TOKEN'), os.getenv('TELEGRAM_CHAT_ID'), bool(global_cfg.telegram.get('enabled', False)))
        self.risk = RiskManager(float(global_cfg.risk.get('account_equity', 10000)), int(global_cfg.execution.get('proposal_expiry_seconds', 300)))
        self.validator = ExecutionValidator(float(global_cfg.execution.get('max_price_deviation_points', 100)), float(global_cfg.execution.get('max_spread_points', 80)))
        self.symbols: list[SymbolRuntime] = []
        self._heartbeat_count = 0

    def setup(self):
        log_event(logger, logging.INFO, 'STARTUP', 'Starting FBBTrade runtime', mode=self.global_cfg.execution.get('mode', 'PAPER'))
        log_event(logger, logging.INFO, 'MT5_CONNECTION', 'Connecting to MT5')
        self.provider.connect()
        for cfg in self.symbol_cfgs:
            try:
                spec = self.provider.symbol_spec(cfg.symbol.mt5_symbol)
                log_event(logger, logging.INFO, 'SYMBOL_VALIDATION', 'Symbol validated', symbol=cfg.symbol.name, mt5_symbol=cfg.symbol.mt5_symbol, point=spec.point, digits=spec.digits)
                warmup = cfg.fbb.length + 5
                self.symbols.append(SymbolRuntime(
                    cfg, spec,
                    CandleManager(self.provider, cfg.symbol.mt5_symbol, cfg.market.timeframe, warmup),
                    FBBCalculator(cfg.fbb.length, cfg.fbb.multiplier, cfg.fbb.levels, cfg.fbb.std_ddof),
                    FBBLevelDetector(cfg.symbol.name, cfg.market.timeframe, cfg.fbb.levels),
                    EntryMachine(cfg.symbol.name, cfg.market.timeframe, cfg.entry),
                ))
                log_event(logger, logging.INFO, 'CONFIGURATION', 'Symbol runtime configured', symbol=cfg.symbol.name, timeframe=cfg.market.timeframe, fbb_length=cfg.fbb.length, fixed_lot=cfg.risk.fixed_lot)
            except Exception:
                logger.exception('Symbol setup failed', extra={'event': 'ERRORS', 'symbol': cfg.symbol.name})
        if not self.symbols:
            raise RuntimeError('No symbols were configured successfully')

    async def run(self):
        self.setup()
        poll = float(os.getenv('FBB_POLL_SECONDS', '1.0'))
        heartbeat_every = max(1, int(float(os.getenv('FBB_HEARTBEAT_SECONDS', '60')) / poll))
        while self.running:
            await asyncio.gather(*(self.process_symbol_safely(s) for s in self.symbols), return_exceptions=True)
            self._heartbeat_count += 1
            if self._heartbeat_count % heartbeat_every == 0:
                log_event(logger, logging.INFO, 'HEARTBEAT', 'Runtime heartbeat', symbols=[s.config.symbol.name for s in self.symbols])
            await asyncio.sleep(poll)
        log_event(logger, logging.INFO, 'SHUTDOWN', 'Runtime loop stopped')

    async def process_symbol_safely(self, rt: SymbolRuntime):
        try:
            await self.process_symbol(rt)
        except Exception:
            logger.exception('Symbol processing failed', extra={'event': 'ERRORS', 'symbol': rt.config.symbol.name})

    async def process_symbol(self, rt: SymbolRuntime):
        symbol = rt.config.symbol.name
        tick = self.provider.latest_tick(rt.config.symbol.mt5_symbol)
        closed, forming = rt.candles.snapshot()
        log_event(logger, logging.DEBUG, 'MARKET_DATA', 'Market data snapshot', symbol=symbol, closed_candles=len(closed), has_forming=forming is not None, bid=tick.bid, ask=tick.ask)
        if len(closed) < rt.config.fbb.length:
            log_event(logger, logging.DEBUG, 'CANDLE_UPDATES', 'Waiting for FBB warmup candles', symbol=symbol, closed_candles=len(closed), required=rt.config.fbb.length)
            return
        records = rt.candles.to_records(closed)
        fbb_result = rt.fbb.calculate(records)
        latest = fbb_result.frame[-1]
        bands = {k: v for k, v in latest.items() if k.startswith(('upper_', 'lower_')) and v is not None}
        tolerance = rt.candles.atr(closed) * float(getattr(rt.config.entry, 'atr_tolerance_multiplier', 0.0))
        bands['atr_tolerance'] = tolerance
        log_event(logger, logging.DEBUG, 'FBB_CALCULATION', 'FBB calculated', symbol=symbol, basis=latest.get('basis'), deviation=latest.get('deviation'), tolerance=tolerance)
        for event in rt.detector.detect(tick.mid, bands, tick.timestamp, tolerance=tolerance):
            log_event(logger, logging.INFO, 'FBB_LEVEL_EVENTS', 'FBB level event detected', symbol=symbol, event_type=event.event_type.value, level=event.level_name, price=event.price, level_price=event.level_price)
            self.db.store('level_event', event.event_id, event.__dict__)
            rt.entry.on_level_event(event)
        if rt.candles.has_new_closed_candle(closed):
            log_event(logger, logging.INFO, 'CANDLE_UPDATES', 'New closed candle detected', symbol=symbol, timestamp=closed[-1].timestamp, close=closed[-1].close)
            signals = rt.entry.on_candle_close(closed[-1].close, bands, closed[-1].timestamp)
            for sig in signals:
                log_event(logger, logging.INFO, 'ENTRY_SIGNALS', 'Entry signal confirmed', symbol=symbol, signal_id=sig.signal_id, direction=sig.direction.value, entry_price=sig.entry_price)
                proposal = self.risk.create_proposal(sig, rt.spec, rt.config.risk)
                log_event(logger, logging.INFO, 'RISK_CALCULATION', 'Risk proposal calculated', symbol=symbol, proposal_id=proposal.proposal_id, lot_size=proposal.lot_size, stop_loss=proposal.stop_loss, take_profit=proposal.take_profit)
                validation = self.validator.validate(proposal, tick, rt.spec)
                self.db.store('entry_signal', sig.signal_id, sig.__dict__)
                if not validation.ok:
                    log_event(logger, logging.WARNING, 'PROPOSAL_REJECTIONS', 'Proposal rejected before Telegram', symbol=symbol, proposal_id=proposal.proposal_id, reason=validation.reason)
                    self.db.store('proposal_rejected_pre_telegram', proposal.proposal_id, {'reason': validation.reason})
                    continue
                chart_path = self.chart.create_chart(records, fbb_result.frame, proposal)
                log_event(logger, logging.INFO, 'CHART_GENERATION', 'Proposal chart generated', symbol=symbol, proposal_id=proposal.proposal_id, chart_path=str(chart_path))
                self.db.store('trade_proposal', proposal.proposal_id, proposal.__dict__)
                log_event(logger, logging.INFO, 'TRADE_PROPOSALS', 'Trade proposal ready for human approval', symbol=symbol, proposal_id=proposal.proposal_id)
                await self.telegram.send_proposal(proposal, chart_path)
                log_event(logger, logging.INFO, 'TELEGRAM', 'Proposal notification sent or printed', symbol=symbol, proposal_id=proposal.proposal_id)

def _load_dotenv():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

def main():
    _load_dotenv()
    global_cfg, symbols = load_configs(os.getenv('FBB_CONFIG_DIR', 'config'))
    configure_logging(global_cfg.app.get('log_level', 'INFO'), global_cfg.app.get('log_file', 'logs/fbbtrade.log'))
    log_event(logger, logging.INFO, 'CONFIGURATION', 'Configuration loaded', enabled_symbols=[s.symbol.name for s in symbols])
    runtime = TradingRuntime(global_cfg, symbols)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    def stop_runtime(*_):
        runtime.running = False
        log_event(logger, logging.INFO, 'SHUTDOWN', 'Shutdown requested')
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, stop_runtime)
        except (ValueError, AttributeError):
            pass
    try:
        loop.run_until_complete(runtime.run())
    except KeyboardInterrupt:
        runtime.running = False
        loop.run_until_complete(asyncio.sleep(0))
    finally:
        loop.close()
        logging.shutdown()

if __name__ == '__main__':
    main()
