#!/usr/bin/env python3
import os
import tempfile
import shutil
import logging
import time
import git
import pytest
from config import Config
from sync_strategies import GitHistorySyncStrategy

def format_history_entry(command: str, timestamp: int = None) -> str:
    """Format command into zsh history format"""
    if timestamp is None:
        timestamp = int(time.time())
    return f": {timestamp}:0;{command}\n"

@pytest.fixture
def setup_git_repo():
    """Setup test Git repository"""
    # Create temporary directories
    remote_dir = tempfile.mkdtemp()
    work_dir = tempfile.mkdtemp()  # Working directory for initial setup
    local_repo_dir = tempfile.mkdtemp()
    local_history_dir = tempfile.mkdtemp()
    local_history_path = os.path.join(local_history_dir, 'local_history.txt')
    
    try:
        # Initialize bare repository
        bare_repo = git.Repo.init(remote_dir, bare=True)
        
        # Initialize working repository
        work_repo = git.Repo.init(work_dir)
        work_repo.create_remote('origin', remote_dir)
        
        # Create and commit initial history
        history_file = os.path.join(work_dir, 'history.txt')
        with open(history_file, 'w') as f:
            f.write(format_history_entry("remote_command1", 1000))
            f.write(format_history_entry("remote_command2", 2000))
        
        work_repo.index.add(['history.txt'])
        work_repo.index.commit("Initial commit")
        
        # Create main branch and push to remote
        work_repo.create_head('main')
        work_repo.heads.main.checkout()
        work_repo.git.push('--set-upstream', 'origin', 'main')
        
        # Create local history
        with open(local_history_path, 'w') as f:
            f.write(format_history_entry("local_command1", 3000))
            f.write(format_history_entry("local_command2", 4000))
        
        # Create config
        config = Config()
        config.config = {
            'sync_type': 'git',
            'paths': {
                'local_history': local_history_path,
                'remote_history': os.path.join(local_repo_dir, 'history.txt'),
                'git_repo': local_repo_dir,
                'log_file': os.path.join(local_repo_dir, 'history_syncer.log'),
                'pid_file': os.path.join(local_repo_dir, 'history_syncer.pid')
            },
            'git': {
                'repository_url': remote_dir,
                'branch': 'main'
            }
        }
        
        yield config, remote_dir, local_repo_dir, local_history_path
        
    finally:
        # Cleanup
        shutil.rmtree(remote_dir, ignore_errors=True)
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(local_repo_dir, ignore_errors=True)
        shutil.rmtree(local_history_dir, ignore_errors=True)

def test_basic_sync(setup_git_repo):
    """Test basic sync functionality"""
    config, _, _, _ = setup_git_repo
    strategy = GitHistorySyncStrategy(config)
    
    # Test reading remote history
    remote_history = strategy.read_remote_history()
    assert len(remote_history) == 2
    assert any("remote_command1" in line for line in remote_history)
    assert any("remote_command2" in line for line in remote_history)
    
    # Test writing new history
    new_command = format_history_entry("new_command", 5000)
    new_history = remote_history + [new_command]
    strategy.write_remote_history(new_history)
    
    # Verify updated history
    updated_history = strategy.read_remote_history()
    assert len(updated_history) == 3, f"Expected 3 entries, got {len(updated_history)}: {updated_history}"
    assert any("remote_command1" in line for line in updated_history), "Missing remote_command1"
    assert any("remote_command2" in line for line in updated_history), "Missing remote_command2"
    assert any("new_command" in line for line in updated_history), "Missing new_command"

def test_merge_history(setup_git_repo):
    """Test history merging functionality"""
    config, _, _, _ = setup_git_repo
    strategy = GitHistorySyncStrategy(config)
    
    # Read and merge histories
    remote_history = strategy.read_remote_history()
    local_history = strategy.get_current_history()
    merged_history = strategy.merge_histories(local_history, remote_history)
    
    # Verify merged history
    assert len(merged_history) == 4
    assert any("remote_command1" in line for line in merged_history)
    assert any("remote_command2" in line for line in merged_history)
    assert any("local_command1" in line for line in merged_history)
    assert any("local_command2" in line for line in merged_history)
    
    # Verify sorting
    timestamps = [int(line.split(':')[1].strip()) for line in merged_history]
    assert timestamps == sorted(timestamps)

def test_clear_history(setup_git_repo):
    """Test history clearing functionality"""
    config, _, _, _ = setup_git_repo
    strategy = GitHistorySyncStrategy(config)
    
    # Clear history
    assert strategy.clear_remote_history()
    
    # Verify history is cleared
    history = strategy.read_remote_history()
    assert len(history) == 0 