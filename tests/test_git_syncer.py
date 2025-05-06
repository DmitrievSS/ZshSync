#!/usr/bin/env python3
import os
import tempfile
import shutil
import logging
import time
from config import Config
from sync_strategies import GitHistorySyncStrategy
import git

def format_history_entry(command: str) -> str:
    """Форматирует команду в формат zsh истории"""
    timestamp = int(time.time())
    return f": {timestamp}:0;{command}\n"

def test_git_syncer():
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Создаем временные директории для локальной истории и git репозитория
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
        f.write(format_history_entry("command1"))
        f.write(format_history_entry("command2"))
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
        
        # Получаем доступ к репозиторию
        repo = strategy.repo
        
        # Тест 1: Чтение локальной истории
        with open(local_history_path, 'r') as f:
            local_history = f.readlines()
        logger.info(f"Локальная история: {local_history}")
        
        # Тест 2: Запись в удаленную историю
        strategy.write_remote_history(local_history)
        strategy.commit_changes("Initial commit")
        logger.info("История записана и зафиксирована")
        
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
        
        # Тест 6: Очистка истории
        logger.info("Тестирование очистки истории...")
        assert strategy.clear_remote_history(), "Очистка истории не удалась"
        
        # Проверяем, что история пуста
        cleared_history = strategy.read_remote_history()
        logger.info(f"Очищенная история: {cleared_history}")
        assert len(cleared_history) == 0, "История не была очищена"
        
        # Проверяем, что файл истории существует и пуст
        history_file = os.path.join(remote_dir, 'history.txt')
        assert os.path.exists(history_file), "Файл истории не существует"
        with open(history_file, 'r') as f:
            content = f.read()
            assert len(content) == 0, "Файл истории не пуст"
        
        # Проверяем, что коммит с очисткой создан
        last_commit = repo.head.commit
        assert "Clear remote history" in last_commit.message, "Коммит очистки не найден"
        
        logger.info("Все тесты пройдены успешно!")
        
    finally:
        # Удаляем временные файлы
        os.unlink(local_history_path)
        shutil.rmtree(remote_dir)
        logger.info("Временные файлы удалены")

if __name__ == '__main__':
    test_git_syncer() 