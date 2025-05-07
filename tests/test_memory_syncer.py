#!/usr/bin/env python3
import os
import tempfile
import logging
import time
from config import Config
from sync_strategies import MemoryHistorySyncStrategy

def format_history_entry(command: str) -> str:
    """Форматирует команду в формат zsh истории"""
    timestamp = int(time.time())
    return f": {timestamp}:0;{command}\n"

def test_memory_syncer():
    """Тест синхронизации в памяти"""
    config = Config()
    config.config = {
        'sync_type': 'memory',
        'paths': {
            'local_history': '/tmp/test_history',
            'remote_history': '/tmp/test_remote_history',
            'log_file': '/tmp/test.log',
            'pid_file': '/tmp/test.pid'
        }
    }
    strategy = MemoryHistorySyncStrategy(config)
    
    # Тест записи и чтения
    test_history = ['command1', 'command2']
    strategy.write_remote_history(test_history)
    assert strategy.read_remote_history() == test_history
    
    # Тест добавления новых команд
    new_history = ['command1', 'command2', 'command3']
    strategy.write_remote_history(new_history)
    assert strategy.read_remote_history() == new_history
    
    # Тест очистки
    strategy.clear_remote_history()
    assert strategy.read_remote_history() == []

if __name__ == '__main__':
    test_memory_syncer() 