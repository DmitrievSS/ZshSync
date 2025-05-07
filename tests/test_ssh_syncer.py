#!/usr/bin/env python3
import os
import tempfile
import shutil
import logging
import time
import unittest
from unittest.mock import MagicMock, patch
from config import Config
from sync_strategies import SSHHistorySyncStrategy
import subprocess
import pytest

def format_history_entry(command: str, timestamp: int = None) -> str:
    """Форматирует команду в формат zsh истории"""
    if timestamp is None:
        timestamp = int(time.time())
    return f": {timestamp}:0;{command}\n"

@pytest.fixture
def ssh_config():
    """Фикстура для конфигурации SSH"""
    config = Config()
    config.config = {
        'paths': {
            'local_history': '/tmp/local_history.txt',
            'remote_history': '/tmp/remote_history.txt',
            'pid_file': '/tmp/pid',
            'lock_file': '/tmp/lock'
        },
        'ssh': {
            'username': 'test',
            'host': 'test.com'
        }
    }
    return config

@pytest.fixture
def ssh_strategy(ssh_config):
    """Фикстура для SSH стратегии"""
    return SSHHistorySyncStrategy(ssh_config)

def test_read_remote_history(ssh_strategy, mocker):
    """Тест чтения удаленной истории"""
    # Настраиваем мок для чтения удаленного файла
    remote_content = format_history_entry('remote_command_1') + format_history_entry('remote_command_2')
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=remote_content,
        text=True
    )

    # Читаем удаленную историю
    history = ssh_strategy.read_remote_history()

    # Проверяем результат
    assert len(history) == 2
    assert any('remote_command_1' in line for line in history)
    assert any('remote_command_2' in line for line in history)

def test_write_remote_history(ssh_strategy, mocker):
    """Тест записи удаленной истории"""
    # Подготавливаем историю для записи
    history = [
        format_history_entry('command_1'),
        format_history_entry('command_2')
    ]

    # Настраиваем мок для записи файла
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = MagicMock(returncode=0)

    # Записываем историю
    ssh_strategy.write_remote_history(history)

    # Проверяем, что команды были вызваны
    assert mock_run.call_count == 2  # mkdir и scp
    assert 'mkdir' in mock_run.call_args_list[0][0][0][-1]  # Первый вызов - создание директории
    assert 'scp' in mock_run.call_args_list[1][0][0][0]  # Второй вызов - копирование файла

def test_invalid_history_format(ssh_strategy, mocker):
    """Тест обработки некорректного формата истории"""
    # Настраиваем мок для чтения файла с некорректным форматом
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout='invalid format',
        text=True
    )

    # Читаем удаленную историю
    history = ssh_strategy.read_remote_history()

    # Проверяем результат
    assert len(history) == 1
    assert 'invalid format' in history[0]

def test_file_permission_error(ssh_strategy, mocker):
    """Тест обработки ошибки доступа к файлу"""
    mock_run = mocker.patch('subprocess.run')
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=['ssh'],
        stderr='Permission denied'
    )

    with pytest.raises(subprocess.CalledProcessError):
        ssh_strategy.read_remote_history()

def test_network_timeout(ssh_strategy, mocker):
    """Тест обработки таймаута сети"""
    mock_run = mocker.patch('subprocess.run')
    mock_run.side_effect = subprocess.TimeoutExpired(
        cmd=['ssh'],
        timeout=10
    )

    with pytest.raises(subprocess.TimeoutExpired):
        ssh_strategy.read_remote_history()

def test_ssh_connection_failure(ssh_strategy, mocker):
    """Тест обработки ошибки подключения SSH"""
    mock_run = mocker.patch('subprocess.run')
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=255,
        cmd=['ssh'],
        stderr='Connection refused'
    )

    with pytest.raises(subprocess.CalledProcessError):
        ssh_strategy.read_remote_history()

if __name__ == '__main__':
    unittest.main() 