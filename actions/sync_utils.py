import os
import logging
from typing import List
from dataclasses import dataclass

from config import Config
from sync_strategies.base import HistorySyncStrategy

@dataclass
class Event:
    """Класс для представления события в истории"""
    timestamp: int
    command: str

    @classmethod
    def from_line(cls, line: str) -> 'Event':
        """Создает Event из строки истории"""
        try:
            # Split on first ': ' to handle cases where command contains ':'
            parts = line.split(': ', 1)
            if len(parts) != 2:
                logging.debug(f"Skipping line - invalid format (no ': '): {line.strip()}")
                return None
                
            # Split timestamp and command (format: "timestamp:0;command")
            timestamp_cmd = parts[1].split(';', 1)
            if len(timestamp_cmd) != 2:
                logging.debug(f"Skipping line - invalid format (no ';'): {line.strip()}")
                return None
                
            # Parse timestamp (format: "timestamp:0")
            timestamp = timestamp_cmd[0].split(':')[0].strip()
            if not timestamp.isdigit():
                logging.debug(f"Skipping line - invalid timestamp: {line.strip()}")
                return None
                
            command = timestamp_cmd[1].rstrip('\n')
            return cls(int(timestamp), command)
                
        except (IndexError, ValueError) as e:
            logging.debug(f"Skipping line - parsing error: {line.strip()}, error: {e}")
            return None

    def to_line(self) -> str:
        """Преобразует Event в строку для записи в историю"""
        return f": {self.timestamp}:0;{self.command}\n"

def read_local_history(file_path: str) -> List[str]:
    """Читает локальную историю из файла"""
    if not os.path.exists(file_path):
        logging.warning(f"Local history file not found: {file_path}")
        return []
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Clean and validate entries
        valid_entries = []
        for i, line in enumerate(lines):
            # Skip empty lines
            if not line.strip():
                logging.debug(f"Skipping empty line at index {i}")
                continue
                
            try:
                # Split on first ': ' to handle cases where command contains ':'
                parts = line.split(': ', 1)
                if len(parts) != 2:
                    logging.debug(f"Skipping line {i} - invalid format (no ': '): {line.strip()}")
                    continue
                    
                # Split timestamp and command
                timestamp_cmd = parts[1].split(';', 1)
                if len(timestamp_cmd) != 2:
                    logging.debug(f"Skipping line {i} - invalid format (no ';'): {line.strip()}")
                    continue
                    
                # Parse timestamp
                timestamp = timestamp_cmd[0].split(':')[0].strip()
                if not timestamp.isdigit():
                    logging.debug(f"Skipping line {i} - invalid timestamp: {line.strip()}")
                    continue
                    
                # Normalize the entry format
                command = timestamp_cmd[1].rstrip('\n')
                normalized_entry = f": {timestamp}:0;{command}\n"
                valid_entries.append(normalized_entry)
                logging.debug(f"Added valid entry at index {i}: {normalized_entry.strip()}")
                
            except (IndexError, ValueError) as e:
                logging.debug(f"Skipping line {i} - parsing error: {line.strip()}, error: {e}")
                continue
                
        logging.info(f"Read {len(lines)} total lines, found {len(valid_entries)} valid entries")
        return valid_entries
        
    except Exception as e:
        logging.error(f"Error reading local history: {e}")
        return []

def write_local_history(file_path: str, history: List[str]) -> None:
    """Записывает историю в локальный файл"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(history)

def merge_histories(current_history: List[str], remote_history: List[str]) -> List[str]:
    """Объединяет две истории, удаляя дубликаты и сортируя по временным меткам"""
    # Логируем последние 5 строк из обеих историй
    logging.debug("Last 5 lines from current history:")
    for line in current_history[-5:]:
        logging.debug(f"  {line.strip()}")
        
    logging.debug("Last 5 lines from remote history:")
    for line in remote_history[-5:]:
        logging.debug(f"  {line.strip()}")
        
    # Конвертируем строки в события
    events = []
    for line in current_history + remote_history:
        if not line.strip():
            continue
            
        event = Event.from_line(line)
        if event:
            events.append(event)
    
    # Удаляем дубликаты и сортируем по timestamp
    unique_events = list({(e.timestamp, e.command): e for e in events}.values())
    unique_events.sort(key=lambda e: e.timestamp)
    
    # Конвертируем обратно в строки
    return [event.to_line() for event in unique_events]

def sync_history(config: Config, strategy: HistorySyncStrategy):
    """Синхронизирует историю команд"""
    try:
        try:
            # Читаем удаленную историю
            logging.info("Reading remote history")
            remote_history = strategy.read_remote_history()
            logging.info(f"Read {len(remote_history)} lines from remote history")
            
            # Читаем локальную историю
            logging.info("Reading local history")
            local_history = read_local_history(config.local_history_path)
            logging.info(f"Read {len(local_history)} lines from local history")
            
            # Объединяем истории
            logging.info("Merging histories")
            merged_history = merge_histories(local_history, remote_history)
            logging.info(f"Merged history contains {len(merged_history)} lines")
            
            # Записываем объединенную историю
            logging.info("Writing merged history to remote")
            strategy.write_remote_history(merged_history)
            logging.info("Remote history updated")
            
            # Записываем локальную историю
            logging.info("Writing merged history to local file")
            write_local_history(config.local_history_path, merged_history)
            logging.info("Local history updated")
            
            logging.info("Synchronization completed")
        finally:
            strategy.cleanup()
    except Exception as e:
        logging.error(f"Ошибка при синхронизации: {e}")
        raise 