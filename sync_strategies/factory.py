from typing import Type, Dict
from config import Config
from .base import HistorySyncStrategy
from .git import GitHistorySyncStrategy
from .ssh import SSHHistorySyncStrategy
import logging

# Реестр доступных стратегий
STRATEGIES: Dict[str, Type[HistorySyncStrategy]] = {
    'git': GitHistorySyncStrategy,
    'ssh': SSHHistorySyncStrategy
}

def create_sync_strategy(config: Config) -> HistorySyncStrategy:
    """
    Создает стратегию синхронизации на основе конфигурации
    Args:
        config: конфигурация
    Returns:
        HistorySyncStrategy: стратегия синхронизации
    """
    logging.info(f"Creating sync strategy with type: {config.sync_type}")
    strategy_class = STRATEGIES.get(config.sync_type)
    if not strategy_class:
        raise ValueError(f"Неизвестный тип синхронизации: {config.sync_type}")
    return strategy_class(config) 