import os
import configparser
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import logging

@dataclass
class PathsConfig:
    """Конфигурация путей"""
    local_history: str
    remote_history: str
    git_repo: str
    log_file: str = '~/.history_syncer/history_syncer.log'
    pid_file: str = '~/.history_syncer/history_syncer.pid'

@dataclass
class SettingsConfig:
    """Конфигурация общих настроек"""
    sync_interval_seconds: int = 3600  # 1 час по умолчанию
    sync_type: str = 'git'  # тип синхронизации по умолчанию

@dataclass
class GitConfig:
    """Конфигурация git"""
    repository_url: Optional[str] = None
    branch: str = 'main'
    remote_name: str = 'origin'

@dataclass
class Config:
    """Основной класс конфигурации"""
    paths: PathsConfig = field(default_factory=PathsConfig)
    settings: SettingsConfig = field(default_factory=SettingsConfig)
    git: GitConfig = field(default_factory=GitConfig)
    
    def __init__(self, config_path: str = 'config.ini'):
        self.config_path = config_path
        logging.info(f"Инициализация Config с путем: {self.config_path}")
        
        self.paths = PathsConfig(
            local_history='~/.zsh_history',
            remote_history='history.txt',
            git_repo='~/.zsh_history_git',
            log_file='~/.history_syncer/history_syncer.log',
            pid_file='~/.history_syncer/history_syncer.pid'
        )
        logging.info(f"Пути по умолчанию: {self.paths}")
        
        self.settings = SettingsConfig()
        self.git = GitConfig()
        self._load_or_create_config()
    
    def _load_or_create_config(self):
        """Загружает существующий конфиг или создает новый с настройками по умолчанию"""
        if os.path.exists(self.config_path):
            self._load_config()
        else:
            self._create_default_config()
    
    def _create_default_config(self):
        """Создает конфигурационный файл с настройками по умолчанию"""
        config = configparser.ConfigParser()
        
        # Сохраняем текущие значения в конфиг
        config['Paths'] = {
            'local_history': self.paths.local_history,
            'remote_history': self.paths.remote_history,
            'git_repo': self.paths.git_repo,
            'log_file': self.paths.log_file,
            'pid_file': self.paths.pid_file
        }
        config['Settings'] = {
            'sync_interval_seconds': str(self.settings.sync_interval_seconds),
            'sync_type': self.settings.sync_type
        }
        config['Git'] = {
            'repository_url': self.git.repository_url or '',
            'branch': self.git.branch,
            'remote_name': self.git.remote_name
        }
        
        # Создаем директорию для конфига, если её нет
        config_dir = os.path.dirname(self.config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        with open(self.config_path, 'w') as f:
            config.write(f)
    
    def _load_config(self):
        """Загружает конфигурацию из файла"""
        config = configparser.ConfigParser()
        config.read(self.config_path)
        
        # Загружаем пути
        self.paths.local_history = config.get('Paths', 'local_history', 
                                            fallback=self.paths.local_history)
        self.paths.remote_history = config.get('Paths', 'remote_history', 
                                             fallback=self.paths.remote_history)
        self.paths.git_repo = config.get('Paths', 'git_repo', 
                                        fallback=self.paths.git_repo)
        self.paths.log_file = config.get('Paths', 'log_file',
                                       fallback=self.paths.log_file)
        self.paths.pid_file = config.get('Paths', 'pid_file',
                                       fallback=self.paths.pid_file)
        
        # Загружаем настройки
        self.settings.sync_interval_seconds = config.getint('Settings', 'sync_interval_seconds', 
                                                          fallback=self.settings.sync_interval_seconds)
        self.settings.sync_type = config.get('Settings', 'sync_type', 
                                           fallback=self.settings.sync_type)
        
        # Загружаем git настройки
        self.git.repository_url = config.get('Git', 'repository_url', 
                                           fallback=self.git.repository_url)
        self.git.branch = config.get('Git', 'branch', 
                                   fallback=self.git.branch)
        self.git.remote_name = config.get('Git', 'remote_name', 
                                        fallback=self.git.remote_name)
    
    def save(self):
        """Сохраняет текущую конфигурацию в файл"""
        self._create_default_config()
    
    def get_path(self, path: str) -> str:
        """Получает путь и расширяет ~ до домашней директории"""
        if not path:
            return path
            
        # Расширяем ~ до домашней директории
        expanded_path = os.path.expanduser(path)
        logging.info(f"Расширенный путь: {expanded_path}")
        
        # Если путь относительный, делаем его абсолютным относительно git_repo
        if not os.path.isabs(expanded_path):
            git_repo_path = os.path.expanduser(self.paths.git_repo)
            expanded_path = os.path.join(git_repo_path, expanded_path)
            logging.info(f"Относительный путь преобразован в абсолютный: {expanded_path}")
        
        return expanded_path 