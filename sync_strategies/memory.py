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
    
    def write_remote_history(self, history: List[str]):
        """Запись удаленной истории"""
        self.history = history.copy()
    
    def commit_changes(self, message: str):
        """Сохранение изменений (в памяти ничего не делаем)"""
        pass 