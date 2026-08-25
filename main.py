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
from utils.observability import (
    SECTIONS,
    event_block,
    fbb_block,
    level_map_block,
    market_block,
    nearest_level,
    no_event_block,
    runtime_status_block,
    section,
)
from utils.time import utc_now

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
        self._symbol_state: dict[str, dict[str, Any]] = {}

    def setup(self):
        log_event(logger, logging.INFO, 'STARTUP', 'Starting FBBTrade runtime', mode=self.global_cfg.execution.get('mode', 'PAPER'))
        logger.info(section(SECTIONS['MARKET'], '[MT5] Connecting to MetaTrader 5 provider'), extra={'event': 'MT5_CONNECTION'})
        self.provider.connect()
        logger.info(section(SECTIONS['MARKET'], '[MT5] Connected'), extra={'event': 'MT5_CONNECTION', 'mt5_state': 'CONNECTED'})
        for cfg in self.symbol_cfgs:
            try:
                spec = self.provider.symbol_spec(cfg.symbol.mt5_symbol)
                logger.info(section(SECTIONS['MARKET'], f'[MT5] Symbol validated\nSymbol={cfg.symbol.name} | MT5Symbol={cfg.symbol.mt5_symbol} | Point={spec.point} | Digits={spec.digits} | VolumeMin={spec.min_lot} | VolumeMax={spec.max_lot} | VolumeStep={spec.lot_step}'), extra={'event': 'SYMBOL_VALIDATION', 'symbol': cfg.symbol.name, 'mt5_symbol': cfg.symbol.mt5_symbol})
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
                for state in self._symbol_state.values():
                    logger.info(runtime_status_block(state), extra={'event': 'HEARTBEAT', 'symbol': state.get('symbol')})
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
        last_closed = closed[-1].timestamp if closed else None
        is_new_closed = rt.candles.has_new_closed_candle(closed)
        logger.debug(market_block(symbol, rt.config.symbol.mt5_symbol, rt.config.market.timeframe, tick, closed, forming, self.provider.is_connected()), extra={'event': 'MARKET_DATA', 'symbol': symbol})
        if len(closed) < rt.config.fbb.length:
            log_event(logger, logging.DEBUG, 'CANDLE_UPDATES', 'Waiting for FBB warmup candles', symbol=symbol, closed_candles=len(closed), required=rt.config.fbb.length)
            self._symbol_state[symbol] = {'symbol': symbol, 'mt5_state': 'CONNECTED' if self.provider.is_connected() else 'DISCONNECTED', 'mode': self.global_cfg.execution.get('mode', 'PAPER'), 'price': tick.mid, 'spread': tick.spread, 'entry_state': 'WARMUP', 'active_setups': 0, 'entry_detail': f'Waiting for {rt.config.fbb.length} closed candles', 'last_closed_candle': last_closed, 'last_successful_cycle': utc_now(), 'pending_proposals': 0}
            return
        records = rt.candles.to_records(closed)
        fbb_result = rt.fbb.calculate(records)
        latest = fbb_result.frame[-1]
        bands = {k: v for k, v in latest.items() if k.startswith(('upper_', 'lower_')) and v is not None}
        tolerance = rt.candles.atr(closed) * float(getattr(rt.config.entry, 'atr_tolerance_multiplier', 0.0))
        bands['atr_tolerance'] = tolerance
        closest = nearest_level(tick.mid, bands, rt.config.fbb.levels)
        entry_state = rt.entry.state_snapshot(tick.mid, bands, tick.timestamp)
        self._symbol_state[symbol] = {'symbol': symbol, 'mt5_state': 'CONNECTED' if self.provider.is_connected() else 'DISCONNECTED', 'mode': self.global_cfg.execution.get('mode', 'PAPER'), 'price': tick.mid, 'spread': tick.spread, 'basis': latest.get('basis'), 'nearest_level': None if closest is None else closest.label, 'nearest_distance': None if closest is None else closest.distance, 'location_status': None if closest is None else closest.status, **entry_state, 'last_closed_candle': last_closed, 'last_successful_cycle': utc_now(), 'pending_proposals': 0}
        if is_new_closed:
            logger.info(market_block(symbol, rt.config.symbol.mt5_symbol, rt.config.market.timeframe, tick, closed, forming, self.provider.is_connected()), extra={'event': 'MARKET_DATA', 'symbol': symbol})
            logger.info(fbb_block(symbol, rt.config.market.timeframe, rt.config.fbb, latest), extra={'event': 'FBB_CALCULATION', 'symbol': symbol})
            logger.info(level_map_block(symbol, rt.config.market.timeframe, tick.mid, bands, rt.config.fbb.levels, latest.get('basis')), extra={'event': 'PRICE_LOCATION', 'symbol': symbol})
            logger.info(section(SECTIONS['ENTRY'], f'[ENTRY STATE]\nSymbol={symbol} | State={entry_state["state"]} | ActiveSetups={entry_state["active_setups"]}\n{entry_state["detail"]}'), extra={'event': 'ENTRY_STATE', 'symbol': symbol})
        else:
            logger.debug(level_map_block(symbol, rt.config.market.timeframe, tick.mid, bands, rt.config.fbb.levels, latest.get('basis')), extra={'event': 'PRICE_LOCATION', 'symbol': symbol})
        events = rt.detector.detect(tick.mid, bands, tick.timestamp, tolerance=tolerance)
        if not events and is_new_closed:
            logger.info(no_event_block(symbol, tick.mid, closest), extra={'event': 'FBB_LEVEL_EVENTS', 'symbol': symbol})
        for event in events:
            logger.info(event_block(event), extra={'event': 'FBB_LEVEL_EVENTS', 'symbol': symbol, 'event_type': event.event_type.value, 'level': event.level_name})
            self.db.store('level_event', event.event_id, event.__dict__)
            rt.entry.on_level_event(event)
        if is_new_closed:
            log_event(logger, logging.INFO, 'CANDLE_UPDATES', 'New closed candle detected', symbol=symbol, timestamp=closed[-1].timestamp, close=closed[-1].close)
            signals = rt.entry.on_candle_close(closed[-1].close, bands, closed[-1].timestamp)
            for sig in signals:
                proposal = self.risk.create_proposal(sig, rt.spec, rt.config.risk)
                validation = self.validator.validate(proposal, tick, rt.spec)
                self.db.store('entry_signal', sig.signal_id, sig.__dict__)
                if not validation.ok:
                    logger.warning(section(SECTIONS['RISK'], f'[PROPOSAL REJECTED]\nSymbol={symbol}\nProposal={proposal.proposal_id}\nReason={validation.reason}\nDecision=NO_TELEGRAM_NO_EXECUTION'), extra={'event': 'PROPOSAL_REJECTIONS', 'symbol': symbol, 'proposal_id': proposal.proposal_id})
                    self.db.store('proposal_rejected_pre_telegram', proposal.proposal_id, {'reason': validation.reason})
                    continue
                chart_path = self.chart.create_chart(records, fbb_result.frame, proposal)
                self.db.store('trade_proposal', proposal.proposal_id, proposal.__dict__)
                logger.info(section(SECTIONS['APPROVAL_EXECUTION'], f'[APPROVAL]\nProposal={proposal.proposal_id}\nStatus=PENDING_HUMAN_APPROVAL\nExecutionMode={self.global_cfg.execution.get("mode", "PAPER")}\nExecutionAttempted=NO'), extra={'event': 'HUMAN_APPROVAL', 'symbol': symbol, 'proposal_id': proposal.proposal_id})
                await self.telegram.send_proposal(proposal, chart_path)

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
    except Exception:
        logger.exception(section(SECTIONS['STATUS'], '[ERROR] Runtime stopped by unhandled startup/runtime exception'), extra={'event': 'ERRORS'})
        raise
    finally:
        loop.close()
        logging.shutdown()

if __name__ == '__main__':
    main()
