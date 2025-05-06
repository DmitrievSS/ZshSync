#!/usr/bin/env python3
import os
import tempfile
import shutil
import logging
import time
from config import Config
from sync_strategies import GitHistorySyncStrategy

def format_history_entry(command: str) -> str:
    """Форматирует команду в формат zsh истории"""
    timestamp = int(time.time())
    return f": {timestamp}:0;{command}\n"

def test_git_merge():
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Создаем временные директории для локальной истории и git репозитория
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
        f.write(format_history_entry("local_command1"))
        f.write(format_history_entry("local_command2"))
        local_history_path = f.name
    
    remote_dir = tempfile.mkdtemp()
    logger.info(f"Создан временный каталог для git: {remote_dir}")
    
    try:
        # Создаем конфигурацию
        config = Config()
        config.paths.local_history = local_history_path
        config.paths.remote_history = remote_dir
        config.paths.git_repo = remote_dir  # Используем тот же каталог для git репозитория
        config.settings.sync_type = 'git'
        config.git.repository_url = None  # Не используем удаленный репозиторий
        
        logger.info("Конфигурация создана")
        
        # Создаем стратегию
        strategy = GitHistorySyncStrategy(config)
        logger.info("Стратегия git инициализирована")
        
        # Шаг 1: Инициализируем удаленный репозиторий с существующей историей
        remote_history = [
            format_history_entry("remote_command1"),
            format_history_entry("remote_command2"),
            format_history_entry("remote_command3")
        ]
        strategy.write_remote_history(remote_history)
        strategy.commit_changes("Initial remote history")
        logger.info("Инициализирована удаленная история")
        
        # Шаг 2: Читаем локальную историю
        with open(local_history_path, 'r') as f:
            local_history = f.readlines()
        logger.info(f"Локальная история: {local_history}")
        
        # Шаг 3: Читаем удаленную историю
        current_remote_history = strategy.read_remote_history()
        logger.info(f"Текущая удаленная история: {current_remote_history}")
        
        # Шаг 4: Объединяем истории
        merged_history = list(set(local_history + current_remote_history))
        merged_history.sort()  # Сортируем по временным меткам
        
        # Шаг 5: Записываем объединенную историю
        strategy.write_remote_history(merged_history)
        strategy.commit_changes("Merge local and remote history")
        logger.info("Истории объединены")
        
        # Шаг 6: Проверяем результат
        final_history = strategy.read_remote_history()
        logger.info(f"Финальная история: {final_history}")
        
        # Проверяем, что все команды присутствуют
        assert len(final_history) == 5, "Неверное количество команд в объединенной истории"
        assert any("local_command1" in line for line in final_history), "Локальная команда 1 не найдена"
        assert any("local_command2" in line for line in final_history), "Локальная команда 2 не найдена"
        assert any("remote_command1" in line for line in final_history), "Удаленная команда 1 не найдена"
        assert any("remote_command2" in line for line in final_history), "Удаленная команда 2 не найдена"
        assert any("remote_command3" in line for line in final_history), "Удаленная команда 3 не найдена"
        
        # Проверяем, что история отсортирована по временным меткам
        timestamps = [int(line.split(':')[1].strip()) for line in final_history]
        assert timestamps == sorted(timestamps), "История не отсортирована по временным меткам"
        
        logger.info("Все тесты пройдены успешно!")
        
    finally:
        # Удаляем временные файлы
        os.unlink(local_history_path)
        shutil.rmtree(remote_dir)
        logger.info("Временные файлы удалены")

if __name__ == '__main__':
    test_git_merge() 