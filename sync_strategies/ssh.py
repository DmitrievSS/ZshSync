#!/usr/bin/env python3
import os
import time
import logging
import subprocess
import tempfile
from typing import List, Optional
from .base import HistorySyncStrategy
from .decorators import retry
from config import Config

class SSHHistorySyncStrategy(HistorySyncStrategy):
    """Реализация синхронизации через SSH"""
    
    def __init__(self, config: Config):
        self.config = config
        self._setup_ssh_connection()
        self._setup_lock_file()
    
    def _setup_ssh_connection(self):
        """Настраивает SSH соединение"""
        try:
            # Формируем строку подключения
            self.ssh_connection = (
                f"{self.config.get_ssh_param('username')}@{self.config.get_ssh_param('host')}"
            )
            logging.info(f"SSH соединение настроено: {self.ssh_connection}")
        except Exception as e:
            logging.error(f"Ошибка при установке SSH соединения: {e}")
            raise
    
    def _setup_lock_file(self):
        """Настраивает файл блокировки"""
        self.lock_file = self.config.get_ssh_param('lock_file', 'zsh_sync_lock.lock')
        logging.info(f"Файл блокировки: {self.lock_file}")
    
    def _check_lock_file(self) -> bool:
        """Проверяет наличие файла блокировки"""
        try:
            result = subprocess.run(
                ['ssh', self.ssh_connection, f'test -f {self.lock_file}'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            logging.error(f"Ошибка при проверке файла блокировки: {e}")
            return False
    
    def _create_lock_file(self):
        """Создает файл блокировки"""
        try:
            subprocess.run(
                ['ssh', self.ssh_connection, f'touch {self.lock_file}'],
                check=True,
                capture_output=True,
                text=True
            )
            logging.info("Файл блокировки создан")
        except Exception as e:
            logging.error(f"Ошибка при создании файла блокировки: {e}")
            raise
    
    def _remove_lock_file(self):
        """Удаляет файл блокировки"""
        try:
            subprocess.run(
                ['ssh', self.ssh_connection, f'rm -f {self.lock_file}'],
                check=True,
                capture_output=True,
                text=True
            )
            logging.info("Файл блокировки удален")
        except Exception as e:
            logging.error(f"Ошибка при удалении файла блокировки: {e}")
            raise
    
    def _wait_for_lock_with_timeout(self, timeout: int = 5) -> bool:
        """Ожидает освобождения файла блокировки с таймаутом"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self._check_lock_file():
                return True
            time.sleep(0.1)
        return False
    
    def _wait_for_lock(self):
        """Ожидает освобождения файла блокировки"""
        if not self._wait_for_lock_with_timeout():
            raise TimeoutError("Таймаут ожидания файла блокировки")
    
    def _run_ssh_command(self, command: str, timeout: int = 10) -> str:
        """Выполняет SSH команду и возвращает результат"""
        ssh_command = [
            'ssh',
            '-o', 'BatchMode=yes',
            '-o', 'ConnectTimeout=5',
            f"{self.config.get_ssh_param('username')}@{self.config.get_ssh_param('host')}",
            command
        ]
        
        try:
            result = subprocess.run(
                ssh_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True
            )
            return result.stdout
        except subprocess.TimeoutExpired as e:
            logging.error(f"SSH команда превысила таймаут {timeout} секунд: {e}")
            raise
        except subprocess.CalledProcessError as e:
            logging.error(f"SSH команда завершилась с ошибкой: {e}")
            raise
        except Exception as e:
            logging.error(f"Ошибка при выполнении SSH команды: {e}")
            raise

    def read_remote_history(self) -> List[str]:
        """Читает удаленную историю через SSH"""
        try:
            output = self._run_ssh_command(f"cat {self.config.remote_history_path}")
            return output.splitlines()
        except subprocess.CalledProcessError as e:
            if "Permission denied" in str(e.stderr):
                logging.error("Отказано в доступе к удаленному файлу истории")
                raise
            elif "No such file" in str(e.stderr):
                logging.warning("Удаленный файл истории не существует")
                return []
            else:
                logging.error(f"Ошибка при чтении удаленной истории: {e}")
                raise
        except Exception as e:
            logging.error(f"Ошибка при чтении удаленной истории: {e}")
            raise

    def write_remote_history(self, history: List[str]) -> None:
        """Записывает историю на удаленный хост через SSH"""
        try:
            # Создаем временный файл с историей
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                temp_file.write('\n'.join(history))
                temp_file.flush()
                
                # Создаем родительскую директорию на удаленном хосте
                remote_dir = os.path.dirname(self.config.remote_history_path)
                mkdir_command = [
                    'ssh',
                    '-o', 'BatchMode=yes',
                    '-o', 'ConnectTimeout=5',
                    f"{self.config.get_ssh_param('username')}@{self.config.get_ssh_param('host')}",
                    f"mkdir -p {remote_dir}"
                ]
                subprocess.run(mkdir_command, capture_output=True, text=True, check=True)
                
                # Копируем файл на удаленный хост
                scp_command = [
                    'scp',
                    '-o', 'BatchMode=yes',
                    '-o', 'ConnectTimeout=5',
                    temp_file.name,
                    f"{self.config.get_ssh_param('username')}@{self.config.get_ssh_param('host')}:{self.config.remote_history_path}"
                ]
                
                subprocess.run(scp_command, capture_output=True, text=True, check=True)
                
            os.unlink(temp_file.name)
        except subprocess.CalledProcessError as e:
            if "Permission denied" in str(e.stderr):
                logging.error("Отказано в доступе при записи удаленной истории")
            else:
                logging.error(f"Ошибка при записи удаленной истории: {e}")
            raise
        except Exception as e:
            logging.error(f"Ошибка при записи удаленной истории: {e}")
            raise

    @retry(max_attempts=3)
    def clear_remote_history(self):
        """Очищает удаленную историю"""
        try:
            # Проверяем наличие файла блокировки
            if self._check_lock_file():
                logging.warning("Обнаружен файл блокировки, ожидаем...")
                return False

            # Создаем файл блокировки
            self._create_lock_file()
            logging.info("Файл блокировки создан")

            try:
                # Очищаем историю
                result = subprocess.run(
                    ['ssh', self.ssh_connection, f'truncate -s 0 {self.config.remote_history_path}'],
                    capture_output=True,
                    text=True,
                    check=True  # Это вызовет исключение при ненулевом коде возврата
                )
                
                logging.info("Удаленная история очищена")
                return True

            except subprocess.CalledProcessError as e:
                logging.error(f"Ошибка при очистке удаленной истории: {e.stderr}")
                return False
            finally:
                # Удаляем файл блокировки
                self._remove_lock_file()
                logging.info("Файл блокировки удален")

        except Exception as e:
            logging.error(f"Ошибка при очистке удаленной истории: {e}")
            return False
    
    def merge_histories(self, current_history: List[str], remote_history: List[str]) -> List[str]:
        """Объединяет локальную и удаленную историю"""
        # Объединяем истории и удаляем дубликаты
        merged = list(set(current_history + remote_history))
        # Сортируем по времени (если есть временные метки)
        merged.sort()
        return merged
    
    def cleanup(self):
        """Очищает ресурсы стратегии"""
        try:
            if hasattr(self, '_remove_lock_file'):
                self._remove_lock_file()
        except Exception as e:
            logging.error(f"Ошибка при очистке ресурсов SSH стратегии: {e}")

    def _read_file_with_fallback(self, file_path: str) -> List[str]:
        """Читает файл с использованием различных кодировок"""
        encodings = ['utf-8', 'latin-1', 'cp1252']
        content = []
        
        for encoding in encodings:
            try:
                with open(file_path, 'rb') as f:
                    raw_content = f.read()
                content = raw_content.decode(encoding).splitlines(keepends=True)
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logging.error(f"Ошибка при чтении файла {file_path}: {e}")
                break
        
        return content

    def _write_file_safely(self, file_path: str, content: List[str]):
        """Безопасно записывает файл с использованием временного файла"""
        try:
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                temp_file.write(''.join(content))
                temp_path = temp_file.name

            # Перемещаем временный файл на место целевого
            os.replace(temp_path, file_path)
            logging.info(f"Файл {file_path} успешно записан")
        except Exception as e:
            logging.error(f"Ошибка при записи файла {file_path}: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise 