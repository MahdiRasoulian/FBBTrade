from pathlib import Path
from core.models.trading import TradeProposal
from .messages import format_proposal
from .keyboards import approval_buttons
class TelegramBot:
    def __init__(self, token:str|None=None, chat_id:str|None=None, enabled:bool=False): self.token=token; self.chat_id=chat_id; self.enabled=enabled
    async def send_proposal(self, proposal:TradeProposal, chart_path:Path|None=None)->None:
        if not self.enabled: print(format_proposal(proposal)); print(approval_buttons(proposal)); return
        from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
        bot=Bot(self.token); kb=InlineKeyboardMarkup([[InlineKeyboardButton(b['text'], callback_data=b['callback_data']) for b in row] for row in approval_buttons(proposal)])
        if chart_path: await bot.send_photo(self.chat_id, chart_path.open('rb'), caption=format_proposal(proposal), reply_markup=kb)
        else: await bot.send_message(self.chat_id, format_proposal(proposal), reply_markup=kb)
