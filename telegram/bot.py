import logging
from pathlib import Path
from core.models.trading import TradeProposal
from .messages import format_proposal
from .keyboards import approval_buttons
from utils.observability import SECTIONS, section
logger = logging.getLogger(__name__)
class TelegramBot:
    def __init__(self, token:str|None=None, chat_id:str|None=None, enabled:bool=False): self.token=token; self.chat_id=chat_id; self.enabled=enabled
    async def send_proposal(self, proposal:TradeProposal, chart_path:Path|None=None)->None:
        if not self.enabled:
            print(format_proposal(proposal)); print(approval_buttons(proposal))
            logger.info(section(SECTIONS['CHART_TELEGRAM'], f'[TELEGRAM]\nTelegram disabled; proposal printed locally\nSymbol={proposal.signal.symbol}\nSide={proposal.signal.direction.value}\nProposal={proposal.proposal_id}\nApprovalRequired=YES'), extra={'event':'TELEGRAM','symbol':proposal.signal.symbol,'proposal_id':proposal.proposal_id})
            return
        from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
        bot=Bot(self.token); kb=InlineKeyboardMarkup([[InlineKeyboardButton(b['text'], callback_data=b['callback_data']) for b in row] for row in approval_buttons(proposal)])
        try:
            if chart_path:
                msg = await bot.send_photo(self.chat_id, chart_path.open('rb'), caption=format_proposal(proposal), reply_markup=kb)
            else:
                msg = await bot.send_message(self.chat_id, format_proposal(proposal), reply_markup=kb)
            logger.info(section(SECTIONS['CHART_TELEGRAM'], f'[TELEGRAM]\nProposal sent\nSymbol={proposal.signal.symbol}\nSide={proposal.signal.direction.value}\nProposal={proposal.proposal_id}\nMessageId={getattr(msg, "message_id", "N/A")}\nApprovalRequired=YES'), extra={'event':'TELEGRAM','symbol':proposal.signal.symbol,'proposal_id':proposal.proposal_id})
        except Exception:
            logger.exception(section(SECTIONS['CHART_TELEGRAM'], f'[TELEGRAM ERROR]\nSymbol={proposal.signal.symbol}\nProposal={proposal.proposal_id}\nReason=send_proposal_failed'), extra={'event':'TELEGRAM','symbol':proposal.signal.symbol,'proposal_id':proposal.proposal_id})
            raise
