#!/usr/bin/env python3
import os
import sys
import logging
import argparse
from typing import Optional

from actions import sync_once, clear_remote_history, stop_daemon, restart_daemon, run_daemon
from config import Config
from cli import create_parser

def setup_logging(config: Config):
    """Настройка логирования"""
    log_dir = os.path.dirname(config.log_file_path)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Create formatters
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    # Create handlers
    file_handler = logging.FileHandler(config.log_file_path)
    file_handler.setFormatter(file_formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logging.info("Logging setup completed")

def main(config_path: Optional[str] = None):
    """Основная функция"""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
    
    config = Config(config_path)
    setup_logging(config)

    parser = create_parser()
    args = parser.parse_args()

    if args.config:
        config = Config(args.config)
        setup_logging(config)

    if args.clear_remote:
        clear_remote_history(config)
    elif args.stop:
        stop_daemon(config)
    elif args.restart:
        restart_daemon(config)
    elif args.once:
        sync_once(config)
    else:
        run_daemon(config)

if __name__ == '__main__':
    main() 