from typing import Dict, Type
from .base import HistorySyncStrategy
from .git import GitHistorySyncStrategy
from .memory import MemoryHistorySyncStrategy
from config import Config

# Реестр доступных стратегий
STRATEGIES: Dict[str, Type[HistorySyncStrategy]] = {
    'git': GitHistorySyncStrategy,
    'memory': MemoryHistorySyncStrategy
}

def create_sync_strategy(config: Config) -> HistorySyncStrategy:
    """Создает стратегию синхронизации на основе конфигурации"""
    strategy_class = STRATEGIES.get(config.settings.sync_type)
    if not strategy_class:
        raise ValueError(f"Неизвестный тип синхронизации: {config.settings.sync_type}")
    return strategy_class(config) 