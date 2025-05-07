#!/usr/bin/env python3
import os
import sys
import logging
import logging.handlers
from config import Config
from cli import create_parser
from actions import sync_once, clear_remote_history, stop_daemon, restart_daemon, run_daemon

def setup_logging():
    """Настройка логирования"""
    log_dir = os.path.expanduser('~/.history_syncer')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'history_syncer.log')
    
    # Настраиваем файловый логгер
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.root.addHandler(file_handler)
    
    logging.root.setLevel(logging.INFO)
    return [file_handler]

def main():
    """Основная функция"""
    args = create_parser().parse_args()
    
    # Определяем путь к конфигурационному файлу
    if args.config:
        config_path = os.path.expanduser(args.config)
        if not os.path.exists(config_path):
            print(f"Ошибка: конфигурационный файл не найден: {config_path}")
            sys.exit(1)
    else:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    
    # Загружаем конфигурацию
    config = Config(config_path)
    
    # Настраиваем логирование
    setup_logging()
    logging.info(f"Используется конфигурационный файл: {config_path}")
    
    if args.restart:
        restart_daemon(config)
    elif args.stop:
        stop_daemon(config)
    elif args.clear_remote:
        clear_remote_history(config)
    elif args.once:
        sync_once(config)
    else:
        # Если запускаем как демон, перенаправляем вывод в файл логов
        if not args.once and not args.stop and not args.clear_remote and not args.restart:
            log_file = config.get_path(config.paths.log_file)
            sys.stdout = open(log_file, 'a')
            sys.stderr = sys.stdout
        run_daemon(config)

if __name__ == '__main__':
    main() 