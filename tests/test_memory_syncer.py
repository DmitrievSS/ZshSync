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
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Создаем временный файл для локальной истории
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
        f.write(format_history_entry("command1"))
        f.write(format_history_entry("command2"))
        local_history_path = f.name
    
    try:
        # Создаем конфигурацию
        config = Config()
        config.paths.local_history = local_history_path
        config.settings.sync_type = 'memory'
        
        logger.info("Конфигурация создана")
        
        # Создаем стратегию
        strategy = MemoryHistorySyncStrategy(config)
        logger.info("Стратегия memory инициализирована")
        
        # Тест 1: Чтение локальной истории
        with open(local_history_path, 'r') as f:
            local_history = f.readlines()
        logger.info(f"Локальная история: {local_history}")
        
        # Тест 2: Запись в удаленную историю
        strategy.write_remote_history(local_history)
        strategy.commit_changes("Test commit")
        logger.info("История записана")
        
        # Тест 3: Чтение удаленной истории
        remote_history = strategy.read_remote_history()
        logger.info(f"Удаленная история: {remote_history}")
        
        # Проверяем, что истории совпадают
        assert remote_history == local_history, "Удаленная история не совпадает с локальной"
        
        # Тест 4: Добавление новой команды
        new_history = remote_history + [format_history_entry("command3")]
        strategy.write_remote_history(new_history)
        strategy.commit_changes("Add command3")
        logger.info("Добавлена новая команда")
        
        # Тест 5: Проверка обновленной истории
        updated_history = strategy.read_remote_history()
        logger.info(f"Обновленная история: {updated_history}")
        
        # Проверяем, что новая история содержит все команды
        assert len(updated_history) == len(new_history), "Неверное количество команд в истории"
        assert any("command3" in line for line in updated_history), "Новая команда не найдена в истории"
        
        logger.info("Все тесты пройдены успешно!")
        
    finally:
        # Удаляем временный файл
        os.unlink(local_history_path)
        logger.info("Временные файлы удалены")

if __name__ == '__main__':
    test_memory_syncer() 