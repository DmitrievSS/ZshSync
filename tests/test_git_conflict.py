#!/usr/bin/env python3
import os
import tempfile
import shutil
import logging
import time
import git
from config import Config
from sync_strategies import GitHistorySyncStrategy

def format_history_entry(command: str, timestamp: int = None) -> str:
    """Форматирует команду в формат zsh истории"""
    if timestamp is None:
        timestamp = int(time.time())
    return f": {timestamp}:0;{command}\n"

def setup_remote_repo():
    """Создает временный удаленный репозиторий"""
    # Создаем временную рабочую директорию
    work_dir = tempfile.mkdtemp()
    work_repo = git.Repo.init(work_dir)
    
    # Создаем начальную историю
    history_file = os.path.join(work_dir, "history.txt")
    with open(history_file, 'w') as f:
        f.write(format_history_entry("initial_command1", 1000))
        f.write(format_history_entry("initial_command2", 2000))
    
    # Инициализируем рабочий репозиторий и создаем первый коммит
    work_repo.index.add(['history.txt'])
    initial_commit = work_repo.index.commit("Initial commit")
    
    # Создаем bare репозиторий
    remote_dir = tempfile.mkdtemp()
    bare_repo = git.Repo.init(remote_dir, bare=True)
    
    # Добавляем удаленный репозиторий
    work_repo.create_remote('origin', remote_dir)
    
    # Создаем ветку main и пушим её в удаленный репозиторий
    work_repo.create_head('main', initial_commit)
    work_repo.heads.main.checkout()
    work_repo.git.push('--set-upstream', 'origin', 'main')
    
    # Добавляем новые команды и создаем второй коммит
    with open(history_file, 'w') as f:
        f.write(format_history_entry("initial_command1", 1000))
        f.write(format_history_entry("initial_command2", 2000))
        f.write(format_history_entry("update_command1", 3000))
        f.write(format_history_entry("update_command2", 4000))
    
    # Коммитим и пушим изменения
    work_repo.index.add(['history.txt'])
    work_repo.index.commit("Update history")
    work_repo.git.push('origin', 'main')
    
    # Удаляем временную рабочую директорию
    shutil.rmtree(work_dir)
    
    return remote_dir, initial_commit.hexsha

def test_git_conflict():
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Создаем временные директории и получаем хеш первого коммита
    remote_dir, initial_commit_sha = setup_remote_repo()
    clone1_dir = tempfile.mkdtemp()  # Первый клон для эмуляции другого компьютера
    clone2_dir = tempfile.mkdtemp()  # Второй клон для нашего текущего компьютера
    
    try:
        # Клонируем репозиторий в обе директории
        repo1 = git.Repo.clone_from(remote_dir, clone1_dir)
        repo2 = git.Repo.clone_from(remote_dir, clone2_dir)
        
        # В первом клоне откатываемся к начальному коммиту и создаем новую ветку
        repo1.git.checkout(initial_commit_sha)
        repo1.git.checkout('-b', 'temp_branch')
        
        # Создаем новую историю в первом клоне (относительно первого коммита)
        history_file1 = os.path.join(clone1_dir, "history.txt")
        with open(history_file1, 'w') as f:
            f.write(format_history_entry("initial_command1", 1000))
            f.write(format_history_entry("initial_command2", 2000))
            f.write(format_history_entry("branch_command1", 5000))
            f.write(format_history_entry("branch_command2", 6000))
        
        # Коммитим изменения в первом клоне
        repo1.index.add([history_file1])
        repo1.index.commit("Add branch commands")
        
        # Переключаемся обратно на main и делаем force-push
        repo1.git.checkout('main')
        repo1.git.reset('--hard', 'temp_branch')  # Заменяем содержимое main веткой temp_branch
        repo1.git.push('--force', 'origin', 'main')
        
        # Создаем локальную историю во втором клоне
        local_history_dir = tempfile.mkdtemp()
        local_history_path = os.path.join(local_history_dir, "local_history.txt")
        with open(local_history_path, 'w') as f:
            f.write(format_history_entry("initial_command1", 1000))
            f.write(format_history_entry("initial_command2", 2000))
        
        # Создаем конфигурацию для второго клона
        config = Config()
        config.paths.local_history = local_history_path
        config.paths.remote_history = clone2_dir
        config.paths.git_repo = clone2_dir
        config.settings.sync_type = 'git'
        config.git.repository_url = remote_dir
        config.git.branch = 'main'
        
        # Создаем стратегию
        strategy = GitHistorySyncStrategy(config)
        
        # Пытаемся синхронизировать второй клон
        strategy.read_remote_history()
        
        # Проверяем результат
        with open(local_history_path, 'r') as f:
            final_history = f.readlines()
        
        # Проверяем, что все команды присутствуют
        assert len(final_history) == 4, "Неверное количество команд в объединенной истории"
        assert any("initial_command1" in line for line in final_history), "Начальная команда 1 не найдена"
        assert any("initial_command2" in line for line in final_history), "Начальная команда 2 не найдена"
        assert any("branch_command1" in line for line in final_history), "Команда ветки 1 не найдена"
        assert any("branch_command2" in line for line in final_history), "Команда ветки 2 не найдена"
        
        # Проверяем, что история отсортирована по временным меткам
        timestamps = [int(line.split(':')[1].strip()) for line in final_history]
        assert timestamps == sorted(timestamps), "История не отсортирована по временным меткам"
        
        # Проверяем, что нет дубликатов
        commands = [line.split(';')[1].strip() for line in final_history]
        assert len(commands) == len(set(commands)), "В истории есть дубликаты команд"
        
        logger.info("Все тесты пройдены успешно!")
        
    finally:
        # Удаляем временные файлы
        shutil.rmtree(remote_dir)
        shutil.rmtree(clone1_dir)
        shutil.rmtree(clone2_dir)
        shutil.rmtree(local_history_dir)
        logger.info("Временные файлы удалены")

if __name__ == '__main__':
    test_git_conflict() 