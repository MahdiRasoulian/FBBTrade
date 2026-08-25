from config_loader.settings import load_configs
from utils.logging import configure_logging

def main():
    global_cfg, symbols = load_configs()
    configure_logging(global_cfg.app.get('log_level','INFO'))
    mode=global_cfg.execution.get('mode','PAPER')
    print(f'EXECUTION MODE: {mode}')
    print(f'Enabled symbols: {", ".join(s.symbol.name for s in symbols)}')
    print('FBBTrade scaffold ready. Run pytest for deterministic engine validation.')
if __name__=='__main__': main()
