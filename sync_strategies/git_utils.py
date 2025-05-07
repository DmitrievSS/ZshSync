import os
import git
import shutil
from typing import Optional
from config import Config
import logging

def setup_repository_directory(git_repo_path: str, config: Config) -> Optional[git.Repo]:
    """Setup repository directory and clone if needed"""
    expanded_path = os.path.expanduser(git_repo_path)
    logging.info(f"Setting up repository directory at {git_repo_path}")
    logging.info(f"Expanded path: {expanded_path}")
    logging.info(f"Directory exists: {os.path.exists(expanded_path)}")
    if os.path.exists(expanded_path):
        return handle_existing_directory(expanded_path, config)
    else:
        return create_and_clone_directory(expanded_path, config)

def handle_existing_directory(git_repo_path: str, config: Config) -> Optional[git.Repo]:
    """Handle existing directory - clean and clone if needed"""
    if not os.path.exists(os.path.join(git_repo_path, '.git')):
        clean_directory(git_repo_path)
        return clone_repository(git_repo_path, config)
    else:
        return git.Repo(git_repo_path)

def clean_directory(git_repo_path: str):
    """Clean directory contents"""
    for item in os.listdir(git_repo_path):
        item_path = os.path.join(git_repo_path, item)
        if os.path.isfile(item_path):
            os.unlink(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)

def create_and_clone_directory(git_repo_path: str, config: Config) -> Optional[git.Repo]:
    """Create directory and clone repository"""
    os.makedirs(git_repo_path, exist_ok=True)
    return clone_repository(git_repo_path, config)

def clone_repository(git_repo_path: str, config: Config) -> Optional[git.Repo]:
    """Clone repository from remote or create new one if remote doesn't exist"""
    try:
        return git.Repo.clone_from(
            config.get_git_param('repository_url'),
            git_repo_path,
            branch=config.get_git_param('branch', 'main')
        )
    except git.exc.GitCommandError as e:
        if "Repository not found" in str(e):
            # Create new repository
            repo = git.Repo.init(git_repo_path)
            repo.create_remote('origin', config.get_git_param('repository_url'))
            return repo
        raise

def setup_git_remote(repo: git.Repo, config: Config):
    """Setup Git remote and ensure correct branch"""
    if 'origin' not in [remote.name for remote in repo.remotes]:
        repo.create_remote('origin', config.get_git_param('repository_url'))

    if repo.active_branch.name != config.get_git_param('branch', 'main'):
        repo.git.checkout(config.get_git_param('branch', 'main'))

def setup_history_file(repo: git.Repo, history_file: str, config: Config):
    """Setup history file if it doesn't exist"""
    if not os.path.exists(history_file):
        create_and_commit_history_file(repo, history_file, config)

def create_and_commit_history_file(repo: git.Repo, history_file: str, config: Config):
    """Create history file and commit it"""
    # Create empty history file
    open(history_file, 'w').close()
    
    # Add and commit the new file
    repo.index.add(['history.txt'])
    repo.index.commit("Initialize history file")
    
    # Push changes
    repo.git.push('origin', config.get_git_param('branch', 'main')) 