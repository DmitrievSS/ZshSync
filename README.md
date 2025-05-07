# ZshSync

A tool for synchronizing zsh command history between different machines using Git or SSH.

## Features

- Synchronize command history between different machines
- Multiple synchronization strategies:
  - Git backend for version-controlled history storage
  - SSH for direct machine-to-machine synchronization
- Daemon mode with configurable sync interval
- One-time synchronization capability
- Remote history clearing
- Flexible configuration via config.yaml
- Simple bash wrapper for easy usage
- Global command availability

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
│   ├── git_utils.py           # Git utilities
│   ├── ssh.py                 # SSH strategy
│   ├── memory.py              # Memory strategy
│   └── factory.py             # Strategy factory
├── cli.py                     # Command line argument parsing
├── config.py                  # Configuration
├── config.yaml               # Configuration file
├── history_syncer.py          # Main script
├── zsh_sync                  # Bash wrapper script
├── install.sh                # Installation script
└── README.md                  # Documentation
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/history_syncer.git
cd history_syncer
```

2. Run the installation script:
```bash
./install.sh
```

This will:
- Create a symlink in `~/.local/bin`
- Add `~/.local/bin` to your PATH if not already present
- Make the script executable

After installation, you can use `zsh_sync` from any directory.

3. Configure in `config.yaml`:
```yaml
paths:
  local_history: ~/.zsh_history
  remote_history: .zsh_history_git/history.txt
  git_repo: .zsh_history_git
  log_file: ~/.history_syncer/history_syncer.log
  pid_file: ~/.history_syncer/history_syncer.pid

settings:
  sync_interval_seconds: 3600
  sync_type: git  # or 'ssh' for SSH strategy

git:
  repository_url: git@github.com:username/zsh_history.git
  branch: main
  remote_name: origin

ssh:
  host: remote.example.com
  port: 22
  username: user
  remote_path: ~/.zsh_history
  lock_file: zsh_sync_lock.lock
```

## Usage

The tool provides a simple bash wrapper that handles all the Python environment setup automatically.

### Start Daemon

```bash
zsh_sync
```

### One-time Synchronization

```bash
zsh_sync --once
```

### Stop Daemon

```bash
zsh_sync --stop
```

### Restart Daemon

```bash
zsh_sync --restart
```

### Clear Remote History

```bash
zsh_sync --clear-remote
```

### Specify Configuration File

```bash
zsh_sync --config /path/to/config.yaml
```

## Configuration

### Paths

- `local_history`: path to local history file
- `remote_history`: path to remote history file
- `git_repo`: path to Git repository (for Git strategy)
- `log_file`: path to log file
- `pid_file`: path to PID file

### Settings

- `sync_interval_seconds`: synchronization interval in seconds
- `sync_type`: synchronization type (git/ssh)

### Git Strategy Settings

The Git strategy provides version-controlled history synchronization using a Git repository:

- `repository_url`: Git repository URL
- `branch`: branch for synchronization
- `remote_name`: remote repository name

Key features:
- Automatic history merging with conflict resolution
- Version control of history changes
- Support for multiple machines through Git branches
- Automatic duplicate removal and timestamp-based sorting

### SSH Strategy Settings

The SSH strategy enables direct machine-to-machine synchronization:

- `host`: remote machine hostname
- `port`: SSH port
- `username`: SSH username
- `remote_path`: path to history file on remote machine
- `lock_file`: lock file name for synchronization

Key features:
- Direct synchronization between machines
- File-level locking for concurrent access prevention
- No intermediate storage required
- Real-time synchronization

## Logging

Logs are saved to the file specified in the configuration (`log_file`). By default, this is `~/.history_syncer/history_syncer.log`.

## Development

### Adding a New Sync Strategy

1. Create a new class in `sync_strategies/` inheriting from `HistorySyncStrategy`
2. Implement required methods:
   - `read_remote_history()`
   - `write_remote_history()`
   - Any strategy-specific helper methods
3. Add the strategy to `STRATEGIES` in `sync_strategies/factory.py`

### Testing

```bash
python3 -m pytest tests/
```

## Features

- Multiple synchronization strategies (Git, SSH)
- Automatic history merging between machines with duplicate removal
- Automatic conflict resolution while preserving all commands
- History sorting by timestamps
- Support for various file encodings
- All operations are logged to `history_syncer.log`
- File-level locking for concurrent access prevention
- Version control support through Git strategy
- Simple bash wrapper for easy usage
- Global command availability

## Requirements

- Python 3.9 or higher
- Git (for Git strategy)
- SSH access (for SSH strategy)
- zsh

## Dependencies

- GitPython==3.1.42
- PyYAML==6.0.1
- python-daemon==3.0.1
- pytest==8.0.0 (for tests)
