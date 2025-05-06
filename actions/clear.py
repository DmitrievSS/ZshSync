import logging
import sys
from config import Config
from sync_strategies.factory import create_sync_strategy

def clear_remote_history(config: Config):
    """Clears remote history"""
    logging.info("Clearing remote history...")
    
    # Create sync strategy
    strategy = create_sync_strategy(config)
    
    # Clear remote history
    if not strategy.clear_remote_history():
        logging.error("Failed to clear remote history")
        sys.exit(1)
    
    logging.info("Remote history cleared successfully") 