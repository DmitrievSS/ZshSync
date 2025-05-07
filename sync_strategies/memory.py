from typing import List
from .base import HistorySyncStrategy
from config import Config

class MemoryHistorySyncStrategy(HistorySyncStrategy):
    """Простая реализация стратегии для тестов, хранящая историю в памяти"""
    
    def __init__(self, config: Config):
        self.config = config
        self.history: List[str] = []
    
    def read_remote_history(self) -> List[str]:
        """Чтение удаленной истории"""
        return self.history.copy()
    
    def write_remote_history(self, new_history: list):
        """Записывает удаленную историю"""
        self.history = new_history

    def clear_remote_history(self):
        """Очищает удаленную историю"""
        self.history = []

    def cleanup(self):
        """Очищает ресурсы стратегии"""
        pass 