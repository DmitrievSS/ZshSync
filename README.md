# ZshSync

A tool for synchronizing zsh command history between different machines using Git.

## Features

- Synchronize command history between different machines
- Git backend support for history storage
- Daemon mode with configurable sync interval
- One-time synchronization capability
- Remote history clearing
- Flexible configuration via config.ini

## Project Structure

```
history_syncer/
├── actions/                   # Action modules
│   ├── __init__.py            
│   ├── sync.py                # One-time synchronization
│   ├── clear.py               # Remote history clearing
│   ├── daemon.py              # Daemon management
│   └── sync_utils.py          # Common sync utilities
├── sync_strategies/           # Sync strategies
│   ├── __init__.py
│   ├── base.py                # Base strategy class
│   ├── git.py                 # Git strategy
│   ├── memory.py              # Memory strategy
│   └── factory.py             # Strategy factory
├── cli.py                     # Command line argument parsing
├── config.py                  # Configuration
├── config.ini                 # Configuration file
├── history_syncer.py          # Main script
└── README.md                  # Documentation
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/history_syncer.git
cd history_syncer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure in `config.ini`:
```ini
[Paths]
local_history = ~/.zsh_history
remote_history = ~/.zsh_history_sync
git_repo = ~/.zsh_history_git
log_file = ~/.history_syncer/history_syncer.log
pid_file = ~/.history_syncer/history_syncer.pid

[Settings]
sync_interval_seconds = 3600
sync_type = git

[Git]
repository_url = git@github.com:username/zsh_history.git
branch = main
remote_name = origin
```

## Usage

### Start Daemon

```bash
history_syncer
```

### One-time Synchronization

```bash
history_syncer --once
```

### Stop Daemon

```bash
history_syncer --stop
```

### Restart Daemon

```bash
history_syncer --restart
```

### Clear Remote History

```bash
history_syncer --clear-remote
```

### Specify Configuration File

```bash
history_syncer --config /path/to/config.ini
```

## Configuration

### Paths

- `local_history`: path to local history file
- `remote_history`: path to remote history file
- `git_repo`: path to Git repository
- `log_file`: path to log file
- `pid_file`: path to PID file

### Settings

- `sync_interval_seconds`: synchronization interval in seconds
- `sync_type`: synchronization type (git/memory)

### Git Settings

- `repository_url`: Git repository URL
- `branch`: branch for synchronization
- `remote_name`: remote repository name

## Logging

Logs are saved to the file specified in the configuration (`log_file`). By default, this is `~/.history_syncer/history_syncer.log`.

## Development

### Adding a New Sync Strategy

1. Create a new class in `sync_strategies/` inheriting from `HistorySyncStrategy`
2. Implement required methods
3. Add the strategy to `STRATEGIES` in `sync_strategies/factory.py`

### Testing

```bash
python -m pytest tests/
```

## Features

- Automatic history merging between machines with duplicate removal
- Automatic conflict resolution while preserving all commands
- History sorting by timestamps
- Support for various file encodings
- All operations are logged to `history_syncer.log`

## Requirements

- Python 3.9 or higher
- Git
- zsh
- SSH access to GitHub (for remote synchronization)

## Dependencies

- GitPython==3.1.41
- python-daemon==3.0.1
- pytest==8.0.0 (for tests)
