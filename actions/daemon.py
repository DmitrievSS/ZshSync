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
    """Returns path to PID file"""
    return config.get_path(config.paths.pid_file)

def is_daemon_running(config: Config) -> bool:
    """Checks if daemon is running"""
    pid_file = get_pid_file_path(config)
    
    try:
        pidlock = daemon.pidfile.PIDLockFile(pid_file)
        
        # Check if PID file is locked
        if pidlock.is_locked():
            pid = pidlock.read_pid()
            if pid is not None:
                try:
                    # Check if process exists
                    os.kill(pid, 0)
                    return True
                except OSError:
                    # Process doesn't exist, clear PID file
                    try:
                        pidlock.break_lock()
                    except Exception:
                        pass
                    return False
        return False
    except Exception as e:
        logging.error(f"Error checking daemon status: {e}")
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

def daemon_process(config: Config):
    """Daemon process"""
    try:
        # Set up logging for new process
        from history_syncer import setup_logging
        setup_logging()
        logging.info("Starting daemon process...")
        
        # Write PID
        pid = os.getpid()
        with open(get_pid_file_path(config), 'w') as f:
            f.write(str(pid))
        
        # Start main daemon loop
        run_daemon(config)
    except Exception as e:
        logging.error(f"Critical error in daemon: {e}")
        if os.path.exists(get_pid_file_path(config)):
            os.remove(get_pid_file_path(config))
        raise

def stop_daemon(config: Config):
    """Stops the daemon"""
    pid_file = get_pid_file_path(config)
    
    try:
        pidlock = daemon.pidfile.PIDLockFile(pid_file)
        if pidlock.is_locked():
            pid = pidlock.read_pid()
            if pid is not None:
                try:
                    os.kill(pid, 15)  # SIGTERM
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
    """Runs synchronizer in daemon mode"""
    try:
        if is_daemon_running(config):
            logging.error("Daemon is already running")
            return
        
        logging.info("Starting synchronizer in daemon mode...")
        
        # Create sync strategy
        logging.info("Creating sync strategy...")
        strategy = create_sync_strategy(config)
        
        logging.info("Starting main daemon loop...")
        while True:
            try:
                logging.info("Starting sync cycle")
                sync_history(config, strategy)
                logging.info("Sync completed successfully")
            except Exception as e:
                logging.error(f"Error during sync: {e}")
            
            logging.info(f"Waiting {config.settings.sync_interval_seconds} seconds...")
            time.sleep(config.settings.sync_interval_seconds)
    except Exception as e:
        logging.error(f"Critical error in daemon: {e}")
        raise

def restart_daemon(config: Config):
    """Restarts the daemon"""
    print("Restarting daemon...")
    if is_daemon_running(config):
        if not stop_daemon(config):
            print("Failed to stop daemon for restart")
            return False
        # Give time for process to terminate
        time.sleep(1)
    
    try:
        # Set up daemon context
        log_dir = os.path.expanduser('~/.history_syncer')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, 'history_syncer.log')
        pid_file = get_pid_file_path(config)
        
        # Open log file
        log_fd = os.open(log_file, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
        
        def log_message(message):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            os.write(log_fd, f"{timestamp} - {message}\n".encode())
            os.fsync(log_fd)  # Force write to disk
        
        # Set up signal handlers
        def handle_sigterm(signo, frame):
            log_message("Received SIGTERM, shutting down...")
            os.close(log_fd)
            sys.exit(0)
        
        # Create daemon context
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
        
        # Start daemon
        with context:
            log_message("Daemon started")
            
            # Create sync strategy
            strategy = create_sync_strategy(config)
            
            # Main daemon loop
            while True:
                try:
                    log_message("Starting sync cycle")
                    sync_history(config, strategy)
                    log_message("Sync completed successfully")
                except Exception as e:
                    log_message(f"Unexpected error during sync: {str(e)}")
                
                log_message(f"Waiting {config.settings.sync_interval_seconds} seconds...")
                time.sleep(config.settings.sync_interval_seconds)
        
        return True
    except Exception as e:
        print(f"Error starting daemon: {e}")
        import traceback
        traceback.print_exc()
        return False 