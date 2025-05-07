import os
import git
import logging
from .base import HistorySyncStrategy
from .decorators import retry
from config import Config
from typing import List
from .git_utils import (
    setup_repository_directory,
    setup_git_remote,
    setup_history_file
)

class GitHistorySyncStrategy(HistorySyncStrategy):
    """Git-based history synchronization implementation"""
    
    def __init__(self, config: Config):
        """Initialize Git sync strategy"""
        self.config = config
        self.git_repo_path = config.git_repo_path
        self.repo = None
        self.logger = logging.getLogger(__name__)
        self.history_file = os.path.join(self.git_repo_path, 'history.txt')
        
        self._setup_repository()

    def _setup_repository(self):
        """Setup Git repository and required files"""
        try:
            self.logger.info(f"Setting up repository in {self.git_repo_path}")
            self.repo = setup_repository_directory(self.git_repo_path, self.config)
            self.logger.info("Repository directory setup completed")
            
            self.logger.info("Setting up Git remote")
            setup_git_remote(self.repo, self.config)
            self.logger.info("Git remote setup completed")
            
            self.logger.info(f"Setting up history file at {self.history_file}")
            setup_history_file(self.repo, self.history_file, self.config)
            self.logger.info("History file setup completed")
        except Exception as e:
            self.logger.error(f"Error setting up repository: {e}")
            raise

    def get_current_history(self) -> list:
        """Get current history from file"""
        from actions.sync_utils import read_local_history  # Перемещаем импорт сюда
        
        self.logger.info(f"Reading current history from {self.config.local_history_path}")
        history = read_local_history(self.config.local_history_path)
        self.logger.info(f"Read {len(history)} lines from local history")
        return history

    def get_remote_history(self) -> list:
        """Get history from remote branch"""
        self.logger.info("Fetching remote history")
        try:
            self.repo.git.fetch()
            self.logger.info("Fetch completed")
            
            remote_content = self.repo.git.show(f'origin/main:history.txt')
            history = remote_content.splitlines(keepends=True)
            self.logger.info(f"Read {len(history)} lines from remote history")
            return history
        except git.exc.GitCommandError as e:
            self.logger.error(f"Error fetching remote history: {e}")
            return []

    def save_history(self, history: list):
        """Save history to file"""
        from actions.sync_utils import Event  # Перемещаем импорт сюда
        
        self.logger.info(f"Saving {len(history)} lines to history file")
        self.logger.debug(f"First 5 lines of input history: {[line.strip() for line in history[:5]]}")
        
        # Convert lines to Events and back to ensure proper formatting
        formatted_history = []
        for i, line in enumerate(history):
            if not line.strip():
                self.logger.debug(f"Skipping empty line at index {i}")
                continue
                
            event = Event.from_line(line)
            if event:
                formatted_line = event.to_line()
                formatted_history.append(formatted_line)
                self.logger.debug(f"Formatted line {i}: {formatted_line.strip()}")
            else:
                self.logger.debug(f"Failed to parse line {i}: {line.strip()}")
        
        self.logger.info(f"Formatted {len(formatted_history)} valid history entries")
        self.logger.debug(f"First 5 lines of formatted history: {[line.strip() for line in formatted_history[:5]]}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        
        # Write to file
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                f.writelines(formatted_history)
            self.logger.info(f"History saved to {self.history_file}")
            
            # Verify file contents
            with open(self.history_file, 'r', encoding='utf-8') as f:
                saved_lines = f.readlines()
            self.logger.info(f"Verified {len(saved_lines)} lines in saved file")
            self.logger.debug(f"First 5 lines of saved file: {[line.strip() for line in saved_lines[:5]]}")
            
        except Exception as e:
            self.logger.error(f"Error saving history to file: {e}")
            raise

    @retry(max_attempts=3)
    def read_remote_history(self) -> List[str]:
        """Read history from remote Git repository"""
        from actions.sync_utils import Event  # Добавляем импорт сюда
        
        self.logger.info("Starting remote history read")
        
        try:
            # Fetch remote changes
            self.logger.info("Fetching remote changes")
            fetch_info = self.repo.remotes.origin.fetch()
            if not fetch_info:
                raise git.exc.GitCommandError("fetch", "Failed to fetch remote changes")
            self.logger.info("Fetch completed")
            
            # Get remote history
            try:
                self.logger.info("Reading remote history file")
                try:
                    remote_content = self.repo.git.show('origin/main:history.txt')
                    if not remote_content:
                        self.logger.warning("Remote history file is empty")
                        return []
                    self.logger.debug(f"Raw remote content: {remote_content}")
                except git.exc.GitCommandError as e:
                    self.logger.error(f"Failed to show remote file: {e}")
                    return []
                    
                remote_history = remote_content.splitlines(keepends=True)
                if not remote_history:
                    self.logger.warning("No history entries found in remote file")
                    return []
                    
                self.logger.info(f"Read {len(remote_history)} lines from remote history")
                if remote_history:
                    self.logger.debug(f"First 5 lines from remote: {[line.strip() for line in remote_history[:5]]}")
                
                # Verify history entries format
                valid_entries = []
                for i, line in enumerate(remote_history):
                    if not line.strip():
                        continue
                    event = Event.from_line(line)
                    if event:
                        valid_entries.append(line)
                    else:
                        self.logger.warning(f"Invalid history entry at line {i}: {line.strip()}")
                
                if not valid_entries:
                    self.logger.warning("No valid history entries found in remote file")
                    return []
                
                self.logger.info("Saving remote history locally")
                self.save_history(valid_entries)
                return valid_entries
            except git.exc.GitCommandError as e:
                self.logger.error(f"Error reading remote history file: {e}")
                return []

        except Exception as e:
            self.logger.error(f"Error reading remote history: {e}")
            return []

    @retry(max_attempts=3)
    def write_remote_history(self, history: List[str]) -> None:
        """Write history to remote Git repository"""
        self.logger.info(f"Starting remote history write with {len(history)} lines")
        
        try:
            # Pull latest changes first
            self.logger.info("Pulling latest changes")
            try:
                pull_result = self.repo.remotes.origin.pull()
                if not pull_result:
                    raise git.exc.GitCommandError("pull", "Failed to pull changes")
                self.logger.info("Pull completed successfully")
            except git.exc.GitCommandError:
                self.logger.warning("Regular pull failed, trying with --allow-unrelated-histories")
                pull_result = self.repo.git.pull('--allow-unrelated-histories')
                if not pull_result:
                    raise git.exc.GitCommandError("pull", "Failed to pull changes with --allow-unrelated-histories")
                self.logger.info("Pull with --allow-unrelated-histories completed")
            
            # Save history locally
            self.logger.info("Saving history locally")
            self.logger.debug(f"First 5 lines of history to save: {[line.strip() for line in history[:5]]}")
            self.save_history(history)
            
            # Verify local file exists and has content
            if not os.path.exists(self.history_file):
                raise FileNotFoundError(f"History file not found after save: {self.history_file}")
            with open(self.history_file, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            if not saved_content:
                raise ValueError("History file is empty after save")
            
            # Add and commit changes
            self.logger.info("Adding and committing changes")
            self.repo.index.add(['history.txt'])
            if not self.repo.index.diff('HEAD'):
                self.logger.warning("No changes to commit")
                return
                
            commit = self.repo.index.commit("Update history")
            if not commit:
                raise git.exc.GitCommandError("commit", "Failed to commit changes")
            self.logger.info("Changes committed")
            
            # Push changes
            self.logger.info("Pushing changes to remote")
            push_info = self.repo.git.push('origin', 'main')
            if not push_info:
                raise git.exc.GitCommandError("push", "Failed to push changes")
            self.logger.info("Changes pushed successfully")
            
            # Verify remote history
            try:
                remote_content = self.repo.git.show('origin/main:history.txt')
                if not remote_content:
                    raise ValueError("Remote history file is empty after push")
                self.logger.info("Remote history verified")
            except git.exc.GitCommandError as e:
                raise git.exc.GitCommandError("verify", f"Failed to verify remote history: {e}")
            
        except Exception as e:
            self.logger.error(f"Error writing history: {e}")
            raise

    @retry(max_attempts=3)
    def clear_remote_history(self):
        """Clear remote history"""
        self.logger.info("Starting remote history clear")
        try:
            # Clear local history
            self.logger.info("Clearing local history")
            self.save_history([])
            
            # Verify local file is empty
            if not os.path.exists(self.history_file):
                raise FileNotFoundError(f"History file not found after clear: {self.history_file}")
            with open(self.history_file, 'r', encoding='utf-8') as f:
                content = f.read()
            if content:
                raise ValueError("History file is not empty after clear")
            
            # Add and commit changes
            self.logger.info("Committing cleared history")
            self.repo.index.add(['history.txt'])
            
            # Force commit even if there are no changes
            commit = self.repo.index.commit("Clear history")
            if not commit:
                raise git.exc.GitCommandError("commit", "Failed to commit cleared history")
            self.logger.info("Changes committed")
            
            # Force push changes
            self.logger.info("Force pushing cleared history")
            try:
                self.repo.git.push('--force', 'origin', self.config.get_git_param('branch', 'main'))
                self.logger.info("Force push completed")
            except git.exc.GitCommandError as e:
                self.logger.error(f"Failed to force push: {e}")
                return False
            
            # Verify remote history is cleared
            try:
                remote_content = self.repo.git.show('origin/main:history.txt')
                if remote_content:
                    raise ValueError("Remote history file is not empty after clear")
                self.logger.info("Remote history verified as cleared")
            except git.exc.GitCommandError as e:
                self.logger.error(f"Failed to verify remote history: {e}")
                return False
            
            self.logger.info("History cleared successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing remote history: {e}")
            return False

    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up resources")
        if hasattr(self, 'repo'):
            self.repo.close()
            self.logger.info("Repository closed")

    def merge_histories(self, local_history: List[str], remote_history: List[str]) -> List[str]:
        """Merge local and remote histories, sorting by timestamp"""
        from actions.sync_utils import Event  # Добавляем импорт сюда
        
        self.logger.info("Starting history merge")
        self.logger.debug(f"Local history: {len(local_history)} entries")
        self.logger.debug(f"Remote history: {len(remote_history)} entries")
        
        # Convert all entries to Event objects
        events = []
        for line in local_history + remote_history:
            if not line.strip():
                continue
            event = Event.from_line(line)
            if event:
                events.append(event)
        
        # Sort by timestamp
        events.sort(key=lambda x: x.timestamp)
        
        # Convert back to lines
        merged_history = [event.to_line() for event in events]
        
        self.logger.info(f"Merged history contains {len(merged_history)} entries")
        return merged_history 