import os
import yaml
import logging
from typing import Dict, Any, Optional

class Config:
    """Класс для работы с конфигурацией"""

    def __init__(self, config_path: str = 'config.yaml'):
        """
        Инициализация конфигурации
        Args:
            config_path: путь к файлу конфигурации
        """
        self.config_path = os.path.expanduser(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Загрузка конфигурации из файла
        Returns:
            Dict: словарь с конфигурацией
        """
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                logging.info(f"Используется конфигурационный файл: {self.config_path}")
                return config
        except FileNotFoundError:
            logging.error(f"Файл конфигурации не найден: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logging.error(f"Ошибка при чтении файла конфигурации: {e}")
            raise

    @property
    def sync_type(self) -> str:
        """Тип синхронизации (git/ssh)"""
        return self.config.get('settings', {}).get('sync_type', 'git')

    @property
    def sync_interval_seconds(self) -> int:
        """Интервал синхронизации в секундах"""
        return self.config.get('sync_interval_seconds', 3600)

    @property
    def local_history_path(self) -> str:
        """Путь к локальному файлу истории"""
        return os.path.expanduser(self.config['paths']['local_history'])

    @property
    def remote_history_path(self) -> str:
        """Путь к удаленному файлу истории"""
        return self.config['paths']['remote_history']

    @property
    def git_repo_path(self) -> str:
        """Путь к локальному git репозиторию"""
        return os.path.expanduser(self.config['paths']['git_repo'])

    @property
    def log_file_path(self) -> str:
        """Путь к файлу логов"""
        return os.path.expanduser(self.config['paths']['log_file'])

    @property
    def pid_file_path(self) -> str:
        """Путь к PID файлу"""
        return os.path.expanduser(self.config['paths']['pid_file'])

    @property
    def git_config(self) -> Dict[str, Any]:
        """Конфигурация для Git стратегии"""
        return self.config.get('git', {})

    @property
    def ssh_config(self) -> Dict[str, Any]:
        """Конфигурация для SSH стратегии"""
        return self.config.get('ssh', {})

    def get_git_param(self, param: str, default: Optional[Any] = None) -> Any:
        """
        Получение параметра Git конфигурации
        Args:
            param: имя параметра
            default: значение по умолчанию
        Returns:
            Any: значение параметра
        """
        git_config = self.config.get('git', {})
        value = git_config.get(param, default)
        if value is None:
            logging.error(f"Git parameter '{param}' not found in config")
        return value

    def get_ssh_param(self, param: str, default: Optional[Any] = None) -> Any:
        """
        Получение параметра SSH конфигурации
        Args:
            param: имя параметра
            default: значение по умолчанию
        Returns:
            Any: значение параметра
        """
        return self.ssh_config.get(param, default)

    def get_path(self, path: str) -> str:
        """Получает путь и расширяет ~ до домашней директории"""
        if not path:
            return path
            
        # Расширяем ~ до домашней директории
        expanded_path = os.path.expanduser(path)
        logging.info(f"Расширенный путь: {expanded_path}")
        
        # Если путь относительный, делаем его абсолютным относительно git_repo
        if not os.path.isabs(expanded_path):
            git_repo_path = os.path.expanduser(self.git_repo_path)
            expanded_path = os.path.join(git_repo_path, expanded_path)
            logging.info(f"Относительный путь преобразован в абсолютный: {expanded_path}")
        
        return expanded_path 