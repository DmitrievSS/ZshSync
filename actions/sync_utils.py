import logging
from config import Config
from sync_strategies.factory import create_sync_strategy

def sync_history(config: Config, strategy=None):
    """
    Performs history synchronization
    
    Args:
        config: Configuration
        strategy: Optional sync strategy. If not provided, a new one will be created
    
    Returns:
        tuple: (merged_history, final_history) - merged history and final history
    """
    if strategy is None:
        strategy = create_sync_strategy(config)
    
    # Read local history
    local_history = strategy._read_file_with_fallback(config.get_path(config.paths.local_history))
    
    # Read remote history
    remote_history = strategy.read_remote_history()
    
    # Merge histories
    merged_history = strategy.merge_histories(local_history, remote_history)
    
    # Save history to Git repository
    strategy.save_history(merged_history)
    
    # Write remote history and commit changes
    strategy.write_remote_history(merged_history)
    strategy.commit_changes("Sync history")
    
    # Read local history again to get new entries
    new_local_history = strategy._read_file_with_fallback(config.get_path(config.paths.local_history))
    
    # Merge new local history with synchronized history
    final_history = strategy.merge_histories(merged_history, new_local_history)
    
    # Update local history file
    strategy._write_file_safely(config.get_path(config.paths.local_history), final_history)
    
    return merged_history, final_history 