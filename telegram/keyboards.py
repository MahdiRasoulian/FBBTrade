from core.models.trading import TradeProposal
def approval_buttons(p:TradeProposal)->list[list[dict[str,str]]]:
    return [[{'text':f'APPROVE {p.signal.direction.value}','callback_data':f'approve:{p.proposal_id}'}],[{'text':'REJECT','callback_data':f'reject:{p.proposal_id}'}]]
