import logging
from config import Config
from sync_strategies.factory import create_sync_strategy
from .sync_utils import sync_history

def sync_once(config: Config):
    """Performs one-time history synchronization"""
    logging.info("Starting one-time synchronization...")
    
    # Create sync strategy
    strategy = create_sync_strategy(config)
    
    # Perform synchronization
    sync_history(config, strategy)
    
    logging.info("Synchronization completed") 