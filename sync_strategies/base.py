from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
import logging




class HistorySyncStrategy(ABC):
    """Абстрактный базовый класс для стратегий синхронизации истории"""
    
    @abstractmethod
    def read_remote_history(self) -> list:
        """Читает удаленную историю"""
        pass
    
    @abstractmethod
    def write_remote_history(self, new_history: list):
        """Записывает удаленную историю"""
        pass
    
    @abstractmethod
    def clear_remote_history(self):
        """Очищает удаленную историю"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Очищает ресурсы стратегии"""
        pass 