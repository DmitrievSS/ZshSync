import argparse

def create_parser() -> argparse.ArgumentParser:
    """Создает парсер аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Синхронизатор истории команд zsh')
    
    parser.add_argument('--once', 
                       action='store_true', 
                       help='Выполнить однократную синхронизацию')
    
    parser.add_argument('--clear-remote', 
                       action='store_true', 
                       help='Очистить удаленную историю')
    
    parser.add_argument('--stop', 
                       action='store_true', 
                       help='Остановить демон')
    
    parser.add_argument('--restart', 
                       action='store_true', 
                       help='Перезапустить демон')
    
    parser.add_argument('--config', 
                       help='Путь к конфигурационному файлу')
    
    return parser 