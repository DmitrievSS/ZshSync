from abc import ABC, abstractmethod

class HistorySyncStrategy(ABC):
    """Абстрактный базовый класс для стратегий синхронизации истории"""
    
    @abstractmethod
    def read_remote_history(self) -> list:
        """Чтение удаленной истории"""
        pass
    
    @abstractmethod
    def write_remote_history(self, history: list):
        """Запись удаленной истории"""
        pass
    
    @abstractmethod
    def commit_changes(self, message: str):
        """Сохранение изменений в удаленном хранилище"""
        pass 