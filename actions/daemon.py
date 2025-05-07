import os
import sys
import time
import logging
import daemon
import daemon.pidfile
import signal
from datetime import datetime
from config import Config
from sync_strategies.factory import create_sync_strategy
from .sync_utils import sync_history

def get_pid_file_path(config: Config) -> str:
    """Получает путь к PID файлу"""
    return os.path.expanduser(config.pid_file_path)

def is_daemon_running(config: Config) -> bool:
    """Проверяет, запущен ли демон"""
    pid_file = get_pid_file_path(config)
    if not os.path.exists(pid_file):
        return False
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Проверяем, существует ли процесс с таким PID
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    except (ValueError, IOError):
        return False

def write_pid_file(config: Config):
    """Writes process PID to file"""
    pid_file = get_pid_file_path(config)
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))

def remove_pid_file(config: Config):
    """Removes PID file"""
    pid_file = get_pid_file_path(config)
    if os.path.exists(pid_file):
        os.remove(pid_file)

def stop_daemon(config: Config):
    """Stops the daemon"""
    pid_file = get_pid_file_path(config)
    
    try:
        pidlock = daemon.pidfile.PIDLockFile(pid_file)
        if pidlock.is_locked():
            pid = pidlock.read_pid()
            if pid is not None:
                try:
                    os.kill(pid, signal.SIGTERM)
                    logging.info(f"Sent stop signal to process {pid}")
                    
                    # Wait for process to terminate
                    for _ in range(10):
                        try:
                            os.kill(pid, 0)
                            time.sleep(1)
                        except OSError:
                            # Process terminated
                            try:
                                pidlock.break_lock()
                            except Exception:
                                pass
                            logging.info("Daemon stopped successfully")
                            return True
                    logging.error("Failed to stop daemon")
                    return False
                except OSError as e:
                    logging.error(f"Error stopping daemon: {e}")
                    try:
                        pidlock.break_lock()
                    except Exception:
                        pass
                    return False
        else:
            logging.error("Daemon is not running")
            return False
    except Exception as e:
        logging.error(f"Error stopping daemon: {e}")
        return False

def run_daemon(config: Config):
    """Запускает демон синхронизации"""
    if is_daemon_running(config):
        logging.warning("Демон уже запущен")
        return False

    # Создаем директории для PID и лог файлов
    pid_file = get_pid_file_path(config)
    pid_dir = os.path.dirname(pid_file)
    os.makedirs(pid_dir, exist_ok=True)

    log_dir = os.path.dirname(os.path.expanduser(config.log_file_path))
    os.makedirs(log_dir, exist_ok=True)

    # Открываем лог файл
    log_file = os.path.expanduser(config.log_file_path)
    log_fd = os.open(log_file, os.O_WRONLY | os.O_CREAT | os.O_APPEND)

    def log_message(message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        os.write(log_fd, f"{timestamp} - {message}\n".encode())
        os.fsync(log_fd)  # Force write to disk

    # Настраиваем обработчики сигналов
    def handle_sigterm(signo, frame):
        log_message("Received SIGTERM, shutting down...")
        os.close(log_fd)
        remove_pid_file(config)
        sys.exit(0)

    # Создаем контекст демона
    context = daemon.DaemonContext(
        working_directory=os.path.expanduser('~'),
        umask=0o022,
        pidfile=daemon.pidfile.PIDLockFile(pid_file),
        files_preserve=[log_fd],
        signal_map={
            signal.SIGTERM: handle_sigterm,
            signal.SIGINT: handle_sigterm
        }
    )

    try:
        # Запускаем демон
        with context:
            log_message("Daemon started")
            write_pid_file(config)

            # Создаем стратегию синхронизации
            strategy = create_sync_strategy(config)

            # Основной цикл демона
            while True:
                try:
                    log_message("Starting sync cycle")
                    sync_history(config, strategy)
                    log_message("Sync completed successfully")
                except Exception as e:
                    log_message(f"Unexpected error during sync: {str(e)}")

                log_message(f"Waiting {config.sync_interval_seconds} seconds...")
                time.sleep(config.sync_interval_seconds)

        return True
    except Exception as e:
        logging.error(f"Error starting daemon: {e}")
        import traceback
        traceback.print_exc()
        remove_pid_file(config)
        return False

def restart_daemon(config: Config):
    """Restarts the daemon"""
    print("Restarting daemon...")
    if is_daemon_running(config):
        if not stop_daemon(config):
            print("Failed to stop daemon for restart")
            return False
        # Give time for process to terminate
        time.sleep(1)

    return run_daemon(config) 